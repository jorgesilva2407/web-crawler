from functools import wraps


def Lock(lock):
    """
    Decorator to acquire a lock before executing a function.
    Args:
        lock (threading.Lock): The lock to be acquired.
    Returns:
        callable: The wrapped function with lock acquisition.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)

        return wrapper

    return decorator
