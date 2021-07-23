import os
from distutils import dir_util

from pytest import fixture

from sellgo_core.utils.constants import KpiConst
from sellgo_core.utils.kpi import calculate_kpis, calculate_multipack_cost, calculate_multipack_quantity, \
    calculate_multipack_profit, calculate_multipack_margin, calculate_multipack_roi, calculate_advance_margin, \
    calculate_advance_roi, calculate_advance_profit


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


def test_calculate_kpis(datadir):
    i = eval(open(datadir.join('kpi.json')).read())
    i['is_variation_size'] = True
    i['is_variation_color'] = True
    i['is_variation_packagequantity'] = True
    i['buybox_suppressed'] = True
    item = calculate_kpis(i)

    assert item is not None
    assert len(item) == 22
    assert item['price'] == 19.69
    assert item['fees'] == 6.14
    assert item['profit'] == - 16.99
    assert item['margin'] == - 86.29
    assert item['roi'] == - 55.63
    assert item['daily_sales'] == 0.0
    assert item['rank'] == 1511
    assert item['fba_fee'] == 2.0
    assert item['referral_fee'] == 1.8
    assert item['variable_closing_fee'] == 0.0
    assert item['num_fba_new_offers'] == 0
    assert item['num_fbm_new_offers'] == 1
    assert item['low_new_fba_price'] == 0
    assert item['low_new_fbm_price'] == 19.69
    assert item['is_variation'] is None
    assert item['multi_asin'] is None
    assert item['num_variations'] is None
    assert item['is_variation_size'] is True
    assert item['is_variation_color'] is True
    assert item['is_variation_packagequantity'] is True
    assert item['buybox_suppressed'] is True

    i['product_cost'] = None
    item = calculate_kpis(i)
    assert item['profit'] == 13.55
    assert item['margin'] is None
    assert item['roi'] is None


def test_calculate_multipack_quantity():
    assert calculate_multipack_quantity(1, 4) == 4


def test_calculate_multipack_cost(datadir):
    i = eval(open(datadir.join('kpi.json')).read())
    multipack_cost = calculate_multipack_cost(3, i['product_cost'],
                                              float(KpiConst.DEFAULT_COST_PERCENTAGE * float(i['price'])))
    assert multipack_cost == 91.62


def test_calculate_multipack_profit(datadir):
    i = eval(open(datadir.join('kpi.json')).read())
    multipack_profit = calculate_multipack_profit(12.20, i['price'], i['fees'])
    assert multipack_profit == 1.35


def test_calculate_multipack_margin(datadir):
    i = eval(open(datadir.join('kpi.json')).read())
    multipack_margin = calculate_multipack_margin(20.15, i['price'])
    assert multipack_margin == 102.34


def test_calculate_multipack_roi():
    multipack_roi = calculate_multipack_roi(23.22, 10.2)
    assert multipack_roi == 43.93


def test_calculate_advance_profit(datadir):
    i = eval(open(datadir.join('kpi.json')).read())
    inbound_shipping = 1
    outbound_shipping = None
    prep_fee = None
    sourcing_tax = None
    vat_registered = None
    vat_perc = None
    custom_charge = None
    custom_discount = None
    advance_profit = calculate_advance_profit(12.20, 4, 91.62, i['price'], i['fees'], inbound_shipping,
                                              outbound_shipping, prep_fee, sourcing_tax,
                                              vat_registered, vat_perc, custom_charge, custom_discount)
    assert advance_profit == 8.2

    vat_registered = True
    vat_perc = 10
    advance_profit = calculate_advance_profit(12.20, 4, 91.62, i['price'], i['fees'], inbound_shipping,
                                              outbound_shipping, prep_fee, sourcing_tax,
                                              vat_registered, vat_perc, custom_charge, custom_discount)
    assert advance_profit == 6.41

    custom_charge = 1
    custom_discount = 20
    advance_profit = calculate_advance_profit(12.20, 4, 91.62, i['price'], i['fees'], inbound_shipping,
                                              outbound_shipping, prep_fee, sourcing_tax,
                                              vat_registered, vat_perc, custom_charge, custom_discount)
    assert advance_profit == 23.73


def test_calculate_advance_margin(datadir):
    i = eval(open(datadir.join('kpi.json')).read())
    advance_margin = calculate_advance_margin(20.15, i['price'])
    assert advance_margin == 102.34


def test_calculate_advance_roi():
    advance_roi = calculate_advance_roi(23.22, 10.2)
    assert advance_roi == 43.93
