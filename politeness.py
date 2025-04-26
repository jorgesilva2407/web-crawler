import logging
import requests
from queue import Queue
from protego import Protego
from datetime import datetime


class PoliteQueue(Queue):
    def __init__(self, base_url: str):
        super().__init__()
        self._base_url = base_url
        self._crawl_delay = None
        self._robots = None
        self._last_crawled = None

    def _parse_robots_txt(self, base_url: str):
        robots_url = f"{base_url}/robots.txt"
        try:
            response = requests.get(robots_url)
            if response.status_code == 200:
                robots = Protego.parse(response.text)
                return robots.crawl_delay("*") or 0.1, robots
            else:
                return self._ignore_robots()
        except Exception:
            return self._ignore_robots()

    def _ignore_robots(self):
        return 0.1, None

    def enque(self, url: str):
        if not self._robots or self._robots.can_fetch("*", url):
            super().put(url)

    def deque(self):
        url = super().get()
        self._last_crawled = datetime.now()
        return url

    def can_crawl(self):
        if not self._last_crawled:
            self._last_crawled = datetime.now()
            self._crawl_delay, self._robots = self._parse_robots_txt(self._base_url)

        now = datetime.now()
        elapsed_time = (now - self._last_crawled).total_seconds()
        return elapsed_time >= self._crawl_delay and not self.empty()
