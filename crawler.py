import time
import json
import logging
import requests
import threading
from writer import Writer
from bs4 import BeautifulSoup
from frontier import Frontier
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

        self._writer = Writer(execution_id, limit, self._finished_event)
        Frontier(self._finished_event, seeds)

    def crawl(self):
        threads = []

        for _ in range(self._num_threads):
            thread = threading.Thread(target=self._crawl)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def _crawl(self):
        while not self._finished_event.is_set():
            url = Frontier.get()

            if url is None:
                continue

            response = self._fetch(url)

            if response is None:
                continue

            parsed_html = self._parse_html(response)

            if parsed_html is None:
                continue

            if self._debug:
                self._print_debug_info(url, parsed_html)

            extracted_urls = self._extract_urls(parsed_html)
            base_and_normalized_url = [
                (base_url(url), normalized_url(url))
                for url in extracted_urls
                if is_valid_url(url)
            ]

            self._writer.write(url, response)
            Frontier.add_range(base_and_normalized_url)

    def _fetch(self, url: str):
        try:
            logging.info(f"Fetching URL: {url}")

            response = requests.get(
                url,
                timeout=0.5,
            )
            if "text/html" in response.headers.get("Content-Type", ""):
                return response

            logging.info(f"Error: URL {url} is not HTML, skipping.")
        except Exception as e:
            logging.info(f"Error fetching URL {url}: {e}")

        return None

    def _parse_html(self, response):
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            return soup
        except Exception as e:
            logging.info(f"Error parsing HTML: {e}")
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
