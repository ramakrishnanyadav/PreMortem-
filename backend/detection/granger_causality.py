import numpy as np
from statsmodels.tsa.stattools import grangercausalitytests
from dataclasses import dataclass
from typing import Optional
import structlog

log = structlog.get_logger()

@dataclass
class GrangerResult:
    source_service: str
    target_service: str
    max_lag_minutes: float
    p_value: float
    is_significant: bool      # p_value < 0.05
    causal_strength: float    # 1 - p_value, normalized 0-1
    predictive_lag_samples: int  # which lag was most significant
    
class GrangerCausalityEngine:
    """
    Tests whether past values of service A significantly improve
    prediction of service B beyond B's own past values alone.
    
    This is directional — A→B is tested independently from B→A.
    Significant result means A causally precedes B in time.
    This is how we find "GitHub Actions degradation CAUSES
    npm resolution failures 4 minutes later" automatically.
    """
    
    MIN_SAMPLES = 60        # minimum data points required
    MAX_LAG = 10            # test lags 1-10 (each = 30 seconds)
    SIGNIFICANCE = 0.05     # p-value threshold
    
    def __init__(self, buffer_registry: dict):
        self.buffers = buffer_registry
        self._causal_edges: dict[tuple, GrangerResult] = {}
    
    def test_causality(
        self, 
        source_service: str,
        source_metric: str,
        target_service: str, 
        target_metric: str,
    ) -> Optional[GrangerResult]:
        """
        Run Granger causality test for one service pair.
        Returns None if insufficient data or test fails.
        """
        source_key = f"{source_service}-{source_metric}"
        target_key = f"{target_service}-{target_metric}"
        
        source_buf = self.buffers.get(source_key)
        target_buf = self.buffers.get(target_key)
        
        if source_buf is None or target_buf is None:
            return None
            
        _, source_data = source_buf.get_data()
        _, target_data = target_buf.get_data()
        
        # Require minimum samples — never run on insufficient data
        if len(source_data) < self.MIN_SAMPLES:
            log.debug("insufficient_samples_for_granger",
                     source=source_key, count=len(source_data))
            return None
        if len(target_data) < self.MIN_SAMPLES:
            return None
            
        # Align lengths — take the shorter of the two
        min_len = min(len(source_data), len(target_data))
        source_data = source_data[-min_len:]
        target_data = target_data[-min_len:]
        
        # Guard: constant series cannot be tested (zero variance)
        if np.std(source_data) == 0 or np.std(target_data) == 0:
            log.debug("constant_series_skipped_granger",
                     source=source_key, target=target_key)
            return None
        
        # Stack into [n_samples, 2] matrix required by statsmodels
        # Column order: [target, source] — statsmodels convention
        data_matrix = np.column_stack([target_data, source_data])
        
        try:
            results = grangercausalitytests(
                data_matrix,
                maxlag=self.MAX_LAG,
                verbose=False
            )
        except Exception as e:
            log.warning("granger_test_failed",
                       source=source_key, target=target_key,
                       error=str(e))
            return None
        
        # Find the lag with the lowest p-value (most significant)
        best_lag = None
        best_p = 1.0
        
        for lag, result in results.items():
            # Use F-test p-value (most reliable for this use case)
            p_val = result[0]['ssr_ftest'][1]
            if p_val < best_p:
                best_p = p_val
                best_lag = lag
        
        if best_lag is None:
            return None
            
        is_significant = best_p < self.SIGNIFICANCE
        
        granger_result = GrangerResult(
            source_service=source_service,
            target_service=target_service,
            max_lag_minutes=best_lag * 0.5,  # 30s samples → minutes
            p_value=round(best_p, 4),
            is_significant=is_significant,
            causal_strength=round(1.0 - best_p, 4) if is_significant 
                           else 0.0,
            predictive_lag_samples=best_lag
        )
        
        if is_significant:
            edge_key = (source_service, target_service)
            self._causal_edges[edge_key] = granger_result
            log.info("granger_causality_detected",
                    source=source_service,
                    target=target_service,
                    lag_minutes=granger_result.max_lag_minutes,
                    p_value=best_p,
                    strength=granger_result.causal_strength)
        
        return granger_result
    
    def run_all_pairs(self, service_metric_pairs: list[tuple]) -> dict:
        """
        Test all directed pairs. Called every 15 minutes.
        Returns dict of significant causal edges found.
        
        service_metric_pairs: list of (service_name, metric_key)
        Tests every ordered pair (A→B) and (B→A) independently.
        """
        significant_edges = {}
        
        for i, (src_svc, src_metric) in enumerate(service_metric_pairs):
            for j, (tgt_svc, tgt_metric) in enumerate(
                service_metric_pairs
            ):
                if i == j:
                    continue  # skip self-causality
                    
                result = self.test_causality(
                    src_svc, src_metric,
                    tgt_svc, tgt_metric
                )
                
                if result and result.is_significant:
                    key = f"{src_svc}→{tgt_svc}"
                    significant_edges[key] = result
        
        log.info("granger_run_complete",
                significant_edges=len(significant_edges),
                total_pairs=len(service_metric_pairs)**2)
        
        return significant_edges
    
    def get_causal_edges(self) -> dict:
        """Return all currently known significant causal edges."""
        return self._causal_edges.copy()
    
    def get_predictive_lag(
        self, source: str, target: str
    ) -> Optional[float]:
        """
        How many minutes does source precede target?
        Used by AI context builder for time_to_impact estimation.
        """
        result = self._causal_edges.get((source, target))
        return result.max_lag_minutes if result else None
