"""
correlation_engine.py
---------------------
Computes cross-correlations and Granger causality between time-series buffers.
"""
import numpy as np
import structlog
from typing import Dict, List, Tuple
from itertools import combinations
from premortem.backend.detection.granger_causality import GrangerCausalityEngine

logger = structlog.get_logger(__name__)

class CorrelationEngine:
    def __init__(self, buffer_manager):
        self.buffer_manager = buffer_manager
        self.granger_engine = GrangerCausalityEngine(buffer_manager.buffers)

    def compute_pearson_matrix(self) -> Dict[str, float]:
        """
        Computes Pearson correlation for all pairs of metrics.
        Returns a dict mapping "metricA -> metricB" to correlation coefficient.
        """
        correlations = {}
        metrics = list(self.buffer_manager.buffers.keys())
        
        for m1, m2 in combinations(metrics, 2):
            ts1, v1 = self.buffer_manager.buffers[m1].get_data()
            ts2, v2 = self.buffer_manager.buffers[m2].get_data()
            
            if len(v1) < 30 or len(v2) < 30:
                continue
                
            min_len = min(len(v1), len(v2))
            v1_align = v1[-min_len:]
            v2_align = v2[-min_len:]
            
            if np.std(v1_align) == 0 or np.std(v2_align) == 0:
                continue
                
            corr = np.corrcoef(v1_align, v2_align)[0, 1]
            
            if not np.isnan(corr):
                correlations[f"{m1} -> {m2}"] = float(corr)
                correlations[f"{m2} -> {m1}"] = float(corr)
                
        return correlations

    def run_granger_updates(self):
        """
        Run Granger causality tests on all service metrics pairs.
        Called every 15 minutes by the intelligence loop.
        """
        service_metric_pairs = []
        for key in self.buffer_manager.buffers.keys():
            # Assume metric format: "service-metric"
            parts = key.split('-')
            if len(parts) >= 2:
                service = parts[0]
                metric = "-".join(parts[1:])
                service_metric_pairs.append((service, metric))
                
        return self.granger_engine.run_all_pairs(service_metric_pairs)

