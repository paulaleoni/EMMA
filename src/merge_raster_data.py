'''
merge lines, nightlight, pollution and population density

out: 'raster_merged.csv'
'''

from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely import wkt
import gc
import numpy as np


if __name__ == "__main__":
    wd = Path.cwd()

    
    # load Kenya shapefile in geopandas dataframe
    shp_file = wd.parent/'data'/'shp'/'Kenya.zip'
    Kenya = gpd.read_file(shp_file)
    counties = ['Kakamega','Nakuru','Kericho','Baringo','Taita Taveta','Kitui']
    Kenya = Kenya[Kenya.NAME_1.isin(counties)]
    Kenya = gpd.GeoDataFrame(index=[0],geometry=[Kenya['geometry'].unary_union])

    # pollution data
    pol = pd.read_csv(wd.parent/'data'/'satellite'/'pollution_raw.csv')
    pol = gpd.GeoDataFrame(pol, geometry=gpd.points_from_xy(pol.lon+ 0.005, pol.lat+ 0.005 )).clip(Kenya.geometry[0]).reset_index(drop=True) 
    # make polygon
    pol.geometry = pol.geometry.buffer(.005, cap_style = 3)

    # get lines
    lines = pd.read_csv(wd.parent/'out'/'data'/'lines.csv')
    lines = gpd.GeoDataFrame(lines, geometry=lines['geometry'].apply(wkt.loads))
    lines = lines.drop('county', axis=1)

    join_lines = gpd.sjoin(pol, lines, how='left', predicate='intersects')
    join_lines = join_lines.reset_index().drop(['index_right'], axis=1)

    # get dummy variables of type
    join_lines = pd.get_dummies(join_lines, columns=['type'])
    
    for t in ['lmcp','nonlmcp','preexisting']:
        join_lines[f'len_{t}'] = join_lines.loc[join_lines[f'type_{t}'] == 1,'line_length']
    
    # add up lines
    agg = join_lines.dissolve(by ='index', 
                    aggfunc={'type_lmcp':'sum',
                             'type_nonlmcp':'sum',
                             'type_preexisting':'sum',
                             'len_lmcp':'sum',
                             'len_nonlmcp':'sum',
                             'len_preexisting':'sum'}, as_index=False).drop('geometry',axis=1)
    
    join_lines = join_lines.drop(['filename','type_nonlmcp','type_lmcp','type_preexisting','len_lmcp','len_nonlmcp','len_preexisting', 'line_length'], axis=1).drop_duplicates()

    join_lines = join_lines.merge(agg, on = 'index', how='left').drop('index',axis=1)

    # rename types
    join_lines = join_lines.rename(columns={'type_lmcp':'n_lmcp','type_nonlmcp':'n_nonlmcp','type_preexisting':'n_preexisting'})

    # delete files from memory
    del(pol)
    del(lines)
    del(agg)
    gc.collect()

    # population density
    pop = pd.read_csv(wd.parent/'data'/'population_density'/'population_density.csv')
    pop = pop.drop(['band','spatial_ref','y','x'], axis=1)
    pop = gpd.GeoDataFrame(pop, geometry=pop['geometry'].apply(wkt.loads)).clip(Kenya.geometry[0])

    # merge
    join_pop = gpd.sjoin(join_lines, pop, how='left').reset_index().drop(['index_right'], axis=1)
    # aggeragte to grid level
    agg = join_pop.dissolve(by ='index', aggfunc={'pop_dens':'mean'},as_index=False).drop('geometry',axis=1)
    join_pop = join_pop.drop('pop_dens',axis=1).drop_duplicates().merge(agg, on = 'index', how='left').drop('index',axis=1)

    del(pop)
    del(agg)
    del(join_lines)
    gc.collect()

    # nightlight data
    nl = pd.read_csv(wd.parent/'data'/'satellite'/'nightlight_raw.csv')
    nl = gpd.GeoDataFrame(nl, geometry=gpd.points_from_xy(nl.x, nl.y)).drop(['x','y'], axis=1)

    nl = nl.clip(Kenya.geometry[0])

    join = gpd.sjoin(join_pop, nl, how='left').reset_index().drop(['index_right'], axis=1)
    
    nl_cols = nl.drop('geometry', axis=1).columns.tolist()
    nl_cols_ind = nl.drop('geometry', axis=1).columns.tolist()
    nl_cols_ind.extend(['index','geometry'])

    agg = join[nl_cols_ind].dissolve(by ='index', aggfunc='mean',as_index=False).drop('geometry',axis=1)
    join = join.drop(nl_cols,axis=1).drop_duplicates().merge(agg, on = 'index', how='left')

    # export
    join.to_csv(wd.parent/'out'/'data'/'raster_merged.csv', index=False)