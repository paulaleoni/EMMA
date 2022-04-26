'''
This script downloades nightlight data from https://eogdata.mines.edu/nighttime_light/monthly/v10/ in the area of Kenya (shapefile from https://purl.stanford.edu/fc462cc8966) and exports a csv with all the data for the given timeframe. Additionally it saves the list of downloaded files in a txt.

'''

from base64 import decode
from pathlib import Path
import rioxarray as rxr
import geopandas as gpd
import requests
import json
import os
import re
import pandas as pd
import gc
from bs4 import BeautifulSoup
from hide import eogdata_user, eogdata_pw

########################
# Function
#######################

def get_load_tif(year, month):
    year = str(year)
    month = str(month)
    
    # Retrieve access token
    params = {    
            'client_id': 'eogdata_oidc',
            'client_secret': '2677ad81-521b-4869-8480-6d05b9e57d48',
            'username': eogdata_user,
            'password': eogdata_pw,
            'grant_type': 'password'
        }
    token_url = 'https://eogauth.mines.edu/auth/realms/master/protocol/openid-connect/token'
    response = requests.post(token_url, data = params)
    access_token_dict = json.loads(response.text)
    access_token = access_token_dict.get('access_token')
    # Submit request with token bearer
    
    # first ne to get the url for the right files
    path_url = f'https://eogdata.mines.edu/nighttime_light/monthly/v10/{year}/{year}{month}/vcmcfg/'
    soup = BeautifulSoup(requests.get(path_url).text, "html.parser")
    files = []
    for td in soup.find_all('td'):
        for a in td.find_all('a'):
            f = a['href']
            if f.__contains__('75N060W') | f.__contains__('00N060W'):
                files.append(f)
    
    files_list = list(set(files))
    
    # download all those files and save
    tifs = {}
    for n in files_list :
        data_url = f'https://eogdata.mines.edu/nighttime_light/monthly/v10/{year}/{year}{month}/vcmcfg/{n}'
        auth = 'Bearer ' + access_token
        headers = {'Authorization' : auth}
        # make request
        req = requests.get(data_url, headers = headers, stream=True)
        output_file = wd.parent/'data'/'temp'/os.path.basename(data_url)
        # save file
        with open(output_file, 'wb') as f:
            f.write(req.content)
        # get name of tif
        tif_file = re.sub('.tgz', '', os.path.basename(data_url)) + '.avg_rade9h.tif'
        # save dataframe in dictionary
        tifs[n] = rxr.open_rasterio(f'/vsitar/vsigzip/{output_file}/{tif_file}', masked = True).rio.clip(geometries=Kenya.geometry,crs = Kenya.crs, from_disk=True, drop=True, all_touched=True).squeeze().to_dataframe(f'nl_{year}{month}').reset_index()

    # merge to one dataframe
    dfs = [tifs[x] for x in files_list]
    out = pd.concat(dfs, ignore_index=True)
    out = out.drop(['band','spatial_ref'],axis=1)
    # delete tifs from memory
    del(tifs)
    gc.collect()
    # return merged df
    return out , files_list

####################
# execute code
######################

if __name__ == "__main__":
    ####### load shapefile ##########
    wd = Path.cwd()

    shp_file = wd.parent/'data'/'shp'/'Kenya.zip'

    # load shapefile in geopandas dataframe
    Kenya_regions = gpd.read_file(shp_file)

    Kenya = gpd.GeoDataFrame(index=[0],geometry=[Kenya_regions['geometry'].unary_union])

    ############ get data ################
    years = [2012 + x for x in range(9)]
    months = [str(0) + str(x) for x in range(1,10)]
    months.extend(['10','11','12'])

    folder_path = f'{wd.parent}\data\\temp\\'

    df = pd.DataFrame(columns=['y','x'])
    list_files = []
    for y in years:
        for m in months:
            print(y,m) 
            try : 
                dfym, lst = get_load_tif(year = y, month=m)
                list_files.extend(lst)
                df = pd.merge(df, dfym, on=['y','x'], how='outer')
            except: continue 
            for file in os.listdir(folder_path):
                os.remove(folder_path + file)

    # export to csv
    df.to_csv(wd.parent/'data'/'satellite'/'nightlight_raw.csv', index=False)

    # export list of files to txt
    with open(wd.parent/'data'/'satellite'/'files_list_nightlight.txt', 'w') as output:
        file_content = "\n".join(list_files)
        output.write(file_content)