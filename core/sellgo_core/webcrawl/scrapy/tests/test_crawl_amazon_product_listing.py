import pytest

from sellgo_core.webcrawl.scrapy.crawl_amazon_product_listing import crawl


def test_crawl_amazon_product_listing(proxycrawl_token, num_asins, aws_access_key_id, aws_secret_access_key, aws_region,
                                      aws_bucket_name):
    asin_file = open('sample_asins.txt', 'r')
    asins = [f"{next(asin_file).strip()}" for i in range(num_asins)]
    asin_file.close()

    with pytest.raises(ValueError):
        crawl([])

    with pytest.raises(ValueError):
        crawl([{'no_asin': 1, 'no_product_id': 2}])

    with pytest.raises(ValueError):
        crawl(asins, enable_proxycrawl=True)

    crawl(asins, enable_proxycrawl=True, proxycrawl_token=proxycrawl_token, enable_multiproc=True, enable_s3=True,
          aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key,
          aws_region=aws_region, aws_bucket_name=aws_bucket_name)
