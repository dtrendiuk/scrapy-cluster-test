import requests


class ProxyCrawl(object):
    BASE_URL = 'https://api.proxycrawl.com?token=%s&url=%s'

    def __init__(self, token):
        self.token = token
        self.session = None

    def set_session(self, session):
        # override session
        self.session = session

    def get(self, url, headers={}):
        url = self._url(url)
        if self.session is None:
            return requests.get(url, headers=headers)
        return self.session.get(url, headers=headers)

    def _url(self, target_url):
        return ProxyCrawl.BASE_URL % (self.token, target_url)
