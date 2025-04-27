import os
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
    url: str
    content: Response


class Writer:
    _instance = None
    _lock: threading.RLock = threading.RLock()
    _buffer: list[Page] = []
    _flush_count: int = 0
    _base_dir: str = None
    _num_crawled: int = 0
    _crawl_limit: int = None
    _finished_event: threading.Event = None

    __BUFFER_SIZE = 1000

    def __new__(
        cls, execution_id: str, crawl_limit: int, finished_event: threading.Event
    ):
        if not cls._instance:
            cls._crawl_limit = crawl_limit
            cls._finished_event = finished_event
            Writer._base_dir = f"output/{execution_id}"
            os.makedirs(Writer._base_dir)
            cls._instance = super(Writer, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def flush():
        logging.info(f"Flushing {len(Writer._buffer)} pages to disk")
        if len(Writer._buffer) == 0:
            return

        file_path = f"{Writer._base_dir}/output-{Writer._flush_count}.warc.gz"

        with open(file_path, "wb") as stream:
            writer = WARCWriter(stream, gzip=True)
            for page in Writer._buffer:
                http_headers = StatusAndHeaders(
                    f"{page.content.status_code} {page.content.reason}",
                    list(page.content.headers.items()),
                    protocol="HTTP/1.1",
                )

                with BytesIO(page.content.content) as payload:
                    record = writer.create_warc_record(
                        page.url,
                        "response",
                        payload=payload,
                        http_headers=http_headers,
                    )

                    writer.write_record(record)

        Writer._buffer = []
        Writer._flush_count += 1

    @staticmethod
    @Lock(_lock)
    def write(url: str, content: Response):
        Writer._buffer.append(Page(url, content))
        Writer._num_crawled += 1

        if Writer._num_crawled % 100 == 0:
            logging.info(f"Crawled pages: {Writer._num_crawled}")

        if len(Writer._buffer) >= Writer.__BUFFER_SIZE:
            Writer.flush()
            return

        if Writer._num_crawled >= Writer._crawl_limit:
            Writer._finished_event.set()
            Writer.flush()
            logging.info(
                f"Finished crawling. Total pages crawled: {Writer._num_crawled}"
            )
