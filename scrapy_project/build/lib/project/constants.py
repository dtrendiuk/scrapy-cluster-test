from typing import Final


class Flag(object):
    MONITOR_PROGRESS: Final = "monitor_progess"
    DONT_MONITOR_PROGRESS: Final = "dont_monitor_progress"

    DEFAULT: Final = DONT_MONITOR_PROGRESS


class Base:
    PROXYCRAWL_SUCCESS = "proxy/proxycrawl/success"
    PROXYCRAWL_ERROR = "proxy/proxycrawl/error"
    CRAWLERA_SUCCESS = "proxy/crawlera/success"
    CRAWLERA_ERROR = "proxy/crawlera/error"


class AmazonMerchantAutoStats(Base):
    SCRAPED_ASINS_COUNT = "result/scraped_asins_count"
    ASINS_WITH_ZERO_NEW_SELLERS_COUNT = "result/asins_with_zero_new_sellers_count"
    ASINS_WITH_ZERO_NEW_SELLERS_PAGE_COUNT = "result/asins_with_zero_new_sellers_page_count"
    INSERTED_SELLER_ID_COUNT = "result/inserted_seller_id_count"
    INSERTED_PRIVATE_LABEL_SELLER_ID_COUNT = "result/inserted_private_label_seller_id_count"
    INSERTED_NON_PRIVATE_LABEL_SELLER_ID_COUNT = "result/inserted_non_private_label_seller_id_count"
    INSERTED_SELLER_COUNT = "result/inserted_seller_count"
    PRIVATE_LABEL_ASINS_COUNT = "result/private_label_asins_count"
    PRIVATE_LABEL_PAGES_COUNT = "result/private_label_pages_count"
