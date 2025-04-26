import os
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

    __BUFFER_SIZE = 1000

    def __new__(cls, execution_id: str):
        if not cls._instance:
            Writer._base_dir = f"output/{execution_id}"
            os.makedirs(Writer._base_dir)
            cls._instance = super(Writer, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def flush():
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

                record = writer.create_warc_record(
                    page.url,
                    "response",
                    payload=BytesIO(page.content.content),
                    http_headers=http_headers,
                )

                writer.write_record(record)

        Writer._buffer = []
        Writer._flush_count += 1

    @staticmethod
    @Lock(_lock)
    def write(url: str, content: Response):
        Writer._buffer.append(Page(url, content))

        if len(Writer._buffer) >= Writer.__BUFFER_SIZE:
            Writer.flush()
