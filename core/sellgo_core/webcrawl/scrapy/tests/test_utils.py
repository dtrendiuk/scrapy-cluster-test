import pytest

from sellgo_core.webcrawl.scrapy.scrapy_common_settings import proxycrawl_settings
from sellgo_core.webcrawl.scrapy.utils import get_product_identifiers, update_spider_with_proxycrawl, clean


def test_get_product_identifiers():
    asin, product_id = get_product_identifiers('B0000AXTUY')
    assert asin == 'B0000AXTUY'
    assert product_id is None

    asin, product_id = get_product_identifiers({'asin': 'B00K72C1T4', 'product_id': '100000001'})
    assert asin == 'B00K72C1T4'
    assert product_id == '100000001'

    class MockProduct:
        def __init__(self, asin=None, product_id=None):
            self.asin = asin
            self.product_id = product_id

    asin, product_id = get_product_identifiers(MockProduct('B0039MQ06Y', '100000002'))
    assert asin == 'B0039MQ06Y'
    assert product_id == '100000002'

    asin, product_id = get_product_identifiers(MockProduct('B0039MQ06Y'))
    assert asin == "B0039MQ06Y"
    assert product_id is None

    asin, product_id = get_product_identifiers(MockProduct(None, '100000003'))
    assert asin is None
    assert product_id == '100000003'

    asin, product_id = get_product_identifiers(MockProduct())
    assert asin is None
    assert product_id is None


def test_update_spider_with_proxycrawl():
    class MockSpider:
        enable_proxycrawl = False

    with pytest.raises(ValueError):
        update_spider_with_proxycrawl(MockSpider, {}, True, None)

    # no change to spider & settings if enable_proxycrawl == False
    settings = {}
    update_spider_with_proxycrawl(MockSpider, settings, False, None)
    assert not MockSpider.enable_proxycrawl
    assert not settings

    # spider & settings should be updated
    settings = {}
    update_spider_with_proxycrawl(MockSpider, settings, True, 'mock_token')
    assert MockSpider.enable_proxycrawl
    assert proxycrawl_settings.items() <= settings.items()
    assert settings["PROXYCRAWL_TOKEN"] == 'mock_token'


def test_clean():
    text = clean(None)
    assert text is None

    text = clean('   demo text   ')
    assert isinstance(text, str) is True
    assert text == 'demo text'

    text = clean([' text 1 ', '    text 2    '])
    assert isinstance(text, list) is True
    assert text == ['text 1', 'text 2']
