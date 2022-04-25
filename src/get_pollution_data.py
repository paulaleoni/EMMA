
from pathlib import Path
import xarray as xr
import rioxarray as rxr
import geopandas as gpd

wd = Path.cwd()

shp_file = wd.parent/'data'/'shp'/'Kenya.zip'

# load shapefile in geopandas dataframe
Kenya_regions = gpd.read_file(shp_file)

Kenya = gpd.GeoDataFrame(index=[0],geometry=[Kenya_regions['geometry'].unary_union])

