"""
github_poller.py
----------------
Polls GitHub API for live metrics: API latency, rate limit status, and proxy for Actions queue depth.
"""
import time
import structlog
import httpx
from premortem.backend.ingestion.base_poller import BasePoller, CircuitBreakerOpenException
from premortem.backend.config import settings

logger = structlog.get_logger(__name__)

class GitHubPoller(BasePoller):
    def __init__(self, buffer_manager, poll_interval_seconds: int = 30):
        super().__init__(name="github_poller", poll_interval_seconds=poll_interval_seconds)
        self.buffer_manager = buffer_manager
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PreMortem-SRE-Agent/1.0"
        }
        if settings.GITHUB_TOKEN:
            self.headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    async def poll(self) -> None:
        try:
            # 1. Fetch Rate Limits & API Latency
            start_time = time.time()
            rate_limit_resp = await self.fetch_with_retry(
                url="https://api.github.com/rate_limit", 
                headers=self.headers
            )
            latency_ms = (time.time() - start_time) * 1000.0
            
            rate_limit_data = rate_limit_resp.json()
            core_remaining = rate_limit_data.get("resources", {}).get("core", {}).get("remaining", 0)
            
            # Push to buffers
            if self.buffer_manager:
                self.buffer_manager.get_buffer("github-api-latency").append(latency_ms)
                self.buffer_manager.get_buffer("github-rate-limit-remaining").append(core_remaining)

            # 2. Proxy for Actions Queue Depth 
            # We query a highly active public repository (e.g., 'microsoft/vscode')
            # and count how many workflow runs are currently in 'queued' or 'in_progress' state.
            workflow_resp = await self.fetch_with_retry(
                url="https://api.github.com/repos/microsoft/vscode/actions/runs",
                headers=self.headers,
                params={"status": "queued", "per_page": 1}
            )
            workflow_data = workflow_resp.json()
            queue_depth = workflow_data.get("total_count", 0)
            
            if self.buffer_manager:
                self.buffer_manager.get_buffer("github-actions-queue_depth").append(queue_depth)

            logger.info("github_poller_success", latency_ms=latency_ms, remaining=core_remaining, queue_depth=queue_depth)

        except CircuitBreakerOpenException:
            # Silently pass, logged by base class
            pass
        except Exception as e:
            logger.error("github_poller_failed", error=str(e))
