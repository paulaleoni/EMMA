'''
create dataset with pollution, nightlight and transformer data

lon = x
lat = y
'''

from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely import wkt

wd = Path.cwd()

data_path = wd.parent/'data'

# pollution data
pol = pd.read_csv(data_path/'satellite'/'pollution_raw.csv')
pol = gpd.GeoDataFrame(pol, geometry=gpd.points_from_xy(pol.lon + 0.005, pol.lat + 0.005).buffer(.01, cap_style = 3)).drop(['lon','lat'],axis=1) # make polygon

# nightlight data
nl = pd.read_csv(data_path/'satellite'/'nightlight_raw.csv')
nl = gpd.GeoDataFrame(nl, geometry=gpd.points_from_xy(nl.x, nl.y)).drop(['x','y'], axis=1)

# transformer data
trans = pd.read_csv(data_path/'transformer'/'transformer_all_raw.csv')
trans = gpd.GeoDataFrame(trans, geometry=trans['geometry'].apply(wkt.loads))


# join data
join_pol_trans = gpd.sjoin(pol,trans, how='left').dropna(subset=['item']).drop(['index_right'], axis=1)
df = gpd.sjoin(join_pol_trans, nl, how='left').drop(['index_right'], axis=1) # then need to do aggregation as below

cols = [x for x in df.columns if x.startswith('pol') | x.startswith('nl') ]
agg = df.groupby(['item'])[cols].sum().reset_index()

df = df.drop(cols, axis=1).drop('geometry',axis=1).drop_duplicates().merge(agg, on='item')


df_long = pd.wide_to_long(df, stubnames=['pol','nl'], i = ['item'], j='yearmonth').reset_index()

df_long.to_csv(wd.parent/'data'/'merged_long.csv', index=False)
