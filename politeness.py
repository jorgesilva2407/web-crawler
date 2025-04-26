from queue import Queue
from datetime import datetime
import requests
from protego import Protego


class PoliteQueue(Queue):
    def __init__(self, base_url: str):
        super().__init__()
        self._last_crawled = datetime.now()
        self._crawl_delay, self._robots = self._parse_robots_txt(base_url)

    def _parse_robots_txt(self, base_url: str):
        robots_url = f"{base_url}/robots.txt"
        try:
            response = requests.get(robots_url)
            if response.status_code == 200:
                robots = Protego.parse(response.text)
                return robots.crawl_delay(), robots
            else:
                return self._ignore_robots()
        except requests.RequestException as e:
            return self._ignore_robots()

    def _ignore_robots(self):
        return 0.1, None

    def enque(self, url: str):
        if self._robots:
            if not self._robots.can_fetch("*", url):
                return False
        super().put(url)

    def deque(self):
        url = super().get()
        self._last_crawled = datetime.now()
        return url

    def can_crawl(self):
        now = datetime.now()
        elapsed_time = (now - self._last_crawled).total_seconds()
        return elapsed_time >= self._crawl_delay and not self.empty()
