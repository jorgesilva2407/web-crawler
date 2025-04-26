import logging
import requests
from queue import Queue
from timer import timeit
from protego import Protego
from datetime import datetime


class PoliteQueue(Queue):
    def __init__(self, base_url: str):
        super().__init__()
        self._base_url = base_url
        self._crawl_delay = None
        self._robots = None
        self._last_crawled = None
        self._crawl_settings_initialized = False

        self._retries = 0
        self.__PARSE_ROBOTS_RETRIES = 3

    def enque(self, url: str):
        if not self._robots or self._robots.can_fetch("*", url):
            super().put(url)

    def deque(self):
        url = super().get()
        self._last_crawled = datetime.now()
        return url

    def can_crawl(self):
        if not self._crawl_settings_initialized:
            self._initialize_crawl_settings()

        if not self._crawl_settings_initialized:
            return False

        now = datetime.now()
        elapsed_time = (now - self._last_crawled).total_seconds()
        return elapsed_time >= self._crawl_delay

    def _initialize_crawl_settings(self):
        self._last_crawled = datetime.now()
        try:
            self._crawl_delay, self._robots = self._parse_robots_txt(self._base_url)
        except requests.exceptions.Timeout:
            if self._retries < self.__PARSE_ROBOTS_RETRIES:
                self._retries += 1
                return False
            else:
                logging.info(
                    f"Error: Failed to fetch robots.txt after {self.__PARSE_ROBOTS_RETRIES} retries, ignoring robots.txt"
                )
                self._crawl_delay, self._robots = self._ignore_robots()
        self._crawl_settings_initialized = True

    @timeit
    def _parse_robots_txt(self, base_url: str):
        robots_url = f"{base_url}/robots.txt"
        try:
            response = requests.get(robots_url, timeout=2)
            if response.status_code == 200:
                robots = Protego.parse(response.text)
                return robots.crawl_delay("*") or 0.1, robots
            else:
                return self._ignore_robots()
        except requests.exceptions.Timeout as e:
            logging.info(f"Error: Timeout while fetching {robots_url}, ignoring robots.txt")
            raise e
        except Exception:
            return self._ignore_robots()

    def _ignore_robots(self):
        return 0.1, None
