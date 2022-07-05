'''
- map of population density, pollution, nightlight
- time series of nightlight and pollution
'''

from pathlib import Path
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely import wkt
import matplotlib.pyplot as plt
import matplotlib.colors as colors

wd = Path.cwd()
path_figure = wd.parent/'out'/'figures'

# load Kenya shapefile
shp_file = wd.parent/'data'/'shp'/'Kenya.zip'
Kenya = gpd.read_file(shp_file)
Kenya = Kenya[['NAME_1','geometry']]
Kenya = Kenya.rename(columns={'NAME_1':'county'})
counties = ['Kakamega','Nakuru','Kericho','Baringo','Taita Taveta','Kitui']
Kenya = Kenya[Kenya.county.isin(counties)]

# load data
df = pd.read_csv(wd.parent/'out'/'data'/'dataset_all.csv')

# prepare data
df = df[df.pop_dens != 0] # drop grid cells with no population
df = df[df.nl.notnull()] # first 3 months of 2012 no data for nightlight
# group grid cells by
# nothing if neither lmcp, nonlmcp, preexisting
df['group'] = np.nan
df.loc[(df.n_lmcp==0) & (df.n_nonlmcp==0) & (df.n_preexisting==0), 'group'] = 'no electricity'
# #lmcp > #nonlmcp + #preexising
df.loc[(df.n_lmcp >= df.n_nonlmcp) & (df.n_lmcp >=df.n_preexisting) & df.group.isnull(), 'group'] = 'lmcp'
# #nonlmcp > #lmcp + #preexising
df.loc[(df.n_nonlmcp >= df.n_lmcp) & (df.n_nonlmcp >= df.n_preexisting) & df.group.isnull(), 'group'] = 'nonlmcp'
# #preexisting > #lmcp + #nonlmcp
df.loc[(df.n_preexisting >= df.n_lmcp) & (df.n_preexisting >= df.n_nonlmcp) & df.group.isnull(), 'group'] = 'preexisting'
#gdf = gpd.GeoDataFrame(df, geometry=df['geometry'].apply(wkt.loads))

agg_yearly = df.groupby(['index','year'])[['pol','nl']].mean().reset_index()
df_yearly = df.drop(['pol','nl','yearmonth'],axis=1).drop_duplicates().merge(agg_yearly, how='left', on=['index','year'])

gdf_yearly = gpd.GeoDataFrame(df_yearly, geometry=df_yearly['geometry'].apply(wkt.loads))

# plot pop dens of 2015
for y in ['2015']:
    data = gdf_yearly[gdf_yearly.year == y]
    for v in ['pop_dens','pol','nl']:
        vmin = data[[v]].min()[0]
        vmax = data[[v]].max()[0]
        vcenter = data[[v]].quantile(0.5)[0]
        divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)
        fig, ax = plt.subplots()
        data.plot(column=v, ax=ax, alpha=.7, cmap='PuRd', norm=divnorm, legend=True)
        Kenya.plot(ax=ax, facecolor='None', edgecolor='grey')
        ax.set_axis_off()
        plt.tight_layout()
        fig.savefig(path_figure/f'{y}_{v}')


# time series of all groups
ts_group = df.groupby(['yearmonth','group'])[['nl', 'pol']].median().reset_index()
ts_group['yearmonth'] = pd.to_datetime(ts_group['yearmonth'], format='%Y%m')

for x in ['nl','pol']:
    fig, ax = plt.subplots()
    for g in ts_group.group.unique().tolist():
        #fig, ax = plt.subplots()
        data= ts_group[ts_group.group==g]
        ax.plot('yearmonth',x, data=data, label=g)
    ax.legend()
    plt.tight_layout()
    fig.savefig(path_figure/f'ts_{x}_median.png')