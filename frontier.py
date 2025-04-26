import url_normalize
from politeness import PoliteQueue
from urllib.parse import urlparse
import threading
from lock import Lock


class Frontier:
    _instance = None
    _queues: dict[str, PoliteQueue] = {}
    _visited: set[str] = set()
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, seeds: list[str]):
        if not cls._instance:
            for seed in seeds:
                Frontier.add(seed)
            cls._instance = super(Frontier, cls).__new__(cls)
        return cls._instance

    @staticmethod
    @Lock(_lock)
    def add(url: str):
        normalized_url = url_normalize.url_normalize(url)

        if normalized_url in Frontier._visited:
            return

        parsed_url = urlparse(normalized_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if base_url not in Frontier._queues:
            Frontier._queues[base_url] = PoliteQueue(base_url)

        Frontier._queues[base_url].enque(normalized_url)

    @staticmethod
    @Lock(_lock)
    def get():
        for queue in Frontier._queues.values():
            if not queue.can_crawl():
                continue
            url = queue.deque()
            Frontier._visited.add(url)
            return url
        return None
