from pathlib import Path
import pandas as pd
#import numpy as np
import geopandas as gpd
from shapely import wkt
import matplotlib.pyplot as plt
import matplotlib.colors as colors
#from linearmodels import PanelOLS
#import statsmodels.api as sm

wd = Path.cwd()
path_figure = wd.parent/'out'/'figures'

shp_file = wd.parent/'data'/'shp'/'Kenya.zip'
Kenya = gpd.read_file(shp_file)
Kenya = Kenya[['NAME_1','geometry']]
Kenya = Kenya.rename(columns={'NAME_1':'county'})
counties = ['Kakamega','Kericho','Taita Taveta','Kitui']
Kenya_counties = Kenya[Kenya.county.str.lower().isin(counties)]

# load raster data
raster = pd.read_csv(wd.parent/'out'/'data'/'raster_merged.csv') 
raster = gpd.GeoDataFrame(raster, geometry=raster['geometry'].apply(wkt.loads), crs= Kenya.crs)
raster = raster[raster.pop_dens > 0]

cols = [x for x in raster.columns.tolist() if x.startswith('pol')]
cols_nl = [x for x in raster.columsns.tolist() if x.startswith('nl')]
cols.extend(cols_nl)
cols.extend(['index','geometry'])

raster = raster[cols]

raster = pd.wide_to_long(raster, stubnames=['pol','nl'], i = ['index'], j='yearmonth').reset_index() 
raster = raster[['index', 'yearmonth','pol','nl','geometry','pop_dens']]
raster['year'] = raster['yearmonth'].astype(str).apply(lambda row: row[0:4]).astype(int)
raster = raster[raster.nl.notnull()]


raster_yearly = raster.groupby(['index','year'])[['pol','nl']].mean().reset_index()
raster_yearly = raster.drop(['pol','nl','yearmonth'],axis=1).drop_duplicates().merge(raster_yearly, how='left', on=['index','year'])

# plot whole Kenya
for y in [2015, 2020]:
    data = raster_yearly[raster_yearly.year == y]
    for v in ['pop_dens','pol','nl']:
        vmin = data[[v]].min()[0]
        vmax = data[[v]].max()[0]
        vcenter = data[[v]].quantile(0.5)[0]
        divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)
        fig, ax = plt.subplots()
        data.plot(column=v, ax=ax, alpha=.7, cmap='PuRd', norm=divnorm, legend=True)
        Kenya.plot(ax=ax, facecolor='None', edgecolor='grey')
        Kenya_counties.plot(ax=ax, facecolor='None', edgecolor='black')
        ax.set_axis_off()
        plt.tight_layout()
        fig.savefig(path_figure/f'Kenya_map_{y}_{v}')