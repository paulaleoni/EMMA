'''
pre-process population density data taken from 
https://sedac.ciesin.columbia.edu/data/set/gpw-v4-population-density-rev11

output: population_density.csv
'''

from pathlib import Path
import geopandas as gpd
import rioxarray as rxr

if __name__ == "__main__":
    wd = Path.cwd()

    # get Kenya geometries
    shp_file = wd.parent/'data'/'shp'/'Kenya.zip'
    Kenya_regions = gpd.read_file(shp_file)
    Kenya = gpd.GeoDataFrame(index=[0],geometry=[Kenya_regions['geometry'].unary_union])

    # load data
    file = f'/vsizip/{wd.parent}/data/population_density/gpw-v4-population-density-rev11_2015_30_sec_tif.zip/gpw_v4_population_density_rev11_2015_30_sec.tif'

    df = rxr.open_rasterio(file, masked = True).rio.clip(geometries=Kenya.geometry,crs = Kenya.crs, from_disk=True, drop=True, all_touched=True).squeeze()

    # to geodataframe
    df = df.to_dataframe('pop_dens').reset_index()

    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y)).clip(Kenya.geometry)

    # export to csv
    gdf.to_csv(f'{wd.parent}/data/population_density/population_density.csv', index=False)