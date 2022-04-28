'''
This file extracts, among other variables, the location of the transformers. The File 'Dasboard...' is an imperfect list of all lmcp transformers in Kenya. For the surveyed counties better data is available (2_raw_county datasets.zip), so these are used instead.


Northings -> Longitude
Eastings -> Latitude

Point(lon, lat)

'''

from pathlib import Path
import zipfile
import pandas as pd
import geopandas as gpd
import re
import pyproj
from zipfile import ZipFile

wd = Path.cwd()

shp_file = wd.parent/'data'/'shp'/'Kenya.zip'

# load shapefile in geopandas dataframe
Kenya_regions = gpd.read_file(shp_file)

Kenya = gpd.GeoDataFrame(index=[0],geometry=[Kenya_regions['geometry'].unary_union])

imp_trans_file = wd.parent/'data'/'transformer'/'Dashboard Donor LMCP August 2020.csv'

imp_trans = pd.read_csv(imp_trans_file, sep =';',dtype='str', header=1, skiprows =[2,3,4,5] ,encoding_errors='ignore')

cols = ['ITEM', 'PROGRAM/PROJECT', 'SUB PROJECT','IMPLEMENTING AGENCY', 'COUNTY', 'PROJECT LOCATION', 'Unnamed: 11', 'TIMELINES', 'Unnamed: 28']

imp_trans = imp_trans[cols]

imp_trans = imp_trans.rename(columns={'Unnamed: 11': 'Loc_east', 'Unnamed: 28':'completion_date'})

imp_trans = imp_trans.dropna(subset= 'PROJECT LOCATION')

def dms2dd(string):
    try: 
        lst = re.split('[°\'"?\s*]|(?=[A-Z])', string)
        lst = list(filter(lambda x: x != '', lst))
        if (len(lst[0]) == 2) & (len(lst) < 4):
            lst.insert(1, lst[0][1])
            lst[0] = lst[0][0]
        if (len(lst[0]) == 3) & (len(lst) < 4): 
            lst.insert(1, lst[0][1:3])
            lst[0] = lst[0][0]
        if len(lst[0]) == 4: 
            lst.insert(1, lst[0][2:4])
            lst[0] = lst[0][:2]
        deg, minutes, seconds, direction =  lst
        dd = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
        return dd
    except: return None
 
def utm2lon(East,North):
    try:
        p2 = pyproj.Proj(proj="utm", zone=37) #proj="utm", zone=37
        East = re.sub('(M)([MS,ME,MN,MW])','',East)
        if re.search('(\d)*(\.)(\d)*',East):
            East = re.search('(\d)*(\.)(\d)*',East).group()
        North = re.sub('(M)([MS,ME,MN,MW])','',North)  
        if re.search('(\d)*(\.)(\d)*',North):
            North = re.search('(\d)*(\.)(\d)*',North).group()   
        x = float(East)
        y = float(North)
        lon, lat = p2(x,y,inverse=True)  
        return lon
    except: return None

def utm2lat(East,North):
    try:
        p2 = pyproj.Proj(proj="utm", zone=37)
        East = re.sub('(M)([MS,ME,MN,MW])','',East)
        if re.search('(\d)*(\.)(\d)*',East):
            East = re.search('(\d)*(\.)(\d)*',East).group()
        North = re.sub('(M)([MS,ME,MN,MW])','',North)  
        if re.search('(\d)*(\.)(\d)*',North):
            North = re.search('(\d)*(\.)(\d)*',North).group() 
        x = float(East)
        y = float(North)
        lon, lat = p2(x,y,inverse=True)  
        return lat
    except: return None 

imp_trans['lon'] = imp_trans['PROJECT LOCATION'].apply(lambda row: dms2dd(row))
imp_trans['lat'] = imp_trans['Loc_east'].apply(lambda row: dms2dd(row))

imp_trans.loc[imp_trans['lon'].isnull(), 'lon'] = imp_trans.loc[imp_trans['lon'].isnull(),:].apply(lambda row: utm2lon(row['Loc_east'],row['PROJECT LOCATION']), axis=1)
imp_trans.loc[imp_trans['lat'].isnull(), 'lat'] = imp_trans.loc[imp_trans['lat'].isnull(), :].apply(lambda row: utm2lat(row['Loc_east'],row['PROJECT LOCATION']), axis=1)


gdf = gpd.GeoDataFrame(imp_trans, geometry=gpd.points_from_xy(imp_trans.lat, imp_trans.lon))
gdf.columns = gdf.columns.str.lower()

'''
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
Kenya.plot(ax=ax, facecolor='None', edgecolor='red')
gdf.plot(ax = ax)

#!!! check latitude, longitude
'''

### from survey shapefiles

zip_path = wd.parent/'data'/'transformer'/'2_raw county datasets.zip'
zip_shapes = ZipFile(zip_path)

list_trans_shp = [x for x in zip_shapes.namelist() if ('transformer' in x.lower()) & (x.endswith('.shp'))]

gdf_survey = gpd.GeoDataFrame(columns=['geometry'], geometry='geometry')
for file in list_trans_shp:
    dfx = gpd.read_file(f'{zip_path}!{file}')
    dfx.columns = dfx.columns.str.lower()
    gdf_survey = pd.concat([gdf_survey, dfx], ignore_index=True)
    
# keep relevant columns
cols = ['geometry','county','ref_no','z_referenc','scheme_nam','item','project','sub_projec','projected_','actual_out','start_date','projected1']
gdf_survey = gdf_survey[cols]

# if item is nan, replace with 'z_referenc' or 'ref_no'
gdf_survey.loc[gdf_survey['item'].isnull(),'item'] = gdf_survey.loc[gdf_survey['item'].isnull(),'z_referenc']
gdf_survey.loc[gdf_survey['item'].isnull(),'item'] = gdf_survey.loc[gdf_survey['item'].isnull(),'ref_no']
gdf_survey = gdf_survey.drop(['z_referenc','ref_no'], axis=1)

# merge both datasets based on zref
gdf_all = gdf.merge(gdf_survey, how='outer', on='item', suffixes=('', '_y')).drop_duplicates()


def merge_columns(col1, col2, df, drop = True):
    # replace col1 if nan by col2, drop col2 afterwards
    df.loc[df[col1].isnull(),col1] = df.loc[df[col1].isnull(),col2]
    if drop==True : df = df.drop(col2, axis=1)
    return df

gdf_all = merge_columns('program/project','project', gdf_all)
gdf_all = merge_columns('sub project','sub_projec', gdf_all)
gdf_all = merge_columns('sub project','scheme_nam', gdf_all)
gdf_all = merge_columns('county','county_y', gdf_all)
gdf_all = merge_columns('timelines','start_date', gdf_all)
gdf_all = merge_columns('completion_date','projected1', gdf_all)
gdf_all = merge_columns('geometry','geometry_y', gdf_all, drop=False)

# if points close, set geometry to geometry_y (geometry_y should be better)
distance = 0.001 # 0.001 deg = 111 m
gdf_all['geom_within'] = gdf_all.apply(lambda row: row['geometry'].within(row['geometry_y'].buffer(distance)) if (row['geometry_y'] is not None) else False, axis=1)

gdf_all['geometry'] = gdf_all.apply(lambda row: row['geometry_y'] if row['geom_within'] else row['geometry'], axis=1)

gdf_all = gdf_all.drop(['geometry_y','geom_within'], axis=1)

fig, ax = plt.subplots()
Kenya.plot(ax=ax)
gdf_all.geometry[0:13300].plot(ax=ax, color='red', markersize=1)


# only keep locations that are within Kenya
gdf_all = gdf_all.loc[gdf_all.within(Kenya.geometry[0])]

# export to csv
gdf_all.to_csv(wd.parent/'data'/'transformer'/'transformer_all_raw.csv', index=False)
