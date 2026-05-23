import pytest
import numpy as np
import threading
import time
from premortem.backend.detection.circular_buffer import CircularBuffer

def test_circular_buffer_initialization():
    cb = CircularBuffer("test_metric", max_size=20)
    assert cb.metric_name == "test_metric"
    assert cb.max_size == 20
    assert repr(cb) == "<CircularBuffer metric='test_metric' count=0/20 head_idx=0>"
    
    # Should return empty on insufficient data
    ts, vals = cb.get_data()
    assert len(ts) == 0
    assert len(vals) == 0

def test_circular_buffer_insufficient_data():
    cb = CircularBuffer("test", max_size=20)
    for i in range(9):
        cb.append(i, float(i))
    
    ts, vals = cb.get_data()
    assert len(ts) == 0
    assert len(vals) == 0
    
    # 10th item
    cb.append(9, 9.0)
    ts, vals = cb.get_data()
    assert len(ts) == 10
    assert len(vals) == 10
    np.testing.assert_array_equal(vals, np.arange(10, dtype=np.float64))

def test_circular_buffer_wrap_around():
    cb = CircularBuffer("test", max_size=15)
    for i in range(20):
        cb.append(i, float(i))
        
    ts, vals = cb.get_data()
    # Expecting the last 15 elements: 5 to 19
    assert len(ts) == 15
    np.testing.assert_array_equal(vals, np.arange(5, 20, dtype=np.float64))
    np.testing.assert_array_equal(ts, np.arange(5, 20, dtype=np.float64))

def test_circular_buffer_nan_filtering():
    cb = CircularBuffer("test", max_size=20)
    for i in range(15):
        if i == 5:
            cb.append(np.nan, float(i))
        else:
            cb.append(i, float(i))
            
    ts, vals = cb.get_data()
    assert len(ts) == 14
    assert np.isnan(vals).sum() == 0

def test_circular_buffer_thread_safety():
    cb = CircularBuffer("test", max_size=1000)
    
    def worker(start_idx, count):
        for i in range(count):
            cb.append(start_idx + i, float(start_idx + i))
            
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i * 100, 100))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    ts, vals = cb.get_data()
    assert len(ts) == 1000
    assert len(vals) == 1000
