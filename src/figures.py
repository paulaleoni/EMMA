'''
- map of Kenya and distribution of transformers
- map of population density, pollution, nightlight
- time series of nightlight and pollution
'''

from formatter import NullFormatter
from json import load
from pathlib import Path
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely import wkt
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from linearmodels import PanelOLS
import statsmodels.api as sm

def setup():
    wd = Path.cwd()
    path_figure = wd.parent/'out'/'figures'
    return wd, path_figure

def load_data(wd):
    df_yearly = pd.read_csv(wd.parent/'out'/'data'/'dataset_yearly.csv')
    df = pd.read_csv(wd.parent/'out'/'data'/'dataset_month.csv')
    counties = df[df.date_first_vend_prepaid.notnull()].county.unique().tolist()
    return df, df_yearly, counties

def load_shp(wd, counties):
    # load Kenya shapefile
    shp_file = wd.parent/'data'/'shp'/'Kenya.zip'
    Kenya = gpd.read_file(shp_file)
    Kenya = Kenya[['NAME_1','geometry']]
    Kenya_all = Kenya.copy()
    Kenya = Kenya.rename(columns={'NAME_1':'county'})
    Kenya = Kenya[Kenya.county.str.lower().isin(counties)]
    Kenya['centroid'] = Kenya.centroid
    return Kenya, Kenya_all

def get_transformers(df):
    ### transformer 
    df_trans = df.loc[df.date_first_vend_prepaid.notnull(),['geometry_transformer','county']].drop_duplicates().reset_index(drop=True).dropna()
    gdf_trans = gpd.GeoDataFrame(df_trans, geometry=df_trans['geometry_transformer'].apply(wkt.loads))
    return gdf_trans

def plot_Kenya(Kenya, Kenya_all, path_figure):
    # plot Kenya and highlight counties for analysis
    fig, ax = plt.subplots()
    Kenya_all.plot(ax=ax, facecolor='None', edgecolor='grey', alpha=.5)
    Kenya.plot(ax=ax, facecolor='None', edgecolor='black', alpha=.7)
    for x, y, label in zip(Kenya.centroid.x, Kenya.centroid.y, Kenya.county):
        ax.annotate(label, xy=(x, y), xytext=(7, 0), textcoords="offset points", fontweight="bold")
    ax.set_axis_off()
    fig.savefig(path_figure/f'map_Kenya',bbox_inches='tight',pad_inches = 0,dpi=200)

def plot_trans(gdf_trans, Kenya, path_figure):
    # plot transformer locations
    fig, ax = plt.subplots()
    Kenya.plot(ax=ax, facecolor='None', edgecolor='grey', alpha=.7)
    gdf_trans.plot(ax=ax, color='black', markersize=1, label='transformer', marker=".")
    ax.set_axis_off()
    plt.tight_layout()
    plt.legend()
    fig.savefig(path_figure/f'map_Transformers',bbox_inches='tight',pad_inches = 0,dpi=200)  

def plot_population(df_yearly, Kenya, path_figure, cmap='PuBuGn', save=True):
    gdf_yearly = gpd.GeoDataFrame(df_yearly, geometry=df_yearly['geometry'].apply(wkt.loads))
    # plot pop dens of 2015
    data = gdf_yearly[gdf_yearly.year == 2015]
    v = 'pop_dens'
    data[v] = np.log1p(data[v])
    vmin = data[[v]].min()[0]
    vmax = data[[v]].max()[0]
    vcenter = data[[v]].quantile(0.5)[0]
    divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)
    fig, ax = plt.subplots()
    data.plot(column=v, ax=ax, alpha=.7, cmap=cmap, norm=divnorm, legend=True)
    Kenya.plot(ax=ax, facecolor='None', edgecolor='grey')
    ax.set_axis_off()
    plt.tight_layout()
    if save==True:
        fig.savefig(path_figure/f'map_2015_pop_dens',bbox_inches='tight',pad_inches = 0,dpi=200)

def plot_pol_nl(df_yearly, Kenya, path_figure, cmap='PuBuGn', save=True):
    gdf_yearly = gpd.GeoDataFrame(df_yearly, geometry=df_yearly['geometry'].apply(wkt.loads))
    # plot nightlight and pollution
    years = [2015, 2020]
    for v in ['pol','nl']:
        data = gdf_yearly
        data[v] = np.log1p(data[v])
        vmin = data[[v]].min()[0]
        vmax = data[[v]].max()[0]
        vcenter = data[[v]].quantile(0.5)[0]
        divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)
        fig, axes = plt.subplots(ncols=2, sharey=True, sharex=True,constrained_layout = True, figsize=(7,5))
        for y in range(len(years)):
            datay = data[data.year == years[y]] #'PuRd''
            datay.plot(column=v, ax=axes[y], alpha=.7, cmap=cmap, norm=divnorm) 
            Kenya.plot(ax=axes[y], facecolor='None', edgecolor='grey')
            axes[y].set_axis_off()
        patch_col = axes[0].collections[0]
        cb = fig.colorbar(patch_col, ax=axes, shrink=.5)
        if save==True:
            fig.savefig(path_figure/f'map_{v}.png',bbox_inches='tight',pad_inches = 0, dpi=300)

def plot_ts(df, var=str, by=str):
    # prepare data
    filter = 'date_first_vend_prepaid.notnull() & nl.notnull() & dist_tr <= 0.02'
    df.query(filter, inplace=True)
    df['yearmonth'] = pd.to_datetime(df['yearmonth'], format='%Y%m')
    west = ["kakamega", "kericho"]
    df["direction"] = df.apply(lambda row: "west" if row.county in west else "south", axis=1)
    fig, ax = plt.subplots()    
    ax.set_prop_cycle(linestyle=["solid", "dashed"], color=["darkgrey", "grey"])
    if by is not None:
        ts = df.groupby(['yearmonth',by])[var].mean().reset_index()
        for c in ts[by].unique():
            data = ts[ts[by]==c]
            ax.plot('yearmonth',var, data=data, label=c)
            ax.legend()
    else: 
        data = df.groupby(['yearmonth'])[var].mean().reset_index()
        ax.plot('yearmonth',var, data=data, color="darkgrey")
    plt.tight_layout()
    fig.savefig(path_figure/f'ts_{var}_mean.png')

if __name__ == "__main__":
    wd, path_figure = setup()
    df, df_yearly, counties = load_data(wd)
    Kenya, Kenya_all = load_shp(wd, counties)
    gdf_trans = get_transformers(df)
    #
    plot_Kenya(Kenya, Kenya_all, path_figure)
    plot_trans(gdf_trans, Kenya, path_figure)
    plot_population(df_yearly, Kenya, path_figure, cmap="plasma", save=True)
    plot_pol_nl(df_yearly, Kenya, path_figure, cmap="plasma", save=True)
    #
    plot_ts(df, "pol", by=None)
    plot_ts(df, "nl", by=None)