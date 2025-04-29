import os
import time
import logging
import threading
from dataclasses import dataclass
from warcio.warcwriter import WARCWriter
from warcio.statusandheaders import StatusAndHeaders
from io import BytesIO
from requests import Response
from lock import Lock


@dataclass
class Page:
    """
    Class representing a web page.
    Attributes:
        url (str): The URL of the page.
        content (Response): The HTTP response content of the page.
    """

    url: str
    content: Response


class Writer:
    """
    Singleton class for writing web pages to disk in WARC format.
    Attributes:
        _instance (Writer): The singleton instance of the Writer class.
        _lock (threading.RLock): A reentrant lock for thread safety.
        _buffer (list[Page]): Buffer to hold pages before writing to disk.
        _flush_count (int): Counter for the number of flushes performed.
        _base_dir (str): Base directory for output files.
        _num_crawled (int): Number of pages crawled.
        _crawl_limit (int): Limit on the number of pages to crawl.
        _finished_event (threading.Event): Event to signal completion of crawling.
    """

    _instance = None
    _lock: threading.RLock = threading.RLock()
    _buffer: list[Page] = []
    _flush_count: int = 0
    _base_dir: str = None
    _num_crawled: int = 0
    _crawl_limit: int = None
    _finished_event: threading.Event = None

    __BUFFER_SIZE = 1000
    __NUM_FLUSH_RETRIES = 60

    def __new__(
        cls,
        execution_id: str,
        crawl_limit: int,
        finished_event: threading.Event,
    ):
        """
        Create a new instance of the Writer class or return the existing instance.
        Args:
            execution_id (str): Unique identifier for the execution.
            crawl_limit (int): Limit on the number of pages to crawl.
            finished_event (threading.Event): Event to signal completion of crawling.
        Returns:
            Writer: The singleton instance of the Writer class.
        """
        if not cls._instance:
            cls._crawl_limit = crawl_limit  # Set the crawl limit
            cls._finished_event = finished_event  # Set the finished event
            Writer._base_dir = (
                f"output/{execution_id}"  # Set the base directory for output files
            )
            os.makedirs(
                Writer._base_dir
            )  # Create the base directory if it doesn't exist
            cls._instance = super(Writer, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def flush():
        """
        Flush the buffer to disk by writing the pages in WARC format.
        This method creates a new WARC file for each flush and writes the pages
        to it. The file is named based on the flush count.
        """
        logging.info(f"Flushing {len(Writer._buffer)} pages to disk")
        if len(Writer._buffer) == 0:
            # No pages to flush
            return

        file_path = f"{Writer._base_dir}/output-{Writer._flush_count}.warc.gz"

        with open(file_path, "wb") as stream:
            writer = WARCWriter(stream, gzip=True)
            for page in Writer._buffer:
                # Sets the headers for the WARC record
                http_headers = StatusAndHeaders(
                    f"{page.content.status_code} {page.content.reason}",
                    list(page.content.headers.items()),
                    protocol="HTTP/1.1",
                )

                # Write the WARC record
                with BytesIO(page.content.content) as payload:
                    record = writer.create_warc_record(
                        page.url,
                        "response",
                        payload=payload,
                        http_headers=http_headers,
                    )

                    writer.write_record(record)

        Writer._buffer = []  # Clear the buffer after flushing
        Writer._flush_count += 1  # Increment the flush count

    @staticmethod
    @Lock(_lock)
    def write(url: str, content: Response):
        """
        Write a page to the buffer. If the buffer reaches the specified size,
        flush the buffer to disk. If the crawl limit is reached, signal completion.
        Args:
            url (str): The URL of the page.
            content (Response): The HTTP response content of the page.
        """
        Writer._buffer.append(Page(url, content))
        Writer._num_crawled += 1

        if Writer._num_crawled % 100 == 0:
            logging.info(f"Crawled pages: {Writer._num_crawled}")

        # Flush the buffer if it reaches the specified size
        if len(Writer._buffer) >= Writer.__BUFFER_SIZE:
            # Retry flushing the buffer in case of failure
            for i in range(Writer.__NUM_FLUSH_RETRIES):
                try:
                    Writer.flush()
                    return
                except Exception as e:
                    logging.info("Error flushing buffer, retry attempt: %d", i + 1)
                    time.sleep(1)  # Sleep for a second before retrying

        # Check if the crawl limit is reached
        if Writer._num_crawled >= Writer._crawl_limit:
            Writer._finished_event.set()  # Signal that crawling is finished
            Writer.flush()  # Flush any remaining pages to disk
            logging.info(
                f"Finished crawling. Total pages crawled: {Writer._num_crawled}"
            )
