"""
anomaly_aggregator.py
---------------------
Runs multiple anomaly detectors on metric buffers and aggregates results.
"""
import structlog
from typing import Dict, List, Any
import numpy as np

from premortem.backend.detection.zscore_detector import ModifiedZScoreDetector
from premortem.backend.detection.cusum_detector import CUSUMDetector
from premortem.backend.detection.isolation_forest import IsolationForestDetector

logger = structlog.get_logger(__name__)

class AnomalyAggregator:
    def __init__(self, buffer_manager):
        self.buffer_manager = buffer_manager
        
        # Maintain a list of detectors per metric
        self.zscore_detectors: Dict[str, ModifiedZScoreDetector] = {}
        self.cusum_detectors: Dict[str, CUSUMDetector] = {}
        self.isolation_forest = IsolationForestDetector(buffer_manager.buffers)

    def _get_zscore(self, metric: str) -> ModifiedZScoreDetector:
        if metric not in self.zscore_detectors:
            self.zscore_detectors[metric] = ModifiedZScoreDetector(metric)
        return self.zscore_detectors[metric]

    def _get_cusum(self, metric: str) -> CUSUMDetector:
        if metric not in self.cusum_detectors:
            self.cusum_detectors[metric] = CUSUMDetector(metric)
        return self.cusum_detectors[metric]

    def run_all(self) -> List[Dict[str, Any]]:
        """
        Runs all configured detectors synchronously over the latest buffer data.
        Returns a list of raw anomaly signals if ensemble_votes >= 2.
        """
        anomalies = []
        
        # 1. Run IF
        if_result = self.isolation_forest.detect()
        
        for metric, buffer in self.buffer_manager.buffers.items():
            ts, vals = buffer.get_data()
            if len(vals) < 3: # Lowered for testing
                continue

            # Run detectors
            z_anomaly = self._get_zscore(metric).detect(vals)
            c_anomaly = self._get_cusum(metric).detect(vals)

            ensemble_votes = sum([
                1 if z_anomaly else 0,
                1 if c_anomaly else 0,
                1 if (if_result and if_result.is_anomaly) else 0
            ])

            if ensemble_votes >= 2:
                if z_anomaly:
                    anomalies.append(z_anomaly)
                if c_anomaly:
                    anomalies.append(c_anomaly)
                
        # Include IF result in anomaly payload if it fired and we have other signals
        if if_result and if_result.is_anomaly and anomalies:
            anomalies.append({
                "detector": "isolation_forest",
                "metric": "multivariate",
                "score": if_result.anomaly_score,
                "features": if_result.feature_names
            })
                
        return anomalies
