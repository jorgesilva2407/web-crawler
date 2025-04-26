import random
import logging
import threading
import url_normalize
from lock import Lock
from urllib.parse import urlparse
from politeness import PoliteQueue


class Frontier:
    _instance = None
    _queues: dict[str, PoliteQueue] = {}
    _queued: set[str] = set()
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

        if normalized_url in Frontier._queued:
            return

        parsed_url = urlparse(normalized_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if base_url not in Frontier._queues:
            Frontier._queues[base_url] = PoliteQueue(base_url)

        Frontier._queued.add(normalized_url)
        Frontier._queues[base_url].enque(normalized_url)

    @staticmethod
    @Lock(_lock)
    def get():
        queues = list(Frontier._queues.values())
        random.shuffle(queues)
        for queue in queues:
            if not queue.can_crawl():
                continue
            url = queue.deque()
            return url
        return None
