"""
base_poller.py
--------------
Abstract base class for all data ingestion pollers.
Handles retries, exponential backoff, circuit breaking, and AsyncClient lifecycle.
"""
import asyncio
import httpx
import structlog
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)

class CircuitBreakerOpenException(Exception):
    pass

class BasePoller(ABC):
    def __init__(self, name: str, poll_interval_seconds: int = 30):
        self.name = name
        self.poll_interval_seconds = poll_interval_seconds
        
        # Circuit breaker state
        self.failure_count = 0
        self.max_failures = 5
        self.circuit_open_until = 0.0
        self.circuit_cooldown = 60.0 # Wait 60s before trying again after circuit opens
        
        # Retry settings
        self.max_retries = 3
        self.base_backoff = 1.0 # 1 second
        
        # HTTP Client configuration
        # Timeout is strictly 10 seconds as per specs
        self.client_timeout = httpx.Timeout(10.0)
        self.client: Optional[httpx.AsyncClient] = None

    async def _init_client(self):
        """Lazy initialization of the httpx AsyncClient to ensure it's in the right event loop"""
        if self.client is None or self.client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            self.client = httpx.AsyncClient(timeout=self.client_timeout, limits=limits)
            logger.debug("poller_client_initialized", poller=self.name)

    async def fetch_with_retry(self, url: str, headers: Dict[str, str] = None, params: Dict[str, Any] = None) -> httpx.Response:
        """
        Executes an HTTP GET request with exponential backoff and circuit breaker logic.
        """
        await self._init_client()
        
        # Check circuit breaker
        if time.time() < self.circuit_open_until:
            logger.warning("poller_circuit_breaker_open", poller=self.name, open_until=self.circuit_open_until)
            raise CircuitBreakerOpenException(f"Circuit open for {self.name}")

        for attempt in range(self.max_retries):
            try:
                response = await self.client.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                # Reset circuit breaker on success
                if self.failure_count > 0:
                    logger.info("poller_circuit_breaker_reset", poller=self.name)
                    self.failure_count = 0
                
                return response
            
            except httpx.HTTPStatusError as e:
                # E.g., rate limits (429) or server errors (5xx)
                if e.response.status_code not in [429, 500, 502, 503, 504]:
                    self._record_failure()
                    raise # Don't retry 400s or 404s
                
                logger.warning("poller_http_error", poller=self.name, url=url, status=e.response.status_code, attempt=attempt+1)
            
            except httpx.RequestError as e:
                # Network errors, timeouts
                logger.warning("poller_request_error", poller=self.name, url=url, error=str(e), attempt=attempt+1)

            # Calculate backoff with jitter
            backoff = self.base_backoff * (2 ** attempt) + (time.time() % 0.1)
            if attempt < self.max_retries - 1:
                logger.debug("poller_retrying", poller=self.name, wait_seconds=backoff)
                await asyncio.sleep(backoff)

        # If we reach here, all retries failed
        self._record_failure()
        raise Exception(f"Failed to fetch {url} after {self.max_retries} attempts")

    def _record_failure(self):
        """Records a failure and potentially opens the circuit breaker"""
        self.failure_count += 1
        if self.failure_count >= self.max_failures:
            self.circuit_open_until = time.time() + self.circuit_cooldown
            logger.error("poller_circuit_breaker_tripped", poller=self.name, cooldown_seconds=self.circuit_cooldown)

    @abstractmethod
    async def poll(self) -> None:
        """
        Implement this method to define exactly what to fetch and how to push it to the detection engine.
        Must catch specific exceptions within the implementation.
        """
        pass

    async def close(self):
        """Clean up the httpx client"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
            logger.debug("poller_client_closed", poller=self.name)
