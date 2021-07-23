def filter_unique_products(products):
    _product_id_processed = {}
    unique_products = []
    for product in products:
        product_id = product[1].product_id
        if product_id in _product_id_processed:
            continue
        _product_id_processed[product_id] = True
        unique_products.append(product)
    return unique_products
