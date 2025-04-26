import threading
from frontier import Frontier
from writer import Writer


class Crawler:
    def __init__(
        self,
        execution_id: str,
        limit: int,
        debug: bool,
        threads: int,
        seeds: list[str],
    ):
        self._limit = limit
        self._num_crawled = 0
        self._debug = debug
        self._num_threads = threads
        self._writer = Writer(execution_id)
        self._frontier = Frontier(seeds)

    def crawl(self):
        threads = []
        
        for _ in range(self._num_threads):
            thread = threading.Thread(target=self._crawl)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def _crawl(self):
        pass

    def _crawl_page(self, url: str):
        pass

    def _get_links(self, url: str):
        pass

    def _save_page(self, url: str, content: str):
        pass
