## reading GeoTiff file

from pathlib import Path
from zipfile import ZipFile
import geopandas as gpd
from rasterio.transform import xy
import rioxarray as rxr
from shapely.geometry.multipolygon import MultiPolygon, polygon
from shapely.ops import unary_union
from shapely import wkt
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.mask import mask
import matplotlib.colors as colors
import json
import geojson
import xarray as xr
import netCDF4
import rasterio.features
from shapely.geometry import shape
#from adjustText import adjust_text

def getFeatures(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    return [json.loads(gdf.to_json())['features'][0]['geometry']]

#####################
# Data
####################

wd = Path.cwd()

shp_file = wd.parent/'data'/'shp'/'Kenya.zip'

# load shapefile in geopandas dataframe
Kenya_regions = gpd.read_file(shp_file)

Kenya = gpd.GeoDataFrame(index=[0],geometry=[Kenya_regions['geometry'].unary_union])

Kakamega = Kenya_regions.loc[Kenya_regions['NAME_1'] == 'Kakamega',]
coords = getFeatures(Kenya)

years = ['2014', '2016','2019']
files = {}
tifs = {}
for y in years:
    # pollution data https://sedac.ciesin.columbia.edu/data/set/sdei-global-annual-gwr-pm2-5-modis-misr-seawifs-aod-v4-gl-03/data-download
    files[y] =f'/vsizip/{wd.parent}/data/satellite/sdei-global-annual-gwr-pm2-5-modis-misr-seawifs-aod-v4-gl-03-{y}-geotiff.zip/sdei-global-annual-gwr-pm2-5-modis-misr-seawifs-aod-v4-gl-03-{y}.tif'
    tifs[y] = rxr.open_rasterio(files[y], masked = True).rio.clip(geometries=Kakamega.geometry,from_disk=True, drop=True).squeeze()

tif = tifs['2019']
df = tif.to_dataframe('2019_values').reset_index() 
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x + 0.005, df.y + 0.005))
gdf.geometry = gdf.geometry.buffer(.01, cap_style = 3)

# plot
fig, ax = plt.subplots(ncols=len(years), figsize=(7*len(years),7))
vmin = min([np.nanmin(tifs[y].values) for y in years])
vmax = max([np.nanmax(tifs[y].values) for y in years])
for y in years:    
    a = ax[years.index(y)]
    tifs[y].sel().plot(ax=a, cmap = 'RdPu', alpha=.7, vmin=vmin, vmax=vmax)
    a.set_title(y)
    #gdf.geometry.plot(ax=a, facecolor='None', edgecolor='grey')
[axi.set_axis_off() for axi in ax.ravel()]
plt.tight_layout()
#fig.savefig(wd.parent/'figures'/'pollution.png')


# nightlight
file = f'/vsigzip/{wd.parent}/data/satellite/VNL_v2_npp_2019_global_vcmslcfg_c202102150000.median_masked.tif.gz'
nl = rxr.open_rasterio(file, masked = True).rio.clip(geometries=Kakamega.geometry,from_disk=True, drop=True).squeeze()

fig, ax = plt.subplots()
divnorm = colors.TwoSlopeNorm(vmin=nl.values.min(), vcenter=2, vmax=nl.values.max())
nl.sel().plot(ax=ax, norm=divnorm)
ax.set_title('NL-2019')
Kakamega.plot(ax=ax, facecolor='None', edgecolor='black',linewidth=1)
ax.set_axis_off()
plt.tight_layout()
#fig.savefig(wd.parent/'figures'/'nightlight.png')

nldf = nl.to_dataframe('nl').reset_index()
nlgdf = gpd.GeoDataFrame(nldf, geometry=gpd.points_from_xy(nldf.x, nldf.y))

join = gpd.sjoin(gdf, nlgdf, how='left').reset_index().dissolve(by ='index', aggfunc='sum')

join[['2019_values','nl']].corr()

#########################################################
# monthly pollution data

m_file = f'{wd.parent}/data/satellite\V5GL02.HybridPM25.Global.201901-201901.nc'

test = xr.open_dataset(m_file)

test = test.rio.write_crs(4326, inplace=True).rio.clip(geometries=Kakamega.geometry,crs= Kakamega.crs ,from_disk=True, drop=True,all_touched=True)

test.GWRPM25.plot()

poldf = test.GWRPM25.to_dataframe('pol').reset_index()
polgdf = gpd.GeoDataFrame(poldf, geometry=gpd.points_from_xy(poldf.lon + 0.005, poldf.lat + 0.005))
polgdf.geometry = polgdf.geometry.buffer(.01, cap_style = 3)

#nc = netCDF4.Dataset(m_file)


# monthly nightlight data
mnl = f'/vsitar/vsigzip/{wd.parent}/data/satellite/SVDNB_npp_20190101-20190131_75N060W_vcmslcfg_v10_c201905201300.tgz/SVDNB_npp_20190101-20190131_75N060W_vcmslcfg_v10_c201905201300.avg_rade9h.tif'


mnl_data =rxr.open_rasterio(mnl, masked = True).rio.clip(geometries=Kenya.geometry,crs = Kenya.crs, from_disk=True, drop=True, all_touched=True).squeeze()

mnldf = mnl_data.to_dataframe('mnl').reset_index()
mnlgdf = gpd.GeoDataFrame(mnldf, geometry=gpd.points_from_xy(mnldf.x, mnldf.y))


join = gpd.sjoin(polgdf, mnlgdf, how='left').reset_index().dissolve(by ='index', aggfunc='sum')

join[['pol','mnl']].corr()


