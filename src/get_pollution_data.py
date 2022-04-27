'''
this file merges the monthly PM2.5 data downloaded from https://sites.wustl.edu/acag/datasets/surface-pm2-5/#V5.GL.02 and extracts the relevant datapoints for Kenya for the given tiem frame. It exports a csv
'''

from pathlib import Path
from zipfile import ZipFile
import xarray as xr
import geopandas as gpd
import pandas as pd


if __name__ == "__main__":
    # load shapefile
    wd = Path.cwd()
    shp_file = wd.parent/'data'/'shp'/'Kenya.zip'
    Kenya_regions = gpd.read_file(shp_file)
    Kenya = gpd.GeoDataFrame(index=[0],geometry=[Kenya_regions['geometry'].unary_union])

    # define zip
    zip_path = 'Pollution_Monthly.zip'
    zip_file = ZipFile(f'{wd.parent}/data/satellite/{zip_path}')
    # define time frame
    years = [2012 + x for x in range(9)]
    months = [str(0) + str(x) for x in range(1,10)]
    months.extend(['10','11','12'])
    # empty dataframe
    df = pd.DataFrame(columns=['lon','lat'])
    # loop 
    for y in years: 
        for m in months:
            #print(y,m)
            # filename
            file = zip_file.open(f'Monthly/V5GL02.HybridPM25.Global.{y}{m}-{y}{m}.nc')
            # open data
            data= xr.open_dataset(file)
            # save in df and clipping Kenya
            dfym = data.rio.write_crs(4326, inplace=True).rio.clip(geometries=Kenya.geometry,crs= Kenya.crs ,from_disk=True, drop=True,all_touched=True).GWRPM25.to_dataframe(f'pol{y}{m}').reset_index().drop('spatial_ref', axis=1)
            # merge
            df = pd.merge(df, dfym, on=['lon','lat'], how='outer')

    # export to csv
    df.to_csv(wd.parent/'data'/'satellite'/'pollution_raw.csv', index=False)