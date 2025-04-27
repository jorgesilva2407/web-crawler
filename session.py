import requests


class Session:
    """
    A class that manages a session with a maximum number of requests.
    It automatically closes and reopens the session after a specified number of requests.
    """

    def __init__(self):
        self._session = requests.Session()
        self._request_count = 0
        self._max_requests = 500

    def get(self, *args, **kwargs):
        """
        Sends a GET request using the session.
        If the maximum number of requests is reached, the session is closed and reopened.
        Args:
            *args: Positional arguments to be passed to the requests.get method.
            **kwargs: Keyword arguments to be passed to the requests.get method.
        Returns:
            Response: The response object returned by the requests.get method.
        """
        if self._request_count >= self._max_requests:
            self._session.close()
            self._session = requests.Session()
            self._request_count = 0

        self._request_count += 1
        response = self._session.get(*args, **kwargs)
        return response
