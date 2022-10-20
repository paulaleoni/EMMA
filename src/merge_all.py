'''
merge raster data with transformer and consumption information

output:
dataset_month.csv
dataset_quarter.csv
dataset_yearly.csv
'''

from pathlib import Path
import pandas as pd
import geopandas as gpd
from zipfile import ZipFile
import re
from shapely.geometry import Point
import numpy as np
from shapely import wkt

def merge_columns(col1, col2, df, drop = True):
    ''' 
    replace col1 if nan by col2, drop col2 afterwards
    '''
    df.loc[df[col1].isnull(),col1] = df.loc[df[col1].isnull(),col2]
    if drop==True : df = df.drop(col2, axis=1)
    return df

def get_transformers():
    '''
    merge transformer data and extract relevant information
    '''
    wd = Path.cwd()

    zip_path = wd.parent/'data'/'transformer'/'2_raw county datasets.zip'
    zip_shapes = ZipFile(zip_path)

    list_trans_shp = [x for x in zip_shapes.namelist() if ('transformers' in x.lower()) & (x.endswith('.shp'))]

    cols = ['geometry','filename','no','trans_no','tx_number','z_referenc', 'scheme_nam', 'county','transforme', 'layer','ref_no', 'trans_no','item', 'project', 'sub_projec', 'implementi', 'projected_','start_date','completion', 'status']

    gdf = gpd.GeoDataFrame(columns=['geometry','filename'], geometry='geometry')
    for file in list_trans_shp:
        dfx = gpd.read_file(f'{zip_path}!{file}')
        dfx.columns = dfx.columns.str.lower()
        dfx['filename'] = re.sub('2_raw county datasets/','',file)
        list_col = [x for x in dfx.columns if x in cols]
        dfx = dfx[list_col]
        gdf = pd.concat([gdf, dfx], ignore_index=True)

    # add Kakamega
    path_Kakamega = wd.parent/'data'/'transformer'/'Final_Transformers.shp'
    trans_K = gpd.read_file(path_Kakamega).rename(columns={'Lat': 'latitude','Long':'longitude'})
    trans_K.geometry = trans_K.geometry.apply(lambda row: Point(row.x, row.y)) # remove 3rd dimension
    trans_K.columns = trans_K.columns.str.lower()
    trans_K['county'] = 'Kakamega'
    list_col = [x for x in trans_K.columns if x in cols]
    trans_K = trans_K[list_col]
    gdf = pd.concat([gdf, trans_K], ignore_index=True)

    
    # clean
    # if item is nan, replace with 'z_referenc' or 'ref_no'
    gdf = merge_columns('item','z_referenc', gdf)
    gdf = merge_columns('item','ref_no', gdf)

    # no county -> Nakuru
    gdf.loc[gdf.county.isnull(),'county'] = 'Nakuru'
    gdf['county'] = gdf['county'].str.lower()
    gdf.loc[gdf['county'] == 'taita taveta','county'] = 'taita'

    #
    types = "(AFDB1|AFDB2|AFDB|IDA)"

    #gdf['type'] = gdf['filename'].str.lower()
    gdf['type'] = gdf['filename'].apply(lambda row: re.search(types, row, re.IGNORECASE).groups()[0] if type(row) == str else np.nan)   

    return gdf

def quarters(yearmonth):
    '''
    get quarter of month
    '''
    try:
        yearmonth = str(yearmonth)
        year = yearmonth[:4]
        month = int(yearmonth[-2:])
        if month <= 3: quarter = 0
        elif month <= 6: quarter = 0.25
        elif month <= 9: quarter = 0.5
        elif month <= 12: quarter = 0.75
        else: np.nan
        yearquarter = int(year) + quarter
        return yearquarter  
    except: return np.nan
          
        

if __name__ == "__main__":
    wd = Path.cwd()    

    # load Kenya shapefile in geopandas dataframe
    shp_file = wd.parent/'data'/'shp'/'Kenya.zip'
    Kenya = gpd.read_file(shp_file)
    Kenya = Kenya[['NAME_1','geometry']]
    Kenya = Kenya.rename(columns={'NAME_1':'county'})
    counties = ['Kakamega','Kericho','Taita Taveta','Kitui']
    Kenya = Kenya[Kenya.county.isin(counties)]
    Kenya.county = Kenya.county.str.lower()

    # load raster data
    df = pd.read_csv(wd.parent/'out'/'data'/'raster_merged.csv') 
    df = gpd.GeoDataFrame(df, geometry=df['geometry'].apply(wkt.loads), crs= Kenya.crs)  
    
    # merge raster data with county
    # this creates some duplicates since some grid cells cover more than one county, drop later based on shortest distance to transformer
    #df = raster#.sjoin(Kenya, how='left').drop(columns=['index_right'], axis=1)

    # load transformer data
    transformers = get_transformers()
    transformers.loc[transformers.county=='taita', 'county'] = 'taita taveta'

    # load consumption data
    cons = pd.read_csv(wd.parent/'out'/'data'/'consumption_firsts.csv', dtype=str)
    cons['county'] = cons['county'].str.lower()

    # find closest transformer for each grid cell
    for index, line in df.iterrows():
        #county = line['county']
        # consider only transformers in the same county to speed things up
        trans = transformers#[transformers['county'] == county]
        # save potential transformers in dictionary
        dists = {}
        for i, tr in trans.iterrows():
            dist = line['geometry'].boundary.distance(tr['geometry'])
            dists[tr.name] = dist
        # find transformer with minimum distance and save distance and transformer
        mindist = min(dists.values())
        res = [k for k, v in dists.items() if v==mindist][0]
        df.loc[index,'dist_tr'] = mindist
        df.loc[index,'trans_index'] = res
        print(index)
    
    # merge transformer data to df
    transformers = transformers.rename(columns={'geometry':'geometry_transformer'})
    df = df.merge(transformers, how='left', left_on=['trans_index'], right_on=[transformers.index])

    # drop duplicates based on which county has closest transformer
    #index_to_keep = df.groupby('index')['dist_tr'].idxmin().dropna().astype(int).tolist()
    #df = df.loc[index_to_keep,]

    # merge consumption information
    merge1 = df.merge(cons, how= 'inner', left_on=['item','county'], right_on=['zrefrence','county'])
    merge2 = df.merge(cons, how= 'inner', left_on=['trans_no','county'], right_on=['tr_number','county'])
    merged = pd.concat([merge1, merge2])
    merged = merged.drop_duplicates(subset='index')
    
    df = df.merge(merged, how='left')

    # to long
    df_long = pd.wide_to_long(df, stubnames=['pol','nl'], i = ['index'], j='yearmonth').reset_index()

    df_long['year'] = df_long['yearmonth'].astype(str).apply(lambda row: row[0:4])

    # bring it to quaterly level
    df_long['yearquarter'] = df_long['yearmonth'].apply(quarters)
    df_long['date_first_vend_prepaid'] = df_long['date_first_vend_prepaid'].apply(quarters)
    
    # make it yearly 
    df_year = df_long.groupby(['index','year'])[['pol','nl']].mean().reset_index()
    df_year = df_year.merge(df_long.drop(['pol','nl','yearmonth','yearquarter'],axis=1).drop_duplicates(), how='left', on=['index','year'])

    # filter data - exclude cells with negative population density
    df_long = df_long[(df_long.pop_dens > 0)]
        
    df_quarterly = df_long.groupby(['index','yearquarter'])[['pol','nl']].mean().reset_index()
    df_long_quarterly = df_quarterly.merge(df_long.drop(['pol','nl', "yearmonth"],axis=1).drop_duplicates(), how='left', on=['index','yearquarter'])
         

    # export to csv
    df_long.to_csv(wd.parent/'out'/'data'/'dataset_month.csv', index=False)
    df_long_quarterly.to_csv(wd.parent/'out'/'data'/'dataset_quarter.csv', index=False)
    df_year.to_csv(wd.parent/'out'/'data'/'dataset_yearly.csv', index=False)    