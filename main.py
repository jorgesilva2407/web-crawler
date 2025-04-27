import logging
from crawler import Crawler
from datetime import datetime
from logger import setup_logger
from utils import parse_args, parse_seeds


def main():
    args = parse_args()
    seeds = parse_seeds(args.seeds)
    execution_id = datetime.now().strftime("%Y%m%d%H%M%S")
    setup_logger(execution_id=execution_id, debug=args.debug)

    crawler = Crawler(
        execution_id=execution_id,
        limit=args.limit,
        debug=args.debug,
        threads=args.threads,
        seeds=seeds,
    )

    logging.info(f"Starting crawler with execution ID: {execution_id}")
    logging.info(f"Limit: {args.limit}")
    logging.info(f"Debug mode: {args.debug}")
    logging.info(f"Threads: {args.threads}")
    logging.info(f"Seeds: {seeds}")
    logging.info(f"Starting crawl at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    crawler.crawl()


if __name__ == "__main__":
    main()
