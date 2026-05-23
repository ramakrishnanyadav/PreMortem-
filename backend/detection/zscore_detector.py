"""
zscore_detector.py
------------------
Implements Modified Z-Score anomaly detection using Median and MAD.
Robust against outliers. Alerts only on 3 consecutive threshold breaches.
"""
import numpy as np
import structlog
from typing import Optional, Dict, Any

logger = structlog.get_logger(__name__)

class ModifiedZScoreDetector:
    def __init__(self, metric_name: str, threshold: float = 3.5, window_size: int = 60, consecutive_alerts: int = 3):
        self.metric_name = metric_name
        self.threshold = threshold
        self.window_size = window_size
        self.consecutive_alerts = consecutive_alerts
        self.alert_counter = 0

    def detect(self, values: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Runs modified Z-score detection on the latest rolling window.
        Returns an anomaly dict if 3 consecutive scores exceed threshold.
        """
        if len(values) < self.window_size:
            # Need full window to compute a stable baseline
            return None
            
        # We look at the last `window_size` samples
        window = values[-self.window_size:]
        
        median = np.median(window)
        abs_dev = np.abs(window - median)
        mad = np.median(abs_dev)
        
        # Guard against zero MAD
        if mad == 0:
            mad = 1e-6
            
        # Calculate modified Z-score for the latest point
        latest_val = window[-1]
        modified_z = 0.6745 * (latest_val - median) / mad
        
        if abs(modified_z) > self.threshold:
            self.alert_counter += 1
            if self.alert_counter >= self.consecutive_alerts:
                # Reset counter to prevent alarm fatigue
                self.alert_counter = 0
                return {
                    "detector": "modified_zscore",
                    "metric": self.metric_name,
                    "latest_value": float(latest_val),
                    "median": float(median),
                    "mad": float(mad),
                    "score": float(modified_z),
                    "threshold": self.threshold
                }
        else:
            # Reset counter if the streak is broken
            self.alert_counter = 0
            
        return None
