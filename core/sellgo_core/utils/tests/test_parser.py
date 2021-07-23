import os
from distutils import dir_util

from pytest import fixture

from sellgo_core.utils.parser import parse_single, parse_inventory_monitoring_report, parse_sales_estimation, \
    parse_data, competitive_pricing_single, sales_rank_single, parse_fees_estimate, parse_offer_sellers_page_count, \
    get_all_offers, parse_amazon_product_listing_page


@fixture
def datadir(tmpdir, request):
    """
    Fixture responsible for searching a folder with the same name of tests
    module and, if available, moving all contents to a temporary directory so
    tests can use them freely.
    """
    filename = request.module.__file__
    test_dir, _ = os.path.splitext(filename)

    if os.path.isdir(test_dir):
        dir_util.copy_tree(test_dir, str(tmpdir))

    return tmpdir


def test_parse_data(datadir):
    cp = eval(open(datadir.join('competitive_pricing.txt')).read())
    offer_listing_list = []
    price_list = []
    sales_rank_list = []
    parse_data(cp, offer_listing_list, price_list, sales_rank_list, 3000014041)

    assert offer_listing_list is not None
    assert len(offer_listing_list) == 3

    assert price_list is not None
    assert len(price_list) == 2

    assert sales_rank_list is not None
    assert len(sales_rank_list) == 3


def test_parse_single(datadir):
    sales_rank_list = []
    price_list = []
    offer_listing_list = []
    i = eval(open(datadir.join('competitive_pricing.txt')).read())
    parse_single(offer_listing_list, price_list, i, sales_rank_list, 3000014041)

    assert offer_listing_list is not None
    assert len(offer_listing_list) == 3

    assert price_list is not None
    assert len(price_list) == 2

    assert sales_rank_list is not None
    assert len(sales_rank_list) == 3


def test_competitive_pricing_single(datadir):
    i = eval(open(datadir.join('competitive_pricing.txt')).read())
    cp_list = i['Product']['CompetitivePricing']['CompetitivePrices']['CompetitivePrice'][0]
    price_dict = competitive_pricing_single(cp_list, 3000003321)

    assert price_dict is not None
    assert isinstance(price_dict, dict)
    assert len(price_dict) == 12


def test_sales_rank_single(datadir):
    sales_rank_list = []
    i = eval(open(datadir.join('competitive_pricing.txt')).read())
    sales_rank = i['Product']['SalesRankings']['SalesRank'][0]
    sales_rank_single(3000003321, sales_rank, sales_rank_list)

    assert len(sales_rank_list) > 0
    assert len(sales_rank_list) == 1


def test_parse_inventory_monitoring_report(datadir):
    i = eval(open(datadir.join('inventory_check.txt')).read())['data']['body']
    asin_id_map = {'B075K7W3BB': 1, 'B009FUF6DM': 2, 'B003TTL0TE': 3, 'B01MXIE9RT': 4, 'B000CITK8S': 5}
    i_list = parse_inventory_monitoring_report(i, asin_id_map)

    assert i_list is not None
    assert len(i_list) == 5


def test_parse_sales_estimation(datadir):
    i = eval(open(datadir.join('sales_estimation.txt')).read())
    se_dict = parse_sales_estimation(i)

    assert se_dict is not None
    assert len(se_dict) == 12
    assert se_dict['daily_max_sales'] == '0.0'
    assert se_dict['daily_max_rank'] == 14923175
    assert se_dict['daily_est_sales'] == '0.0'
    assert se_dict['daily_est_rank'] == 1374555
    assert se_dict['daily_min_sales'] == '64.5'
    assert se_dict['daily_min_rank'] == 29
    assert se_dict['monthly_max_sales'] == '0.0'
    assert se_dict['monthly_max_rank'] == 14923175
    assert se_dict['monthly_est_sales'] == '0.0'
    assert se_dict['monthly_est_rank'] == 1374555
    assert se_dict['monthly_min_sales'] == '84.72052042160738'
    assert se_dict['monthly_min_rank'] == 3


def test_parse_fees_estimate(datadir):
    fees_estimate_parsed = eval(open(datadir.join('fees_estimation.txt')).read())

    fees_estimate_dict = parse_fees_estimate(fees_estimate_parsed)
    assert fees_estimate_dict is not None and len(fees_estimate_dict) > 0
    assert len(fees_estimate_dict) == 2

    fees_estimate_dict_expected = {'total_amount': '9.68', 'total_currency': 'USD'}
    for key in fees_estimate_dict_expected.keys():
        assert fees_estimate_dict[key] == fees_estimate_dict_expected[key]


def test_parse_offer_sellers_page_count(datadir):
    sellers_page_text = open(datadir.join('aod_sellers_onepage.txt')).read()
    page_count = parse_offer_sellers_page_count(sellers_page_text)
    assert page_count is not None and page_count != 0
    assert page_count == 3

    sellers_page_text = open(datadir.join('aod_sellers_onepage.txt')).read()
    page_count = parse_offer_sellers_page_count(sellers_page_text)
    assert page_count is not None and page_count != 0
    assert page_count == 3


def test_parse_offer_sellers(datadir):
    sellers_page_text = open(datadir.join('aod_sellers_onepage.txt')).read()
    sellers = get_all_offers("SOMEASIN", sellers_page_text)
    assert sellers is not None and type(sellers) == list
    assert len(sellers) == 3

    sellers_page_text = open(datadir.join('aod_sellers_onepage.txt')).read()
    sellers = get_all_offers("SOMEASIN", sellers_page_text)
    assert sellers is not None and type(sellers) == list
    assert len(sellers) == 3


def test_parse_amazon_product_listing_page(datadir):
    product_page_text = open(datadir.join('product_listing.txt')).read()
    product = parse_amazon_product_listing_page(product_page_text)
    assert product is not None and type(product) == dict
    assert len(product) == 13
