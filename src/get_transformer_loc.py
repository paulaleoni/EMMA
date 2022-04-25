'''
Northings -> Longitude
Eastings -> Latitude

'''

from pathlib import Path
import pandas as pd
import geopandas as gpd
import re
import pyproj

wd = Path.cwd()

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


import matplotlib.pyplot as plt
shp_file = wd.parent/'data'/'shp'/'Kenya.zip'

# load shapefile in geopandas dataframe
Kenya_regions = gpd.read_file(shp_file)

Kenya = gpd.GeoDataFrame(index=[0],geometry=[Kenya_regions['geometry'].unary_union])

fig, ax = plt.subplots()
Kenya.plot(ax=ax, facecolor='None', edgecolor='red')
gdf.plot(ax = ax)

#!!! check latitude, longitude