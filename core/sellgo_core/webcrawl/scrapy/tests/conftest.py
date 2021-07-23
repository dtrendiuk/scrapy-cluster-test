def pytest_addoption(parser):
    parser.addoption(
        "--proxycrawl_token",
        default='',
        help="proxycrawl token",
    )
    parser.addoption(
        "--num_asins",
        default=100,
        type=int,
        help="number of asins to crawl",
    )
    parser.addoption(
        "--aws_access_key_id",
        default='',
        help="aws access key id for s3",
    )
    parser.addoption(
        "--aws_secret_access_key",
        default='',
        help="aws secret access key for s3",
    )
    parser.addoption(
        "--aws_region",
        default='',
        help="aws region for s3",
    )
    parser.addoption(
        "--aws_bucket_name",
        default='',
        help="aws bucket name for s3",
    )


def pytest_generate_tests(metafunc):
    if "proxycrawl_token" in metafunc.fixturenames:
        metafunc.parametrize("proxycrawl_token", [metafunc.config.getoption("proxycrawl_token")])
    if "num_asins" in metafunc.fixturenames:
        metafunc.parametrize("num_asins", [metafunc.config.getoption("num_asins")])
    if "aws_access_key_id" in metafunc.fixturenames:
        metafunc.parametrize("aws_access_key_id", [metafunc.config.getoption("aws_access_key_id")])
    if "aws_secret_access_key" in metafunc.fixturenames:
        metafunc.parametrize("aws_secret_access_key", [metafunc.config.getoption("aws_secret_access_key")])
    if "aws_region" in metafunc.fixturenames:
        metafunc.parametrize("aws_region", [metafunc.config.getoption("aws_region")])
    if "aws_bucket_name" in metafunc.fixturenames:
        metafunc.parametrize("aws_bucket_name", [metafunc.config.getoption("aws_bucket_name")])
