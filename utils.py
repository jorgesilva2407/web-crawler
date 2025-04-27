import logging
import argparse
import url_normalize
from urllib.parse import urlparse


def parse_args():
    parser = argparse.ArgumentParser(description="Web Crawler")
    parser.add_argument(
        "-s",
        "--seeds",
        type=str,
        required=True,
        help="File containing seed URLs (one per line)",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        required=True,
        help="Maximum number of pages to crawl",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=16,
        help="Number of threads to use for crawling (default: 16)",
    )
    return parser.parse_args()


def parse_seeds(seeds_file):
    with open(seeds_file, "r") as f:
        seeds = [line.strip() for line in f.readlines()]
    return seeds


def base_url(url: str) -> str:
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def normalized_url(url: str) -> str:
    try:
        return url_normalize.url_normalize(url)
    except Exception as e:
        logging.error(f"Error normalizing URL {url}: {e}")
        return None


def is_valid_url(url: str):
    try:
        parsed = urlparse(url)
        return all([parsed.scheme in ("http", "https"), parsed.netloc])
    except Exception:
        return False
