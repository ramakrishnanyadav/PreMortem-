import numpy as np
from sklearn.ensemble import IsolationForest as SKLearnIF
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass
from typing import Optional
import structlog
import threading

log = structlog.get_logger()

@dataclass  
class IsolationForestResult:
    is_anomaly: bool
    anomaly_score: float      # -1 to 1, lower = more anomalous
    contamination_estimate: float
    feature_names: list[str]
    feature_values: list[float]
    feature_deltas: list[float]  # change from rolling mean

class IsolationForestDetector:
    """
    Multivariate outlier detection across all service metrics
    simultaneously. Catches systemic anomalies that no single
    metric detector can see in isolation.
    
    Retrains every 30 minutes on fresh rolling data.
    Uses delta features (change from baseline) not raw values —
    this makes the model service-agnostic and transfer-learning
    friendly. A 500ms latency spike means the same thing whether
    the baseline is 50ms or 5000ms.
    """
    
    CONTAMINATION = 0.05      # expect 5% anomalous windows
    N_ESTIMATORS = 100        # number of isolation trees
    MIN_SAMPLES = 30          # minimum before training
    RETRAIN_INTERVAL = 30     # minutes between retraining
    ANOMALY_THRESHOLD = -0.1  # score below this = anomaly
    
    def __init__(self, buffer_registry: dict):
        self.buffers = buffer_registry
        self._model: Optional[SKLearnIF] = None
        self._scaler = StandardScaler()
        self._feature_keys: list[str] = []
        self._lock = threading.Lock()
        self._last_train_time: float = 0.0
        self._training_sample_count: int = 0
    
    def _build_feature_vector(self) -> Optional[tuple]:
        """
        Build a single feature vector from current buffer state.
        Features are deltas from rolling mean — not raw values.
        Returns (feature_names, feature_values, feature_deltas)
        or None if insufficient data.
        """
        feature_names = []
        feature_values = []
        feature_deltas = []
        
        for key, buffer in self.buffers.items():
            _, values = buffer.get_data()
            if len(values) < self.MIN_SAMPLES:
                continue
                
            current = values[-1]
            rolling_mean = np.mean(values[-20:])   # 10-min baseline
            long_mean = np.mean(values[-60:])      # 30-min baseline
            
            # Delta from short baseline (catches spikes)
            delta_short = (current - rolling_mean) / (
                np.std(values[-20:]) + 1e-9
            )
            # Delta from long baseline (catches drift)
            delta_long = (current - long_mean) / (
                np.std(values[-60:]) + 1e-9
            )
            
            feature_names.append(f"{key}_delta_short")
            feature_values.append(float(delta_short))
            feature_deltas.append(float(current - rolling_mean))
            
            feature_names.append(f"{key}_delta_long")
            feature_values.append(float(delta_long))
            feature_deltas.append(float(current - long_mean))
        
        if len(feature_names) < 4:  # need at least 2 metrics
            return None
            
        return feature_names, feature_values, feature_deltas
    
    def _build_training_matrix(self) -> Optional[np.ndarray]:
        """
        Build training matrix from historical buffer data.
        Each row = one time window's feature vector.
        Uses last 60 windows (30 minutes of data).
        """
        rows = []
        
        # Get consistent feature keys from current buffers
        valid_keys = []
        for k, buf in self.buffers.items():
            _, vals = buf.get_data()
            if len(vals) >= self.MIN_SAMPLES:
                valid_keys.append(k)
        
        if len(valid_keys) < 2:
            return None
        
        self._feature_keys = valid_keys
        
        # Build sliding window samples
        for offset in range(60, 0, -1):
            row = []
            for key in valid_keys:
                _, values = self.buffers[key].get_data()
                if offset >= len(values):
                    row.append(0.0)
                    row.append(0.0) # We need 2 features per metric
                    continue
                idx = len(values) - offset
                
                # short window
                window_short = values[max(0, idx-20):idx]
                if len(window_short) < 5:
                    row.append(0.0)
                else:
                    current = values[idx - 1]
                    mean = np.mean(window_short)
                    std = np.std(window_short) + 1e-9
                    row.append(float((current - mean) / std))
                    
                # long window
                window_long = values[max(0, idx-60):idx]
                if len(window_long) < 5:
                    row.append(0.0)
                else:
                    current = values[idx - 1]
                    mean = np.mean(window_long)
                    std = np.std(window_long) + 1e-9
                    row.append(float((current - mean) / std))
                    
            rows.append(row)
        
        if len(rows) < self.MIN_SAMPLES:
            return None
            
        return np.array(rows)
    
    def train(self) -> bool:
        """
        Train/retrain the Isolation Forest model.
        Called on startup and every RETRAIN_INTERVAL minutes.
        Returns True if training succeeded.
        """
        matrix = self._build_training_matrix()
        if matrix is None:
            log.warning("isolation_forest_training_skipped",
                       reason="insufficient_data")
            return False
        
        try:
            with self._lock:
                scaled = self._scaler.fit_transform(matrix)
                self._model = SKLearnIF(
                    n_estimators=self.N_ESTIMATORS,
                    contamination=self.CONTAMINATION,
                    random_state=42,
                    n_jobs=-1  # use all CPU cores
                )
                self._model.fit(scaled)
                self._training_sample_count = len(matrix)
                
            log.info("isolation_forest_trained",
                    samples=len(matrix),
                    features=matrix.shape[1])
            return True
            
        except Exception as e:
            log.error("isolation_forest_training_failed", error=str(e))
            return False
    
    def detect(self) -> Optional[IsolationForestResult]:
        """
        Run detection on current system state.
        Returns None if model not trained or insufficient data.
        Called by anomaly_aggregator every 30 seconds.
        """
        with self._lock:
            if self._model is None:
                return None
        
        result = self._build_feature_vector()
        if result is None:
            return None
            
        feature_names, feature_values, feature_deltas = result
        
        # Pad/trim to match training feature count
        if len(feature_values) != len(self._feature_keys) * 2:
            return None  # feature mismatch — retrain needed
        
        try:
            with self._lock:
                vector = np.array(feature_values).reshape(1, -1)
                scaled = self._scaler.transform(vector)
                prediction = self._model.predict(scaled)[0]
                score = self._model.score_samples(scaled)[0]
            
            is_anomaly = (prediction == -1 and 
                         score < self.ANOMALY_THRESHOLD)
            
            if is_anomaly:
                log.warning("isolation_forest_anomaly_detected",
                           score=round(float(score), 4),
                           features=len(feature_names))
            
            return IsolationForestResult(
                is_anomaly=bool(is_anomaly),
                anomaly_score=round(float(score), 4),
                contamination_estimate=self.CONTAMINATION,
                feature_names=feature_names,
                feature_values=[round(v, 4) for v in feature_values],
                feature_deltas=[round(d, 4) for d in feature_deltas]
            )
            
        except Exception as e:
            log.error("isolation_forest_detection_failed",
                     error=str(e))
            return None
