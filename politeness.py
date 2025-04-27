import logging
from threading import Lock
from protego import Protego
from session import Session
from datetime import datetime, timedelta


class PageInfo:
    """
    Class representing the politeness information for a web page.
    Attributes:
        url (str): The URL of the page.
        lock (Lock): A lock for thread safety.
        initialized (bool): Flag indicating if the object is initialized.
        robots (Protego): Robots.txt parser object.
        crawl_delay_float (float): Crawl delay in seconds.
        crawl_delay_timedelta (timedelta): Crawl delay as a timedelta object.
        last_crawled (datetime): Timestamp of the last crawl.
    """

    def __init__(self, url: str):
        """
        Initialize the PageInfo object.
        Args:
            url (str): The URL of the page.
        """
        self.url = url
        self.lock = Lock()
        self.initialized = False
        self.robots = None
        self.crawl_delay_float = None
        self.crawl_delay_timedelta = None
        self.last_crawled = None

    def time_to_wait(self):
        """
        Calculate the time to wait before the next crawl.
        Returns:
            int: The time in seconds to wait before the next crawl.
        """
        time_to_crawl = self.last_crawled + self.crawl_delay_timedelta
        time_to_wait = (time_to_crawl - datetime.now()).total_seconds()
        return max(0, time_to_wait)

    def can_fetch(self, url: str):
        """
        Check if the URL can be fetched based on the robots.txt rules.
        Args:
            url (str): The URL to check.
        Returns:
            bool: True if the URL can be fetched, False otherwise.
        """
        if not self.robots:
            return True
        return self.robots.can_fetch("*", url)

    def fetch_robots(self, session: Session):
        """
        Fetch the robots.txt file for the URL and initialize the politeness settings.
        Args:
            session (Session): The session object to use for fetching the robots.txt file.
        """
        robots_url = f"{self.url}/robots.txt"
        try:
            response = session.get(robots_url, timeout=2)
            if response.status_code == 200:
                # Parse the robots.txt file
                robots = Protego.parse(response.text)
                self._initialize(
                    robots=robots,
                    crawl_delay=robots.crawl_delay("*") or 0.1,
                )
                logging.info(f"Success: Fetched robots.txt for {self.url}")
            else:
                # If the robots.txt file is not found or has an error, initialize with default values
                self._initialize()
                logging.info(
                    f"Error: Failed to fetch robots.txt for {self.url}: {response.status_code}"
                )
        except Exception as e:
            # If there is an error fetching the robots.txt file, initialize with default values
            self._initialize()
            logging.error(f"Exception: {e} while fetching robots.txt for {self.url}")

    def _initialize(self, robots=None, crawl_delay=0.1):
        """
        Initialize the PageInfo object with the given robots.txt and crawl delay.
        Args:
            robots (Protego): The robots.txt parser object.
            crawl_delay (float): The crawl delay in seconds.
        """
        self.robots = robots
        self.crawl_delay_float = crawl_delay
        self.crawl_delay_timedelta = timedelta(seconds=crawl_delay)
        self.last_crawled = datetime.now()
        self.initialized = True


class Politeness:
    """
    Singleton class to manage politeness settings for web crawling.
    Attributes:
        _instance (Politeness): The singleton instance of the class.
        _page_info_registry (dict[str, PageInfo]): Registry of PageInfo objects for different URLs.
        _lock (Lock): A lock for thread safety.
    """

    _instance = None
    _page_info_registry: dict[str, PageInfo] = {}
    _lock: Lock = Lock()

    def __new__(cls):
        """
        Create a new instance of the Politeness class if it doesn't exist.
        Returns:
            Politeness: The singleton instance of the class.
        """
        if not cls._instance:
            cls._instance = super(Politeness, cls).__new__(cls)
        return cls._instance

    def get_page_info(self, base_url: str) -> PageInfo:
        """
        Get the PageInfo object for the given base URL.
        Args:
            base_url (str): The base URL of the page.
        Returns:
            PageInfo: The PageInfo object for the given base URL.
        """
        with self._lock:
            if base_url not in self._page_info_registry:
                self._page_info_registry[base_url] = PageInfo(base_url)
            return self._page_info_registry[base_url]
