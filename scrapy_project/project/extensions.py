import os

import sentry_sdk
from scrapy.exceptions import NotConfigured


class SentryLogging(object):
    """
    Send exceptions and errors to Sentry.
    """

    @classmethod
    def from_crawler(cls, _):
        sentry_dsn = os.getenv("SENTRY_DSN", None)
        sentry_enabled = os.getenv("SENTRY_ENABLED", "false")
        sentry_environment = os.getenv("SENTRY_ENVIRONMENT", "dev")

        if sentry_dsn is None and sentry_enabled.lower() == "true":
            raise NotConfigured
        # instantiate the extension object
        ext = cls()
        if sentry_enabled.lower() == "true":
            # instantiate
            sentry_sdk.init(sentry_dsn, environment=sentry_environment)
        # return the extension object
        return ext
