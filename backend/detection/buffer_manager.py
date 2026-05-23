"""
buffer_manager.py
-----------------
Manages all CircularBuffer instances for metrics.
"""
import structlog
from typing import Dict
from premortem.backend.detection.circular_buffer import CircularBuffer

logger = structlog.get_logger(__name__)

class BufferManager:
    def __init__(self, max_size: int = 240):
        self.buffers: Dict[str, CircularBuffer] = {}
        self.max_size = max_size

    def get_buffer(self, metric_name: str) -> CircularBuffer:
        if metric_name not in self.buffers:
            self.buffers[metric_name] = CircularBuffer(metric_name, self.max_size)
            logger.info("buffer_created", metric=metric_name)
        return self.buffers[metric_name]
