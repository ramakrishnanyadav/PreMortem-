"""
npm_poller.py
-------------
Polls the public npm registry to measure package resolution latency.
This acts as a live proxy for npm registry health.
"""
import time
import structlog
from premortem.backend.ingestion.base_poller import BasePoller, CircuitBreakerOpenException

logger = structlog.get_logger(__name__)

class NpmPoller(BasePoller):
    def __init__(self, buffer_manager, poll_interval_seconds: int = 30):
        super().__init__(name="npm_poller", poll_interval_seconds=poll_interval_seconds)
        self.buffer_manager = buffer_manager

    async def poll(self) -> None:
        try:
            start_time = time.time()
            # Fetch metadata for a highly downloaded package to proxy registry health
            # We use 'react' as it's almost constantly hit
            resp = await self.fetch_with_retry(
                url="https://registry.npmjs.org/react"
            )
            latency_ms = (time.time() - start_time) * 1000.0
            
            if self.buffer_manager:
                self.buffer_manager.get_buffer("npm-registry-resolution-latency").append(latency_ms)

            logger.info("npm_poller_success", latency_ms=latency_ms)

        except CircuitBreakerOpenException:
            pass
        except Exception as e:
            logger.error("npm_poller_failed", error=str(e))
