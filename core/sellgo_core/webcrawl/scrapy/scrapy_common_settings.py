from sellgo_core.webcrawl.scrapy.constants import ProxyCrawlConst

common_settings = {
    'RETRY_HTTP_CODES': [500, 502, 503, 429, 400, 520],
    'RETRY_TIMES': 10,
    "LOG_FORMAT": ' %(asctime)s.%(msecs)03d [%(name)s] %(levelname)s: %(message)s',
    'LOG_LEVEL': 'INFO',  # use INFO for production, use DEBUG for testing
    # use only for testing purposes, otherwise use item pipelines
    # 'FEEDS': {
    #     'result.json': {
    #         'format': 'json'
    #     }
    #   },
    "COOKIES_ENABLED": False,
    'TELNETCONSOLE_ENABLED': False,
    'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 '
                  'Safari/537.36',
}

proxycrawl_settings = {
    "DOWNLOADER_MIDDLEWARES": {'scrapy_proxycrawl.ProxyCrawlMiddleware': 610},
    "PROXYCRAWL_ENABLED": True,
    # set concurrency parameters to something arbitrarily high
    'CONCURRENT_REQUESTS': '1000',
    'CONCURRENT_REQUESTS_PER_DOMAIN': '1000',
    'REACTOR_THREADPOOL_MAXSIZE': '1000',
    'CONCURRENT_ITEMS': '1000',
    # use this setting to control requests made per second
    "DOWNLOAD_DELAY": 1.0 / ProxyCrawlConst.MAX_REQUESTS_PER_SECOND,
    'RANDOMIZE_DOWNLOAD_DELAY': False,
    'DNSCACHE_ENABLED': False,  # recommended by ProxyCrawl
}
