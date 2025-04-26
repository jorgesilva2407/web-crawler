from functools import wraps


def Lock(lock):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)

        return wrapper

    return decorator
