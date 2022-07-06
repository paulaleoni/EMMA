'''
pre-process lines data
merge county data and save relevant information

output: lines.csv
'''

from pathlib import Path
import pandas as pd
import geopandas as gpd
from zipfile import ZipFile
import re

if __name__ == "__main__":
    wd = Path.cwd()

    zip_path = wd.parent/'data'/'transformer'/'2_raw county datasets.zip'
    zip_shapes = ZipFile(zip_path)

    list_trans_shp = [x for x in zip_shapes.namelist() if ('lines' in x.lower()) & (x.endswith('.shp'))]

    gdf = gpd.GeoDataFrame(columns=['geometry','filename'], geometry='geometry')
    for file in list_trans_shp:
        dfx = gpd.read_file(f'{zip_path}!{file}')
        dfx.columns = dfx.columns.str.lower()
        dfx['filename'] = re.sub('2_raw county datasets/','',file)
        dfx = dfx[['geometry','filename']]
        gdf = pd.concat([gdf, dfx], ignore_index=True)

    # extract county from filename
    gdf['county'] = gdf['filename'].str.lower()

    gdf['county'] = gdf['county'].apply(lambda row: re.sub(r'(2_raw county datasets/)','',row))

    gdf['county'] = gdf['county'].apply(lambda row: re.match(r"^.*?(?=\/+)", row).group())

    gdf['county'] = gdf['county'].apply(lambda row: re.search(r"[a-z]+", row).group())

    # extract type from filename
    types = "(nonlmcp|AFDB|preexisting|non_lmcp|pre_exsiting|lmcp)"

    gdf['type'] = gdf['filename'].str.lower()
    gdf['type'] = gdf['type'].apply(lambda row: re.search(types, row, re.IGNORECASE).groups()[0])

    gdf.loc[gdf['type'] == 'afdb', 'type'] = 'lmcp'
    gdf.loc[gdf['type'] == 'pre_exsiting', 'type'] = 'preexisting'
    gdf.loc[gdf['type'] == 'non_lmcp', 'type'] = 'nonlmcp'

    ''' 
    #check if wrongly identified 
    lmcp = gdf.loc[gdf['type'] == 'lmcp','filename'].tolist()

    [x for x in lmcp if 'non' in x.lower()]

    # check non identified types
    gdf[gdf['type'].isnull()]
    '''

    gdf['line_length'] = gdf.length

    gdf.to_csv(wd.parent/'out'/'data'/'lines.csv', index=False)