import argparse


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
        default=8,
        help="Number of threads to use for crawling (default: 8)",
    )
    return parser.parse_args()


def parse_seeds(seeds_file):
    with open(seeds_file, "r") as f:
        seeds = [line.strip() for line in f.readlines()]
    return seeds
