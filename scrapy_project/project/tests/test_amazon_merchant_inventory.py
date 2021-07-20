import pathlib

from project.spiders.amazon_merchant_inventory import (
    AmazonMerchantInventorySpider,
)


def test_get_inventory_count():
    path = pathlib.Path(__file__).parent.absolute()
    f = open(f"{path}/fixtures/amazon_merchant_inventory_body.txt", "rb").read()

    count = AmazonMerchantInventorySpider.get_inventory_count(f)
    assert count == "279"


def test_get_products():
    path = pathlib.Path(__file__).parent.absolute()
    f = open(f"{path}/fixtures/amazon_merchant_inventory_body.txt", "rb").read()

    products = AmazonMerchantInventorySpider.get_products(f)
    assert len(products) == 16


def test_get_product_data():
    class MockSelf:
        _job = "test"
        _project = "test"
        _spider = "test"
        _total_expected_len = 0
        _total_yield = 1

    path = pathlib.Path(__file__).parent.absolute()
    f = open(f"{path}/fixtures/amazon_merchant_inventory_body.txt", "rb").read()

    products = AmazonMerchantInventorySpider.get_products(f)
    product_data = AmazonMerchantInventorySpider.get_product_data(self=MockSelf, product_raw=products[0])

    assert isinstance(product_data, dict)
    assert product_data["asin"] == "B008CPQMNO"
    assert product_data["current_price"] == "$24.49"
    assert product_data["reviews_count"] == "117"
