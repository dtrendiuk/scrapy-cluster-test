import os

import numpy as np
import pandas as pd

from sellgo_core import AmazonMarketplacesConst

CURR_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(CURR_DIR, 'data')
DATA_FILE_NAME = os.path.join(DATA_DIR, 'sales_estimation_lookup.csv')


def is_valid_marketplace(marketplace_id):
    return marketplace_id.isalnum()


def calculate_sales_estimation(rank: int, marketplace_id: str, category: str):
    df = pd.read_csv(DATA_FILE_NAME)
    df.fillna(0, inplace=True)
    values = df.loc[(df['marketplace_id'] == marketplace_id) & (df['amazon_category_name'] == category)].to_dict()
    try:
        key = list(values['marketplace_id'].keys())[0]
        a = float(values['a'][key])
        b = float(values['b'][key])
        bsr_1 = float(values['bsr_1'][key])
        slope_150 = float(values['slope_150'][key])
        if rank <= 150 and marketplace_id == AmazonMarketplacesConst.US['id'] and bsr_1 and slope_150:
            sales = round(float(bsr_1) - (float(slope_150) * rank), 1)
        else:
            sales = round(np.exp(float(a)) * np.power(rank, float(b)), 1)
    except (KeyError, IndexError):
        sales = None
    return sales
