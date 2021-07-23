from sellgo_core.utils.constants import KpiConst


def calculate_kpis(params):
    kpi_dict = {}

    kpi_dict['price'] = float(params['price']) if params.get('price') else 0
    product_cost = float(params['product_cost']) if params.get(
        'product_cost') else float(KpiConst.DEFAULT_COST_PERCENTAGE * kpi_dict['price'])
    kpi_dict['fees'] = float(params['fees']) if params.get('fees') else 0

    kpi_dict['profit'] = kpi_dict['price'] - kpi_dict['fees'] - product_cost if kpi_dict['price'] > 0 else 0
    if product_cost > 0:
        kpi_dict['margin'] = round((kpi_dict['profit'] / kpi_dict['price']) * 100, 2) if kpi_dict['price'] > 0 else 0
        kpi_dict['roi'] = round((kpi_dict['profit'] / product_cost) * 100, 2) if product_cost > 0 else 0
    else:
        kpi_dict['margin'] = None
        kpi_dict['roi'] = None

    kpi_dict['daily_sales'] = round(float(params['daily_est_sales']), 2) if params.get('daily_est_sales') else 0
    kpi_dict['monthly_sales'] = round(round(float(params['monthly_est_sales']), 1) * 30, 2) if params.get(
        'monthly_est_sales') else 0

    kpi_dict['rank'] = int(params['rank']) if params.get('rank') else 0
    kpi_dict['fba_fee'] = float(params['fba_fee']) if params.get('fba_fee') else 0
    kpi_dict['referral_fee'] = float(params['referral_fee']) if params.get('referral_fee') else 0
    kpi_dict['variable_closing_fee'] = float(params['variable_closing_fee']) if params.get(
        'variable_closing_fee') else 0

    if isinstance(params.get('lowest_offer_listings'), list):
        for lol in params['lowest_offer_listings']:
            if lol['condition'] == 'New' and lol['fulfillment'] == 'Amazon':
                kpi_dict['num_fba_new_offers'] = int(lol['num_offers'])
                kpi_dict['low_new_fba_price'] = float(lol['landed_price_amount'])
            elif lol['condition'] == 'New' and lol['fulfillment'] == 'Merchant':
                kpi_dict['num_fbm_new_offers'] = int(lol['num_offers'])
                kpi_dict['low_new_fbm_price'] = float(lol['landed_price_amount'])
    kpi_dict['num_fba_new_offers'] = kpi_dict['num_fba_new_offers'] if kpi_dict.get('num_fba_new_offers') else 0
    kpi_dict['low_new_fba_price'] = kpi_dict['low_new_fba_price'] if kpi_dict.get('low_new_fba_price') else 0
    kpi_dict['num_fbm_new_offers'] = kpi_dict['num_fbm_new_offers'] if kpi_dict.get('num_fbm_new_offers') else 0
    kpi_dict['low_new_fbm_price'] = kpi_dict['low_new_fbm_price'] if kpi_dict.get('low_new_fbm_price') else 0

    kpi_dict['is_variation'] = params['is_variation'] if 'is_variation' in params else None
    kpi_dict['multi_asin'] = params['multi_asin'] if 'multi_asin' in params else None
    kpi_dict['num_variations'] = params['num_variations'] if 'num_variations' in params else None
    kpi_dict['is_variation_size'] = params['is_variation_size'] if 'is_variation_size' in params else None
    kpi_dict['is_variation_color'] = params['is_variation_color'] if 'is_variation_color' in params else None
    kpi_dict['is_variation_packagequantity'] = params[
        'is_variation_packagequantity'] if 'is_variation_packagequantity' in params else None
    kpi_dict['buybox_suppressed'] = params['buybox_suppressed'] if 'buybox_suppressed' in params else None

    return kpi_dict


def calculate_multipack_cost(multipack_quantity, product_cost, default_cost):
    return int(multipack_quantity) * float(product_cost) if product_cost else default_cost


def calculate_multipack_profit(multipack_cost, price, fees):
    price = float(price) if price else 0
    fees = float(fees) if fees else 0
    multipack_cost = float(multipack_cost) if multipack_cost else 0
    return round(price - fees - multipack_cost, 2) if price else 0


def calculate_multipack_margin(multipack_profit, price):
    price = float(price) if price else 0
    return round(100 * multipack_profit / price, 2) if price > 0 else 0


def calculate_multipack_roi(multipack_cost, multipack_profit):
    multipack_cost = float(multipack_cost) if multipack_cost else 0
    return round(100 * multipack_profit / multipack_cost, 2) if multipack_cost > 0 else 0


def calculate_multipack_quantity(package_quantity, number_of_items):
    pkg_qty = int(package_quantity) if package_quantity else 1
    num_items = int(number_of_items) if number_of_items else 1
    return max(pkg_qty, num_items)


def calculate_advance_profit(multipack_profit, multipack_quantity, multipack_cost, price, fees, inbound_shipping,
                             outbound_shipping, prep_fee, sourcing_tax,
                             vat_registered, vat_perc, custom_charge, custom_discount):
    if any(c is not None for c in
           [inbound_shipping, outbound_shipping, prep_fee, sourcing_tax, vat_registered, vat_perc, custom_charge,
            custom_discount]):

        inbound_shipping = 0 if not inbound_shipping else float(inbound_shipping)
        outbound_shipping = 0 if not outbound_shipping else float(outbound_shipping)
        prep_fee = 0 if not prep_fee else float(prep_fee)
        sourcing_tax = 0 if not sourcing_tax else float(sourcing_tax)
        vat_perc = 0 if not vat_perc else float(vat_perc)
        custom_charge = 0 if not custom_charge else float(custom_charge)
        custom_discount = 0 if not custom_discount else float(custom_discount)
        multipack_profit = 0 if not multipack_profit else float(multipack_profit)
        multipack_cost = 0 if not multipack_cost else float(multipack_cost)
        price = 0 if not price else float(price)
        fees = 0 if not fees else float(fees)

        if vat_registered:
            advance_profit = multipack_profit - (inbound_shipping * multipack_quantity) - (
                    outbound_shipping * multipack_quantity) - (prep_fee * multipack_quantity) - (
                                     (sourcing_tax / 100) * multipack_cost) - (
                                     price - (price / (1 + (vat_perc / 100)))) - custom_charge + (
                                     (custom_discount / 100) * multipack_cost)
        else:
            advance_profit = multipack_profit - (inbound_shipping * multipack_quantity) - (
                    outbound_shipping * multipack_quantity) - (prep_fee * multipack_quantity) - (
                                     (sourcing_tax / 100) * multipack_cost) - (
                                     fees * vat_perc / 100) - custom_charge + (
                                     (custom_discount / 100) * multipack_cost)
    else:
        return multipack_profit

    return round(advance_profit, 2)


def calculate_advance_margin(advance_profit, price):
    advance_profit = 0 if not advance_profit else float(advance_profit)
    price = 0 if not price else float(price)
    return calculate_multipack_margin(advance_profit, price)


def calculate_advance_roi(multipack_cost, advance_profit):
    multipack_cost = 0 if not multipack_cost else float(multipack_cost)
    advance_profit = 0 if not advance_profit else float(advance_profit)
    return calculate_multipack_roi(multipack_cost, advance_profit)
