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
pol = gpd.GeoDataFrame(pol, geometry=gpd.points_from_xy(pol.lon, pol.lat)).drop(['lon','lat'],axis=1) # make polygon

# nightlight data
nl = pd.read_csv(data_path/'satellite'/'nightlight_raw.csv')
nl = gpd.GeoDataFrame(nl, geometry=gpd.points_from_xy(nl.x, nl.y)).drop(['x','y'], axis=1)

# transformer data
trans = pd.read_csv(data_path/'transformer'/'transformer_all_raw.csv')
trans = gpd.GeoDataFrame(trans, geometry=trans['geometry'].apply(wkt.loads))
radius = .01 # 0.01 deg = 1111 m
trans.geometry = trans.geometry.buffer(radius)

# join pol and nl values to transformer within radius
join = gpd.sjoin(trans,pol, how='left').drop(['index_right'], axis=1)
# aggregate data
cols = [x for x in join.columns if x.startswith('pol')]
agg = join.groupby(['item'])[cols].sum().reset_index()
join = join.drop(cols, axis=1).drop_duplicates().merge(agg, on='item')

join_nl = gpd.sjoin(trans,nl, how='left').drop(['index_right'], axis=1)
# aggregate data
cols = [x for x in join_nl.columns if x.startswith('nl')]
agg = join_nl.groupby(['item'])[cols].sum().reset_index()
join_nl = join_nl.drop(cols, axis=1).drop_duplicates().merge(agg, on='item')

df = join.merge(join_nl)

df_long = pd.wide_to_long(df, stubnames=['pol','nl'], i = ['item'], j='yearmonth').reset_index()

df_long.to_csv(data_path/'merged_long.csv', index=False)
