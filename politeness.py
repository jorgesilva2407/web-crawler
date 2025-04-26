import logging
from threading import Lock
from protego import Protego
from session import Session
from datetime import datetime, timedelta


class PageInfo:
    def __init__(self, url: str):
        self.url = url
        self.lock = Lock()
        self.initialized = False
        self.robots = None
        self.crawl_delay_float = None
        self.crawl_delay_timedelta = None
        self.last_crawled = None

    def time_to_wait(self):
        time_to_crawl = self.last_crawled + self.crawl_delay_timedelta
        time_to_wait = (time_to_crawl - datetime.now()).total_seconds()
        return max(0, time_to_wait)

    def can_fetch(self, url: str):
        if not self.robots:
            return True
        return self.robots.can_fetch("*", url)

    def fetch_robots(self, session: Session):
        robots_url = f"{self.url}/robots.txt"
        try:
            response = session.get(robots_url, timeout=2)
            if response.status_code == 200:
                robots = Protego.parse(response.text)
                self._initialize(
                    robots=robots,
                    crawl_delay=robots.crawl_delay("*") or 0.1,
                    last_crawled=datetime.now(),
                )
                logging.info(f"Success: Fetched robots.txt for {self.url}")
            else:
                self._initialize()
                logging.info(
                    f"Error: Failed to fetch robots.txt for {self.url}: {response.status_code}"
                )
        except Exception as e:
            self._initialize()
            logging.error(f"Exception: {e} while fetching robots.txt for {self.url}")

    def _initialize(self, robots=None, crawl_delay=0.1):
        self.robots = robots
        self.crawl_delay_float = crawl_delay
        self.crawl_delay_timedelta = timedelta(seconds=crawl_delay)
        self.last_crawled = datetime.now()
        self.initialized = True


class Politeness:
    _instance = None
    _page_info_registry: dict[str, PageInfo] = {}
    _lock: Lock = Lock()

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(Politeness, cls).__new__(cls)
        return cls._instance

    def get_page_info(self, base_url: str) -> PageInfo:
        with self._lock:
            if base_url not in self._page_info_registry:
                self._page_info_registry[base_url] = PageInfo(base_url)
            return self._page_info_registry[base_url]
