import os
import logging


def setup_logger(execution_id, debug):
    base_log_dir = "logs"
    log_file = os.path.join(base_log_dir, f"execution_{execution_id}.log")
    os.makedirs(base_log_dir, exist_ok=True)

    handlers = [logging.FileHandler(log_file)]
    if not debug:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
