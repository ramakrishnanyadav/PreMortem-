"""
statuspage_poller.py
--------------------
Polls public StatusPage.io APIs for major SaaS services.
Maps text statuses to numeric anomaly indicators.
"""
import time
import asyncio
import structlog
from typing import Dict, List
from premortem.backend.ingestion.base_poller import BasePoller, CircuitBreakerOpenException

logger = structlog.get_logger(__name__)

# A mapping of service names to their StatusPage.io summary.json endpoints
STATUS_PAGES = {
    "github": "https://www.githubstatus.com/api/v2/summary.json",
    "vercel": "https://www.vercel-status.com/api/v2/summary.json",
    "cloudflare": "https://www.cloudflarestatus.com/api/v2/summary.json",
    "datadog": "https://status.datadoghq.com/api/v2/summary.json",
    "npm": "https://status.npmjs.org/api/v2/summary.json",
}

# StatusPage.io indicator mapping to numeric values
# none, minor, major, critical
INDICATOR_MAP = {
    "none": 0.0,
    "minor": 1.0,
    "major": 2.0,
    "critical": 3.0,
    "maintenance": 0.5
}

class StatusPagePoller(BasePoller):
    def __init__(self, buffer_manager, service_name: str, url: str, poll_interval_seconds: int = 30):
        super().__init__(name=f"statuspage_poller_{service_name}", poll_interval_seconds=poll_interval_seconds)
        self.buffer_manager = buffer_manager
        self.service_name = service_name
        self.url = url

    async def poll(self) -> None:
        try:
            start_time = time.time()
            resp = await self.fetch_with_retry(self.url)
            data = resp.json()
            latency_ms = (time.time() - start_time) * 1000.0

            # Atlassian Statuspage format
            status_indicator = "none"
            if "status" in data and "indicator" in data["status"]:
                status_indicator = data["status"]["indicator"]
                
            numeric_status = INDICATOR_MAP.get(status_indicator.lower(), 0.0)
            
            if self.buffer_manager:
                self.buffer_manager.get_buffer(f"{self.service_name}-status-severity").append(numeric_status)
                self.buffer_manager.get_buffer(f"{self.service_name}-status-latency").append(latency_ms)

            logger.debug("statuspage_polled", service=self.service_name, status=status_indicator, latency=latency_ms)
            
        except CircuitBreakerOpenException:
            pass # Circuit open for this poller instance
        except Exception as e:
            logger.warning("statuspage_poll_error", service=self.service_name, error=str(e))

