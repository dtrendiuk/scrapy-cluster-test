from logging import Logger, getLogger
from typing import Optional, Union

from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.http import Response
from scrapy.http.request import Request
from scrapy.spiders import Spider
from scrapy.utils.python import global_object_name
from scrapy.utils.response import response_status_message

from .constants import Base as Constants
from .db import db
from .utils import (
    build_proxycrawl,
    build_proxycrawl_js,
    get_url_from_proxycrawl,
)

logger = getLogger(__name__)


def get_retry_request(
    request: Request,
    spider: Spider,
    reason: Union[str, Exception] = "unspecified",
    response: Response = None,
    max_retry_times: Optional[int] = None,
    priority_adjust: Optional[int] = None,
    logger: Logger = logger,
    stats_base_key: str = "retry",
):
    """
    Returns a new :class:`~scrapy.Request` object to retry the specified
    request, or ``None`` if retries of the specified request have been
    exhausted.
    For example, in a :class:`~scrapy.Spider` callback, you could use it as
    follows::
        def parse(self, response):
            if not response.text:
                new_request_or_none = get_retry_request(
                    response.request,
                    spider=self,
                    reason='empty',
                )
                return new_request_or_none

    *spider* is the :class:`~scrapy.Spider` instance which is asking for the
    retry request. It is used to access the :ref:`settings <topics-settings>`
    and :ref:`stats <topics-stats>`, and to provide extra logging context (see
    :func:`logging.debug`).

    *reason* is a string or an :class:`Exception` object that indicates the
    reason why the request needs to be retried. It is used to name retry stats.

    *max_retry_times* is a number that determines the maximum number of times
    that *request* can be retried. If not specified or ``None``, the number is
    read from the :reqmeta:`max_retry_times` meta key of the request. If the
    :reqmeta:`max_retry_times` meta key is not defined or ``None``, the number
    is read from the :setting:`RETRY_TIMES` setting.

    *priority_adjust* is a number that determines how the priority of the new
    request changes in relation to *request*. If not specified, the number is
    read from the :setting:`RETRY_PRIORITY_ADJUST` setting.

    *logger* is the logging.Logger object to be used when logging messages

    *stats_base_key* is a string to be used as the base key for the
    retry-related job stats

    """
    settings = spider.crawler.settings
    stats = spider.crawler.stats
    retry_times = request.meta.get("retry_times", 0) + 1

    crawlera = request.meta.get("crawlera")
    proxycrawl = request.meta.get("proxycrawl")
    proxycrawl_js = request.meta.get("proxycrawl_js")
    proxycrawl_js_enabled = request.meta.get("proxycrawl_js_enabled", False)

    crawlera_error = None
    response_status_code = None

    page_name = request.meta.get("page_name", "unknown_page")

    if response:
        response_status_code = response.status
        crawlera_error = response.headers.get("X-Crawlera-Error")
        crawlera_error = crawlera_error.decode("utf-8") if crawlera_error else None

    proxy_provider = "crawlera"
    if "proxycrawl" in request.url:
        proxy_provider = "proxycrawl"

    if not (crawlera and proxycrawl and proxycrawl_js):
        raise NoProxyCredentials("crawlera, proxycrawl, and proxycrawl_js API Key is required")

    if max_retry_times is None:
        max_retry_times = request.meta.get("max_retry_times", 1)
        if max_retry_times is None:
            max_retry_times = int(settings.getint("RETRY_TIMES"))

    if proxy_provider == "crawlera":
        key = f"{Constants.CRAWLERA_ERROR}"
        stats.inc_value(key)
        if crawlera_error:
            key += f"/{crawlera_error}"
            stats.inc_value(key)

        key = f"{Constants.CRAWLERA_ERROR}/{response_status_code}"
        stats.inc_value(key)
        if crawlera_error:
            key += f"/{crawlera_error}"
            stats.inc_value(key)

        if response_status_code:
            key = f"{Constants.CRAWLERA_ERROR}/{response_status_code}/{reason}"
            stats.inc_value(key)

        key = f"{Constants.CRAWLERA_ERROR}/{page_name}"
        stats.inc_value(key)
        if crawlera_error:
            key += f"/{crawlera_error}"
            stats.inc_value(key)

        key = f"{Constants.CRAWLERA_ERROR}/{page_name}/{response_status_code}"
        stats.inc_value(key)
        if crawlera_error:
            key = f"{Constants.CRAWLERA_ERROR}/{page_name}/{crawlera_error}"
            stats.inc_value(key)

        if response_status_code:
            key = f"{Constants.CRAWLERA_ERROR}/{page_name}/{response_status_code}/{reason}"
            stats.inc_value(key)

    elif proxy_provider == "proxycrawl":
        key = f"{Constants.PROXYCRAWL_ERROR}"
        stats.inc_value(key)

        key = f"{Constants.PROXYCRAWL_ERROR}/{response_status_code}"
        stats.inc_value(key)

        if response_status_code:
            key = f"{Constants.PROXYCRAWL_ERROR}/{response_status_code}/{reason}"
            stats.inc_value(key)

        key = f"{Constants.PROXYCRAWL_ERROR}/{page_name}/{response_status_code}"
        stats.inc_value(key)

        if response_status_code:
            key = f"{Constants.PROXYCRAWL_ERROR}/{page_name}/{response_status_code}/{reason}"
            stats.inc_value(key)

    if retry_times <= max_retry_times:
        new_request = request.copy()
        new_request.meta["retry_times"] = retry_times
        new_request.dont_filter = True
        if priority_adjust is None:
            priority_adjust = settings.getint("RETRY_PRIORITY_ADJUST")
            new_request.priority = request.priority + priority_adjust  # type: ignore

        if callable(reason):
            reason = reason()
        if isinstance(reason, Exception):
            reason = global_object_name(reason.__class__)

        stats.inc_value(f"{stats_base_key}/count")
        stats.inc_value(f"{stats_base_key}/reason_count/{reason}")

        if retry_times == 1:
            if proxy_provider == "crawlera":
                logger.debug(
                    f"Retrying {request} (failed {retry_times} times) - "
                    f"using {proxy_provider}(X-Crawlera-Error = {crawlera_error}): {reason}",
                    extra={"spider": spider},
                )
            else:
                logger.debug(
                    f"Retrying {request} (failed {retry_times} times) - using {proxy_provider}: {reason}",
                    extra={"spider": spider},
                )
        else:
            # Switch proxy provider
            if "proxycrawl" in request.url:
                new_request.meta["proxy"] = crawlera
                new_url = get_url_from_proxycrawl(request.url)
                new_request = new_request.replace(url=new_url)

                logger.debug(
                    f"Retrying {request} (failed {retry_times} times) - switch proxycrawl to crawlera: {reason}",
                    extra={"spider": spider},
                )
            else:
                new_request.meta["proxy"] = None

                if proxycrawl_js_enabled:
                    new_url = build_proxycrawl_js(request.url, proxycrawl_js)
                    new_request = new_request.replace(url=new_url)
                else:
                    new_url = build_proxycrawl(request.url, proxycrawl)
                    new_request = new_request.replace(url=new_url)

                logger.debug(
                    f"Retrying {request} (failed {retry_times} times) - "
                    f"using {proxy_provider}(X-Crawlera-Error = {crawlera_error}): {reason}",
                    extra={"spider": spider},
                )

        return new_request
    else:
        update_on_fail = request.meta.get("update_on_fail")
        if update_on_fail:
            key_name = update_on_fail["key"]
            key_value = update_on_fail[key_name]
            update_values = update_on_fail["update_values"]

            collection = db[update_on_fail["collection"]]
            collection.update_one({key_name: key_value}, {"$set": update_values})

        stats.inc_value(f"{stats_base_key}/max_reached")

        if proxy_provider == "crawlera":
            logger.debug(
                f"Gave up retrying {request} (failed {retry_times} times) - "
                f"using {proxy_provider}(X-Crawlera-Error = {crawlera_error}): {reason}",
                extra={"spider": spider},
            )
        else:
            logger.debug(
                f"Gave up retrying {request} (failed {retry_times} times) - using {proxy_provider}: {reason}",
                extra={"spider": spider},
            )

        return None


class CustomRetryMiddleware(RetryMiddleware):
    def process_response(self, request, response, spider):
        if request.meta.get("dont_retry", False):
            return response
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider, response) or response
        return response

    def _retry(self, request, reason, spider, response=None):
        max_retry_times = request.meta.get("max_retry_times", self.max_retry_times)
        priority_adjust = request.meta.get("priority_adjust", self.priority_adjust)
        return get_retry_request(
            request=request,
            spider=spider,
            reason=reason,
            response=response,
            max_retry_times=max_retry_times,
            priority_adjust=priority_adjust,
        )


class NoProxyCredentials(Exception):
    pass
