import json
import time
import random
import logging
import threading
from writer import Writer
from session import Session
from bs4 import BeautifulSoup
from politeness import Politeness
from utils import base_url, normalized_url, is_valid_url


class Crawler:
    """
    Class representing a web crawler.
    Attributes:
        _debug (bool): Flag to enable debug mode.
        _num_threads (int): Number of threads to use for crawling.
        _finished_event (threading.Event): Event to signal completion of crawling.
        _lock (threading.Lock): Lock for thread safety.
        _visited (set): Set of visited URLs.
        _frontier (list[str]): List of URLs to crawl.
        _queued (set): Set of queued URLs. URLs in this set should not be added to the frontier again.
        _politeness (Politeness): Politeness manager for handling crawl delays.
        _writer (Writer): Writer object for saving crawled pages.
    """

    def __init__(
        self,
        execution_id: str,
        limit: int,
        debug: bool,
        threads: int,
        seeds: list[str],
    ):
        """
        Initialize the Crawler object.
        Args:
            execution_id (str): Unique identifier for the execution.
            limit (int): Limit on the number of pages to crawl.
            debug (bool): Flag to enable debug mode.
            threads (int): Number of threads to use for crawling.
            seeds (list[str]): List of seed URLs to start crawling from.
        """
        self._debug = debug
        self._num_threads = threads
        self._finished_event = threading.Event()

        self._lock = threading.Lock()
        self._visited = set()
        self._frontier: list[str] = [normalized_url(seed) for seed in seeds]
        self._queued = set(self._frontier)
        self._politeness = Politeness()
        self._writer = Writer(execution_id, limit, self._finished_event)

    def crawl(self):
        """
        Start the crawling process using multiple threads.
        This method creates a number of threads specified by _num_threads and
        starts the crawling process in each thread. It waits for all threads to
        finish before returning.
        """
        threads = []

        # Create and start threads
        for _ in range(self._num_threads):
            thread = threading.Thread(target=self._crawl)
            threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

    def _crawl(self):
        """
        The main crawling loop for each thread.
        This method continuously fetches URLs from the frontier, checks
        politeness rules, fetches the page, parses it, extracts URLs,
        and adds new URLs to the frontier. It also handles robots.txt
        rules and crawl delays.
        """
        # Initialize session for HTTP requests
        session = Session()
        while not self._finished_event.is_set():
            url = self._get_from_frontier()  # Get a URL from the frontier

            if url is None:
                # If no URLs are left in the frontier, wait for a bit
                time.sleep(0.2)
                continue

            info = self._politeness.get_page_info(
                base_url(url)
            )  # Get politeness info for the URL

            # Locks the page so that only one thread can access it at a time
            with info.lock:
                if not info.initialized:
                    # Initialize the politeness info for the URL
                    info.fetch_robots(session)

                if info.robots:
                    # Check if the URL is allowed to be crawled
                    if not info.robots.can_fetch("*", url):
                        # If not allowed, skip the URL
                        logging.info(f"Warning: URL blocked by robots.txt: {url}")
                        continue

                time_to_wait = info.time_to_wait()  # Calculate the crawl delay
                if time_to_wait > 0:
                    # If the crawl delay is greater than 0, wait before crawling
                    logging.info(
                        f"Warning: Waiting for {time_to_wait} seconds before crawling {url}"
                    )
                    time.sleep(time_to_wait)

                logging.info(f"Fetching URL: {url}")
                response = self._fetch(url, session)  # Fetch the page
                if response is None:
                    # If the response is None, skip to the next URL
                    continue

                parsed_html = self._parse_html(url, response)  # Parse the HTML
                if parsed_html is None:
                    # If parsing failed, skip to the next URL
                    continue

                if self._debug:
                    # If in debug mode, print debug information
                    self._print_debug_info(url, parsed_html)

                extracted_urls = self._extract_urls(
                    parsed_html
                )  # Extract URLs from the page
                valid_urls = [
                    url for url in extracted_urls if is_valid_url(url)
                ]  # Filter valid URLs
                normalized_urls = [
                    normalized_url(url) for url in valid_urls
                ]  # Normalize URLs
                not_visited_queued_urls = [
                    url
                    for url in normalized_urls
                    if url and url not in self._visited and url not in self._queued
                ]  # Filter URLs that are not visited or queued
                authorized_urls = [
                    url for url in not_visited_queued_urls if info.can_fetch(url)
                ]  # Filter URLs that are allowed to be crawled
                logging.info(
                    f"Success: Extracted {len(authorized_urls)} URLs from {url}"
                )

                self._writer.write(url, response)  # Write the page to the writer
                self._visited.add(url)  # Mark the URL as visited
                self._add_to_frontier(normalized_urls)  # Add new URLs to the frontier

    def _get_from_frontier(self):
        """
        Get a URL from the frontier.
        This method randomly selects a URL from the frontier and removes it from the list.
        Returns:
            str: The selected URL from the frontier, or None if the frontier is empty.
        """
        # Locks the frontier so that only one thread can access it at a time
        with self._lock:
            if len(self._frontier) == 0:
                return None
            idx = random.randrange(0, len(self._frontier))  # Randomly select an index
            return self._frontier.pop(
                idx
            )  # Remove and return the URL from the frontier

    def _fetch(self, url: str, session: Session):
        """
        Fetch the content of a URL using the provided session.
        This method handles HTTP errors and checks if the content is HTML.
        Args:
            url (str): The URL to fetch.
            session (Session): The session object to use for fetching the URL.
        Returns:
            Response: The HTTP response object if successful, None otherwise.
        """
        try:
            response = session.get(
                url, timeout=0.5
            )  # Fetch the URL with a 0.5 second timeout
            if self._is_text_html(response):  # Check if the content is HTML
                return response
            # If the content is not HTML, log a message and skip the URL
            logging.info(f"Error: URL {url} is not HTML, skipping.")
        except Exception as e:
            # If there is an error fetching the URL, log the error and skip the URL
            logging.info(f"Error fetching URL {url}: {e}")
        return None

    def _is_text_html(self, response):
        """
        Check if the response content type is HTML.
        Args:
            response (Response): The HTTP response object.
        Returns:
            bool: True if the content type is HTML, False otherwise.
        """
        content_type = response.headers.get("Content-Type", "")
        return "text/html" in content_type

    def _parse_html(self, url, response):
        """
        Parse the HTML content of a page using BeautifulSoup.
        Args:
            url (str): The URL of the page.
            response (Response): The HTTP response object.
        Returns:
            BeautifulSoup: The parsed HTML object if successful, None otherwise.
        """
        try:
            soup = BeautifulSoup(response.text, "html.parser")  # Parse the HTML content
            return soup
        except Exception as e:
            # If there is an error parsing the HTML, log the error and return None
            logging.info(f"Error parsing HTML for URL {url}: {e}")
            return None

    def _print_debug_info(self, url, soup):
        """
        Print debug information for the crawled page.
        This method extracts the title, text, and URLs from the page and prints them in JSON format.
        Args:
            url (str): The URL of the page.
            soup (BeautifulSoup): The parsed HTML object.
        """
        metadata = {
            "URL": url,
            "Title": self._extract_title(soup),
            "Text": self._extract_twenty_words(soup),
            "Timestamp": int(time.time()),
        }
        print(json.dumps(metadata))

    def _extract_title(self, soup):
        """
        Extract the title of the page from the parsed HTML.
        Args:
            soup (BeautifulSoup): The parsed HTML object.
        Returns:
            str: The title of the page if found, "No title found" otherwise.
        """
        title = soup.title.string if soup.title else "No title found"
        return title

    def _extract_twenty_words(self, soup):
        """
        Extract the first 20 words from the parsed HTML.
        Args:
            soup (BeautifulSoup): The parsed HTML object.
        Returns:
            str: The first 20 words of the page text.
        """
        text = soup.get_text()
        words = text.split()[:20]
        return " ".join(words)

    def _extract_urls(self, soup):
        """
        Extract all valid URLs from the parsed HTML.
        Args:
            soup (BeautifulSoup): The parsed HTML object.
        Returns:
            list[str]: A list of valid URLs extracted from the page.
        """
        links = []

        # Extract all anchor tags with href attributes
        for a_tag in soup.find_all("a", href=True):
            # Get the href attribute of the anchor tag
            href = a_tag["href"]
            if href.startswith("http://") or href.startswith("https://"):
                # Basic check for valid URLs
                links.append(href)

        return links

    def _add_to_frontier(self, urls):
        """
        Add new URLs to the frontier.
        This method checks if the URLs are not already visited or queued before adding them.
        Args:
            urls (list[str]): A list of URLs to add to the frontier.
        """
        # Locks the frontier so that only one thread can access it at a time
        with self._lock:
            self._frontier.extend(
                [url for url in urls if url not in self._visited]
            )  # Adds the URLs to the frontier
            self._queued.update(urls)  # Adds the URLs to the queued set
