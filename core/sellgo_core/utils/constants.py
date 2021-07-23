class StatusConst:
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class TaskConst:
    CALCULATE_KPI = 1
    COMPETITIVE_PRICING = 2
    FEES_ESTIMATE = 3
    SALES_ESTIMATION = 4
    WEBCRAWL = 5
    INVENTORY = 6
    ADD_ASIN = 7
    REMOVE_ASIN = 8


class AttributeConst:
    FEES = 4000000001
    PRICE = 4000000002
    SELLERS_COUNT = 4000000003
    SIZE_VARIATIONS_COUNT = 4000000004
    COLOR_VARIATIONS_COUNT = 4000000005
    IS_MULTIPACK = 4000000006
    AVERAGE_REVIEWS_COUNT = 4000000007
    RANK = 4000000008
    REVIEW_RATE = 4000000009
    SALES_TO_REVIEW = 4000000010
    TITLE = 4000000011
    BRAND = 4000000012
    HEIGHT = 4000000013
    LENGTH = 4000000014
    WIDTH = 4000000015
    WEIGHT = 4000000016
    SMALL_IMG_URL = 4000000017
    SMALL_IMG_HEIGHT = 4000000018
    SMALL_IMG_WIDTH = 4000000019
    INB_SHIPPING_COST = 4000000020
    OUB_SHIPPING_COST = 4000000021
    PACKAGE_QUANTITY = 4000000022


class WebCrawlConst:
    PROXYCRAWL_MAX_RETRY = 10
    PROXYCRAWL_RETRY_SLEEP = 1
    AMAZON_MERCHANT_ID = 'ATVPDKIKX0DER'
    AMAZON_WAREHOUSE_MERCHANT_ID = 'A2L77EE7U53NWQ'
    FULFILLMENT_BY_AMAZON = 'FBA'
    FULFILLMENT_BY_MERCHANT = 'FBM'


class MwsConst:
    MWS_THROTTLED_ERROR = 'RequestThrottled'
    MWS_GET_FEE_ESTIMATE_THROTTLE_SLEEP = 1
    MWS_MAX_RETRY = 3


class KpiConst:
    DEFAULT_COST_PERCENTAGE = 0
