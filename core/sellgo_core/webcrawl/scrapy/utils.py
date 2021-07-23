import re

from sellgo_core.webcrawl.scrapy.scrapy_common_settings import proxycrawl_settings


def get_product_identifiers(product):
    if isinstance(product, str):
        asin = product
        product_id = None
    elif isinstance(product, dict) and {'asin', 'product_id'} <= product.keys():
        asin = product['asin']
        product_id = product['product_id']
    elif hasattr(product, 'asin') and hasattr(product, 'product_id'):
        asin = product.asin
        product_id = product.product_id
    else:
        asin = None
        product_id = None
    return asin, product_id


def update_spider_with_proxycrawl(spider, updated_settings, enable_proxycrawl, proxycrawl_token):
    if enable_proxycrawl and proxycrawl_token:
        spider.enable_proxycrawl = enable_proxycrawl
        updated_settings.update(proxycrawl_settings)
        updated_settings.update({"PROXYCRAWL_TOKEN": proxycrawl_token})
    elif enable_proxycrawl and not proxycrawl_token:
        raise ValueError("proxycrawl_token must be provided if enable_proxycrawl is True")


def clean(to_clean):
    if to_clean is None:
        return None

    if isinstance(to_clean, str):
        return re.sub(r'\s+', ' ', to_clean.replace('\xa0', ' ')).strip()
    to_clean = [clean(c) for c in to_clean]

    return [c for c in to_clean if c]
