"""
circular_buffer.py
------------------
Thread-safe, preallocated numpy-based circular buffer for time-series data.
Zero heap allocations during normal operation. 
"""
import numpy as np
import threading
import time
import structlog
from typing import Tuple

logger = structlog.get_logger(__name__)

class CircularBuffer:
    def __init__(self, metric_name: str, max_size: int = 240):
        """
        Initializes a thread-safe circular buffer.
        
        Args:
            metric_name (str): Name of the metric (e.g., 'github-actions-queue_depth').
            max_size (int): Max number of samples (default 240 for 2-hour window at 30s resolution).
        """
        self.metric_name = metric_name
        self.max_size = max_size
        
        # Preallocate numpy arrays for zero heap allocation during normal operation
        self._timestamps = np.zeros(max_size, dtype=np.float64)
        self._values = np.zeros(max_size, dtype=np.float64)
        
        self._lock = threading.Lock()
        self._head = 0  # Points to the next insertion index
        self._count = 0 # Number of valid samples
        
        logger.debug("circular_buffer_initialized", metric=self.metric_name, max_size=self.max_size)

    def append(self, value: float, timestamp: float = None) -> None:
        """
        Appends a new value to the buffer.
        """
        if timestamp is None:
            timestamp = time.time()
            
        with self._lock:
            self._timestamps[self._head] = timestamp
            self._values[self._head] = float(value)
            
            self._head = (self._head + 1) % self.max_size
            if self._count < self.max_size:
                self._count += 1
                
        logger.debug("circular_buffer_appended", metric=self.metric_name, value=value, ts=timestamp)

    def get_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns a chronologically ordered copy of timestamps and values.
        Guards against insufficient data (minimum 10 samples required).
        
        Returns:
            Tuple[np.ndarray, np.ndarray]: Ordered timestamps and values arrays.
            If count < 10, returns (empty array, empty array) and logs a warning.
        """
        with self._lock:
            count = self._count
            if count < 10:
                logger.warning("circular_buffer_insufficient_data", metric=self.metric_name, count=count, min_required=10)
                return np.array([], dtype=np.float64), np.array([], dtype=np.float64)
                
            # If buffer is not full, the valid data is from 0 to count
            if count < self.max_size:
                ts_out = self._timestamps[:count].copy()
                val_out = self._values[:count].copy()
            else:
                # If buffer is full, unwrap it: head to end, then 0 to head
                ts_out = np.concatenate((self._timestamps[self._head:], self._timestamps[:self._head]))
                val_out = np.concatenate((self._values[self._head:], self._values[:self._head]))
                
        # Guard against NaNs just in case they were appended
        valid_mask = ~np.isnan(val_out)
        
        # If filtering NaNs drops us below 10 samples, return empty
        if np.sum(valid_mask) < 10:
            logger.warning("circular_buffer_insufficient_valid_data_after_nan_filter", metric=self.metric_name)
            return np.array([], dtype=np.float64), np.array([], dtype=np.float64)
            
        return ts_out[valid_mask], val_out[valid_mask]

    def __repr__(self) -> str:
        with self._lock:
            return f"<CircularBuffer metric='{self.metric_name}' count={self._count}/{self.max_size} head_idx={self._head}>"
