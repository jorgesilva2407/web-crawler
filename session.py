import requests


class Session:
    def __init__(self):
        self._session = requests.Session()
        self._request_count = 0
        self._max_requests = 500

    def get(self, *args, **kwargs):
        if self._request_count >= self._max_requests:
            self._session.close()
            self._session = requests.Session()
            self._request_count = 0

        self._request_count += 1
        response = self._session.get(*args, **kwargs)
        return response
