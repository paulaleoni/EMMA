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
from linearmodels import PanelOLS
import statsmodels.api as sm

wd = Path.cwd()
path_figure = wd.parent/'out'/'figures'

# load data
df = pd.read_csv(wd.parent/'out'/'data'/'dataset_all.csv')
# prepare data
#df = df[df.pop_dens != 0] # drop grid cells with no population
df = df[df.nl.notnull()] # first 3 months of 2012 no data for nightlight
df = df[df.pop_dens > 0] # drop grid cells with no population
#df = df[df.date_first_vend_prepaid.notnull()]
#df = df[df.dist_tr <= 0.02]
counties = df[df.date_first_vend_prepaid.notnull()].county.unique().tolist()
df = df[df.county.isin(counties)]


# load Kenya shapefile
shp_file = wd.parent/'data'/'shp'/'Kenya.zip'
Kenya = gpd.read_file(shp_file)
Kenya = Kenya[['NAME_1','geometry']]
Kenya_all = Kenya.copy()
Kenya = Kenya.rename(columns={'NAME_1':'county'})
Kenya = Kenya[Kenya.county.str.lower().isin(counties)]
Kenya['centroid'] = Kenya.centroid

### transformer 
df_trans = df.loc[df.date_first_vend_prepaid.notnull(),['geometry_transformer','county']].drop_duplicates().reset_index(drop=True).dropna()
gdf_trans = gpd.GeoDataFrame(df_trans, geometry=df_trans['geometry_transformer'].apply(wkt.loads))

'''
# group grid cells by
# nothing if neither lmcp, nonlmcp, preexisting
df['group'] = np.nan
df.loc[(df.n_lmcp==0) & (df.n_nonlmcp==0) & (df.n_preexisting==0), 'group'] = 'no electricity'
# #lmcp > #nonlmcp + #preexising
df.loc[(df.len_lmcp >= df.len_nonlmcp) & (df.len_lmcp >=df.len_preexisting) & df.group.isnull(), 'group'] = 'lmcp'
# #nonlmcp > #lmcp + #preexising
df.loc[(df.len_nonlmcp >= df.len_lmcp) & (df.len_nonlmcp >= df.len_preexisting) & df.group.isnull(), 'group'] = 'nonlmcp'
# #preexisting > #lmcp + #nonlmcp
df.loc[(df.len_preexisting >= df.len_lmcp) & (df.len_preexisting >= df.len_nonlmcp) & df.group.isnull(), 'group'] = 'preexisting'
#gdf = gpd.GeoDataFrame(df, geometry=df['geometry'].apply(wkt.loads))
'''
agg_yearly = df.groupby(['index','year'])[['pol','nl']].mean().reset_index()
df_yearly = df.drop(['pol','nl','yearmonth'],axis=1).drop_duplicates().merge(agg_yearly, how='left', on=['index','year'])

gdf_yearly = gpd.GeoDataFrame(df_yearly, geometry=df_yearly['geometry'].apply(wkt.loads))

# plot Kenya and highlight counties for analysis
fig, ax = plt.subplots()
Kenya_all.plot(ax=ax, facecolor='None', edgecolor='grey', alpha=.5)
Kenya.plot(ax=ax, facecolor='None', edgecolor='black', alpha=.7)
for x, y, label in zip(Kenya.centroid.x, Kenya.centroid.y, Kenya.county):
    ax.annotate(label, xy=(x, y), xytext=(7, 0), textcoords="offset points", fontweight="bold")
ax.set_axis_off()
fig.savefig(path_figure/f'map_Kenya',bbox_inches='tight',pad_inches = 0)

# plot transformer locations
fig, ax = plt.subplots()
Kenya.plot(ax=ax, facecolor='None', edgecolor='grey', alpha=.7)
gdf_trans.plot(ax=ax, color='black', markersize=1, label='transformer')
ax.set_axis_off()
plt.tight_layout()
plt.legend()
fig.savefig(path_figure/f'map_Transformers',bbox_inches='tight',pad_inches = 0)

# plot pop dens of 2015
data = gdf_yearly[gdf_yearly.year == 2015]
v = 'pop_dens'
vmin = data[[v]].min()[0]
vmax = data[[v]].max()[0]
vcenter = data[[v]].quantile(0.5)[0]
divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)
fig, ax = plt.subplots()
data.plot(column=v, ax=ax, alpha=.7, cmap='PuBuGn', norm=divnorm, legend=True)
Kenya.plot(ax=ax, facecolor='None', edgecolor='grey')
ax.set_axis_off()
plt.tight_layout()
fig.savefig(path_figure/f'map_2015_pop_dens',bbox_inches='tight',pad_inches = 0)

# plot nightlight and pollution
years = [2015, 2020]
for v in ['pol','nl']:
    data = gdf_yearly
    vmin = data[[v]].min()[0]
    vmax = data[[v]].max()[0]
    vcenter = data[[v]].quantile(0.5)[0]
    divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)
    fig, axes = plt.subplots(ncols=2, sharey=True, sharex=True,constrained_layout = True, figsize=(7,5))
    for y in range(len(years)):
        datay = data[data.year == years[y]] #'PuRd''
        datay.plot(column=v, ax=axes[y], alpha=.7, cmap='PuBuGn', norm=divnorm) 
        Kenya.plot(ax=axes[y], facecolor='None', edgecolor='grey')
        axes[y].set_axis_off()
        #gdf_trans.plot(ax=axes[y], color='black', markersize=1, label='transformer')
    patch_col = axes[0].collections[0]
    cb = fig.colorbar(patch_col, ax=axes, shrink=.5)
    fig.savefig(path_figure/f'map_{v}',bbox_inches='tight',pad_inches = 0, dpi=200)
'''
# plot map of groups
data = df[df.yearmonth==201204]
data = gpd.GeoDataFrame(data, geometry=data['geometry'].apply(wkt.loads))
#data['group'] = pd.Categorical(data['group'])
fig, ax = plt.subplots()
data.plot(column='group', ax=ax, alpha=.7, legend=True, cmap='Accent')
Kenya.plot(ax=ax, facecolor='None', edgecolor='grey')
ax.set_axis_off()
plt.tight_layout()
fig.savefig(path_figure/'map_electricity.png')
'''

# residualize pollution
data = df[df.date_first_vend_prepaid.notnull() & (df.dist_tr <= 0.02)]
data = data.set_index(['index','yearmonth'])
exog = sm.add_constant(data['pop_dens'])
dep = data['pol']
mod = PanelOLS(dependent=dep,exog=exog, drop_absorbed=True)
res = mod.fit()

pred = res.predict(exog)

pol_residuals = dep-pred['predictions']
pol_residuals = pol_residuals.rename('pol_residuals')#.reset_index()

data = data.merge(pol_residuals, left_index=True, right_index=True).reset_index()

# time series of all groups
# drop grid cells with no population
ts_group = data.groupby(['yearmonth'])[['nl', 'pol', 'pol_residuals']].median().reset_index()
ts_group['yearmonth'] = pd.to_datetime(ts_group['yearmonth'], format='%Y%m')
# set cmap colors
cmap = plt.get_cmap('Accent')
cls = [cmap.colors[0], cmap.colors[2],cmap.colors[5],cmap.colors[7]]
cls = [colors.to_hex(x) for x in cls]

for x in ['nl','pol', 'pol_residuals']:
    fig, ax = plt.subplots()    
    #ax.set_prop_cycle(color=cls)
    ax.plot('yearmonth',x, data=ts_group, label='')
    ax.legend()
    plt.tight_layout()
    fig.savefig(path_figure/f'ts_{x}_median.png')

# nightlight time series for distinct years
for y in [2016, 2017, 2018, 2019, 2020]:
    fig, ax = plt.subplots()
    ax.set_prop_cycle(color=cls)
    for g in ts_group.group.unique().tolist():
        data= ts_group[(ts_group.group==g) & (ts_group.yearmonth.dt.year == y)]
        ax.plot('yearmonth','nl', data=data, label=g)
    ax.legend()
    plt.tight_layout()
    fig.savefig(path_figure/f'ts_nl_{y}_median.png')