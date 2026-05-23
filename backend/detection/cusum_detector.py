"""
cusum_detector.py
-----------------
Implements CUSUM (Cumulative Sum) drift detector.
Detects gradual drift that Z-score might miss.
"""
import numpy as np
import structlog
from typing import Optional, Dict, Any

logger = structlog.get_logger(__name__)

class CUSUMDetector:
    def __init__(self, metric_name: str, window_size: int = 60):
        self.metric_name = metric_name
        self.window_size = window_size
        self.S_pos = 0.0
        self.S_neg = 0.0

    def detect(self, values: np.ndarray) -> Optional[Dict[str, Any]]:
        if len(values) < self.window_size:
            return None

        # Calculate baseline stats on the window excluding the latest point
        baseline = values[-self.window_size:-1]
        latest_val = values[-1]
        
        mu = np.mean(baseline)
        sigma = np.std(baseline)
        
        if sigma == 0:
            sigma = 1e-6

        # CUSUM parameters
        k = 0.5 * sigma
        h = 5 * sigma

        # Update accumulators
        self.S_pos = max(0, self.S_pos + (latest_val - mu - k))
        self.S_neg = max(0, self.S_neg + (mu - latest_val - k))

        # Check for alerts
        drift_direction = None
        if self.S_pos > h:
            drift_direction = "upward"
        elif self.S_neg > h:
            drift_direction = "downward"

        if drift_direction:
            # Reset accumulators on alert
            self.S_pos = 0.0
            self.S_neg = 0.0
            
            return {
                "detector": "cusum",
                "metric": self.metric_name,
                "latest_value": float(latest_val),
                "mu": float(mu),
                "sigma": float(sigma),
                "drift_direction": drift_direction
            }
            
        return None
