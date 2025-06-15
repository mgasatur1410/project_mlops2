import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2
import os

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def add_features(df):
    df['transaction_time'] = pd.to_datetime(df['transaction_time'])
    df['hour'] = df['transaction_time'].dt.hour
    df['dayofweek'] = df['transaction_time'].dt.dayofweek
    df['month'] = df['transaction_time'].dt.month
    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
    df['amount_log'] = np.log1p(df['amount'])
    df['distance'] = df.apply(lambda r: haversine(r['lat'], r['lon'], r['merchant_lat'], r['merchant_lon']), axis=1)
    return df

INPUT_PATH = 'input/test.csv'
OUTPUT_PATH = 'input/test_processed.csv'

if not os.path.exists(INPUT_PATH):
    raise FileNotFoundError(f"Input file {INPUT_PATH} not found!")

test = pd.read_csv(INPUT_PATH)
test = add_features(test)

features = [c for c in test.columns if c != 'transaction_time']
for col in features:
    if test[col].dtype == 'object':
        test[col] = test[col].fillna('missing')
    else:
        test[col] = test[col].fillna(test[col].median())

test.to_csv(OUTPUT_PATH, index=False)
print(f"Preprocessed test data saved to {OUTPUT_PATH}") 