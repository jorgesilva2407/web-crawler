import logging
from crawler import Crawler
from datetime import datetime
from logger import setup_logger
from utils import parse_args, parse_seeds


def main():
    """
    Main function to set up the crawler and start the crawling process.
    """
    args = parse_args() # Parse command line arguments
    seeds = parse_seeds(args.seeds) # Parse the seeds from the command line arguments
    execution_id = datetime.now().strftime("%Y%m%d%H%M%S") # Generate a unique execution ID based on the current timestamp
    setup_logger(execution_id=execution_id, debug=args.debug) # Set up the logger with the execution ID and debug mode

    # Set up the crawler with the parsed arguments
    crawler = Crawler(
        execution_id=execution_id,
        limit=args.limit,
        debug=args.debug,
        threads=args.threads,
        seeds=seeds,
    )

    # Log the start of the crawler
    logging.info(f"Starting crawler with execution ID: {execution_id}")
    logging.info(f"Limit: {args.limit}")
    logging.info(f"Debug mode: {args.debug}")
    logging.info(f"Threads: {args.threads}")
    logging.info(f"Seeds: {seeds}")
    logging.info(f"Starting crawl at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Start the crawling process
    crawler.crawl()


if __name__ == "__main__":
    main()
