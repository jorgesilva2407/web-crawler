import json
import time
import random
import logging
import requests
import threading
from writer import Writer
from session import Session
from bs4 import BeautifulSoup
from politeness import Politeness
from utils import base_url, normalized_url, is_valid_url


class Crawler:
    def __init__(
        self,
        execution_id: str,
        limit: int,
        debug: bool,
        threads: int,
        seeds: list[str],
    ):
        self._debug = debug
        self._num_threads = threads
        self._finished_event = threading.Event()

        self._lock = threading.Lock()
        self._visited = set()
        self._frontier: list[str] = [normalized_url(seed) for seed in seeds]
        self._politeness = Politeness()
        self._writer = Writer(execution_id, limit, self._finished_event)

    def crawl(self):
        threads = []

        for _ in range(self._num_threads):
            thread = threading.Thread(target=self._crawl)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def _crawl(self):
        session = Session()
        while not self._finished_event.is_set():
            url = self._get_from_frontier()

            if url is None:
                time.sleep(0.2)
                continue

            info = self._politeness.get_page_info(base_url(url))

            with info.lock:
                if not info.initialized:
                    info.fetch_robots(session)

                if info.robots:
                    if not info.robots.can_fetch("*", url):
                        logging.info(f"Warning: URL blocked by robots.txt: {url}")
                        continue

                time_to_wait = info.time_to_wait()
                if time_to_wait > 0:
                    logging.info(
                        f"Warning: Waiting for {time_to_wait} seconds before crawling {url}"
                    )
                    time.sleep(time_to_wait)

                logging.info(f"Fetching URL: {url}")
                response = self._fetch(url, session)
                if response is None:
                    continue
                logging.info(f"Success: Fetched URL {url}")

                logging.info(f"Parsing HTML for URL: {url}")
                parsed_html = self._parse_html(url, response)
                if parsed_html is None:
                    continue
                logging.info(f"Success: Parsed HTML for URL {url}")

                if self._debug:
                    self._print_debug_info(url, parsed_html)

                logging.info(f"Extracting URLs from {url}")
                extracted_urls = self._extract_urls(parsed_html)
                valid_urls = [url for url in extracted_urls if is_valid_url(url)]
                normalized_urls = [normalized_url(url) for url in valid_urls]
                authorized_urls = [
                    url for url in normalized_urls if url and info.can_fetch(url)
                ]
                logging.info(
                    f"Success: Extracted {len(authorized_urls)} URLs from {url}"
                )

                self._writer.write(url, response)
                self._add_to_frontier(normalized_urls)

    def _get_from_frontier(self):
        with self._lock:
            if len(self._frontier) == 0:
                return None
            idx = random.randrange(0, len(self._frontier))
            return self._frontier.pop(idx)

    def _fetch(self, url: str, session: Session):
        try:
            response = session.get(url, timeout=0.5)
            if self._is_text_html(response):
                return response
            logging.info(f"Error: URL {url} is not HTML, skipping.")
        except Exception as e:
            logging.info(f"Error fetching URL {url}: {e}")
        return None

    def _is_text_html(self, response):
        content_type = response.headers.get("Content-Type", "")
        return "text/html" in content_type

    def _parse_html(self, url, response):
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            return soup
        except Exception as e:
            logging.info(f"Error parsing HTML for URL {url}: {e}")
            return None

    def _print_debug_info(self, url, soup):
        metadata = {
            "URL": url,
            "Title": self._extract_title(soup),
            "Text": self._extract_twenty_words(soup),
            "Timestamp": int(time.time()),
        }
        print(json.dumps(metadata))

    def _extract_title(self, soup):
        title = soup.title.string if soup.title else "No title found"
        return title

    def _extract_twenty_words(self, soup):
        text = soup.get_text()
        words = text.split()[:20]
        return " ".join(words)

    def _extract_urls(self, soup):
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("http://") or href.startswith("https://"):
                links.append(href)

        return links

    def _add_to_frontier(self, urls):
        with self._lock:
            self._frontier.extend([url for url in urls if url not in self._visited])
