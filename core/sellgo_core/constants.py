class AmazonMarketplacesConst:
    US = {'name': 'US', 'code': 'US', 'id': 'ATVPDKIKX0DER', 'extension': 'com'}
    BRAZIL = {'name': 'Brazil', 'code': 'BR', 'id': 'A2Q3Y263D00KWC', 'extension': 'com.br'}
    CANADA = {'name': 'Canada', 'code': 'CA', 'id': 'A2EUQ1WTGCTBG2', 'extension': 'ca'}
    MEXICO = {'name': 'Mexico', 'code': 'MX', 'id': 'A1AM78C64UM0Y8', 'extension': 'com.mx'}
    UAE = {'name': 'United Arab Emirates (U.A.E.)', 'code': 'AE', 'id': 'A2VIGQ35RCS4UG', 'extension': 'ae'}
    GERMANY = {'name': 'Germany', 'code': 'DE', 'id': 'A1PA6795UKMFR9', 'extension': 'de'}
    SPAIN = {"name": "Spain", 'code': 'ES', 'id': 'A1RKKUPIHCS9HS', 'extension': 'es'}
    FRANCE = {"name": "France", 'code': 'FR', 'id': 'A13V1IB3VIYZZH', 'extension': 'fr'}
    UK = {'name': 'UK', 'code': 'GB', 'id': 'A1F83G8C2ARO7P', 'extension': 'co.uk'}
    INDIA = {'name': 'India', 'code': 'IN', 'id': 'A21TJRUUN4KGV', 'extension': 'in'}
    ITALY = {'name': "Italy", 'code': "IT", 'id': 'APJ6JRA9NG5V4', 'extension': 'it'}
    TURKEY = {"name": 'Turkey', 'code': 'TR', 'id': 'A33AVAJ2PDY3EV', 'extension': 'com.tr'}
    SINGAPORE = {'name': 'Singapore', 'code': 'SG', 'id': 'A19VAU5U5O7RUS', 'extension': 'sg'}
    AUSTRALIA = {"name": "Australia", 'code': "AU", 'id': 'A39IBJ37TRP1C6', 'extension': 'com.au'}
    JAPAN = {"name": "Japan", 'code': 'JP', 'id': 'A1VC38T7YXB528', 'extension': 'co.jp'}
    NETHERLANDS = {"name": "Netherlands", 'code': 'NL', 'id': "A1805IZSGTT6HS", 'extension': 'cn'}
    CHINA = {"name": "China", 'code': 'CN', 'id': "AAHKV2X7AFYLW", 'extension': 'cn'}
    ALL = [US, BRAZIL, CANADA, MEXICO, UAE, GERMANY, SPAIN, FRANCE, UK, INDIA, ITALY, TURKEY, SINGAPORE,
           AUSTRALIA, JAPAN, CHINA]
    ALL_ID_INDEXED = {m['id']: m for m in ALL}
