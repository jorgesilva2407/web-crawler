import random
import logging
import threading
from lock import Lock
from timer import timeit
from politeness import PoliteQueue
from utils import base_url, normalized_url


class Frontier:
    _instance = None
    _queues: dict[str, PoliteQueue] = {}
    _queued: set[str] = set()
    _lock: threading.Lock = threading.Lock()
    _consecutive_miss_counts: int = 0
    _max_consecutive_miss_counts: int = 100
    _finished_event: threading.Event = None

    def __new__(cls, finished_event, seeds: list[str]):
        if not cls._instance:
            cls._finished_event = finished_event
            Frontier.add_range(
                [(base_url(seed), normalized_url(seed)) for seed in seeds]
            )
            cls._instance = super(Frontier, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def _add(base_url: str, normalized_url: str = None):
        if normalized_url in Frontier._queued:
            return

        if base_url not in Frontier._queues:
            Frontier._queues[base_url] = PoliteQueue(base_url)

        Frontier._queued.add(normalized_url)
        Frontier._queues[base_url].enque(normalized_url)

    @timeit
    @staticmethod
    @Lock(_lock)
    def add_range(base_and_normalized_urls: list[tuple[str, str]]):
        for base_url, normalized_url in base_and_normalized_urls:
            Frontier._add(base_url, normalized_url)

    def track_miss_count(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result is None:
                Frontier._consecutive_miss_counts += 1
                if (
                    Frontier._consecutive_miss_counts
                    >= Frontier._max_consecutive_miss_counts
                ):
                    for url, queue in Frontier._queues.items():
                        print(f"Queue for {url} has {queue.qsize()} items")
                    Frontier._finished_event.set()
            else:
                Frontier._consecutive_miss_counts = 0
            return result

        return wrapper

    @timeit
    @staticmethod
    @Lock(_lock)
    @track_miss_count
    def get():
        urls = list(Frontier._queues.keys())
        if len(urls) == 0:
            return None

        url = random.choice(urls)
        queue = Frontier._queues[url]

        if queue.empty():
            Frontier._queues.pop(url)
            logging.info(
                f"Warning: Queue for {url} is empty, removing it from the frontier."
            )
            return None

        if not queue.can_crawl():
            return None

        return queue.deque()
