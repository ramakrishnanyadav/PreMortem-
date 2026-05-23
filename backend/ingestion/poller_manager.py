"""
poller_manager.py
-----------------
Orchestrates all pollers using APScheduler.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import structlog
from typing import List

from premortem.backend.ingestion.base_poller import BasePoller

logger = structlog.get_logger(__name__)

class PollerManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.pollers: List[BasePoller] = []

    def register_poller(self, poller: BasePoller):
        self.pollers.append(poller)
        self.scheduler.add_job(
            poller.poll,
            'interval',
            seconds=poller.poll_interval_seconds,
            id=poller.name,
            replace_existing=True,
            max_instances=1
        )
        logger.info("poller_registered", name=poller.name, interval_s=poller.poll_interval_seconds)

    def start(self):
        logger.info("starting_poller_manager")
        self.scheduler.start()

    async def shutdown(self):
        logger.info("shutting_down_poller_manager")
        self.scheduler.shutdown()
        for poller in self.pollers:
            await poller.close()
