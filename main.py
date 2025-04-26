from utils import parse_args, parse_seeds
from crawler import Crawler
from datetime import datetime


def main():
    args = parse_args()
    seeds = parse_seeds(args.seeds)
    execution_id = datetime.now().strftime("%Y%m%d%H%M%S")
    crawler = Crawler(
        limit=args.limit,
        debug=args.debug,
        threads=args.threads,
        seeds=seeds,
    )
    crawler.crawl()


if __name__ == "__main__":
    main()
