from sellgo_core import AmazonMarketplacesConst
from sellgo_core.utils.sales_estimator import calculate_sales_estimation, is_valid_marketplace


def test_calculate_sales_estimation():
    sale_correct_more_150 = calculate_sales_estimation(
        rank=1000, category='Beauty & Personal Care', marketplace_id=AmazonMarketplacesConst.US['id']
    )
    assert sale_correct_more_150 is not None

    sale_correct_less_150 = calculate_sales_estimation(rank=89, category='Shoes & Bags',
                                                       marketplace_id="A1F83G8C2ARO7P")
    assert sale_correct_less_150 is not None

    mismatched_sale = calculate_sales_estimation(rank=100, category='Shoes & Bags',
                                                 marketplace_id=AmazonMarketplacesConst.US['id'])
    assert mismatched_sale is None

    sales_correct_exact = calculate_sales_estimation(rank=1004036, category='Beauty & Personal Care',
                                                     marketplace_id=AmazonMarketplacesConst.US['id'])
    assert sales_correct_exact is not None
    assert sales_correct_exact == 25.2

    sales_correct_exact = calculate_sales_estimation(rank=48061, category='Grocery & Gourmet Food',
                                                     marketplace_id=AmazonMarketplacesConst.US['id'])
    assert sales_correct_exact is not None
    assert sales_correct_exact == 104.2

    sales_correct_exact = calculate_sales_estimation(rank=280830, category='Sports & Outdoors',
                                                     marketplace_id=AmazonMarketplacesConst.US['id'])
    assert sales_correct_exact is not None
    assert sales_correct_exact == 22.2

    sales_correct_exact = calculate_sales_estimation(rank=1000000000, category='Sports & Outdoors',
                                                     marketplace_id=AmazonMarketplacesConst.US['id'])
    assert sales_correct_exact is not None
    assert sales_correct_exact == 0.0


def test_is_valid_marketplace():
    all_num = '1234567890'
    assert is_valid_marketplace(all_num) is True
    all_char = 'dfasdfj'
    assert is_valid_marketplace(all_char) is True
    non_alphanum = '(!&#*&!)@(#&'
    assert is_valid_marketplace(non_alphanum) is False
