'''
make summary tables
'''
import pandas as pd
from pathlib import Path
import geopandas as gpd
from shapely import wkt
import numpy as np

wd = Path.cwd()
path_stats = wd.parent/'out'/'results'

# load data
df = pd.read_csv(wd.parent/'out'/'data'/'dataset_yearly.csv')
df_quarter = pd.read_csv(wd.parent/'out'/'data'/'dataset_quarter.csv')

# prepare data
filter = 'date_first_vend_prepaid.notnull() & nl.notnull() & dist_tr <= 0.02 & pop_dens >0'

df.query(filter, inplace=True)
df_quarter.query(filter, inplace=True)

name_dict = {"pol":"air pollution", "nl":"nightlight", "pop_dens":"population density"}
cor_quar = df_quarter[["pol","nl"]].corr().applymap(lambda x: "{:.2f}".format(x))
cor_year = df.loc[df.year==2015,["pol","nl","pop_dens"]].corr().applymap(lambda x: "{:.2f}".format(x))

cor_table = cor_quar.append(cor_year['pop_dens'])

cor_table.loc["pol","nl"] = np.nan

cor_table = cor_table.fillna("-").rename(columns=name_dict, index=name_dict)

col_align = "r" + cor_table.shape[1]* "c"
cap = "correlation table - the last row measures the correlation when the data is aggregated to the year 2015 to match the population date. The other rows correspond to the whole sample that is taken for the analysis."

with open(path_stats/'stats_corr.tex','w') as tf:
    tf.write(cor_table.style.to_latex(position='H', hrules=True,  label='tab:stats-cor', environment='longtable', multicol_align='c', column_format=col_align, caption=cap))


# https://stackoverflow.com/questions/54466196/descriptive-statistics-in-python-with-pandas-with-std-in-parentheses
idx = pd.IndexSlice
years = [x for x in range(2012,2020+1)]
df_desc = (df[df.year.isin(years)]).groupby(['year'])[['nl','pol']].describe()

df_desc = df_desc.loc[idx[:],idx[:,["mean", "std"]]].T
df_desc.loc[idx[:,["std"]],idx[:]] = df_desc.loc[idx[:,["std"]],idx[:]].applymap(lambda x: "("+"{:.2f}".format(x)+")")

df_desc.loc[idx[:,["mean"]],idx[:]] = df_desc.loc[idx[:,["mean"]],idx[:]].applymap(lambda x: "{:.2f}".format(x))

df_desc=df_desc.reset_index(drop=True)

df_new = pd.DataFrame(df_desc.values, index=["nightlight", "", "air pollution", ""], columns=df_desc.columns)

col_align = 'l' + len(years)*'c'

cap = r"mean and standard deviation (in parentheses) of nightlight (in $nW/cm^2/sr$ ) and PM concentration (in $\mu g/m^3$) by year"

with open(path_stats/'stats.tex','w') as tf:
    tf.write(df_new.style.to_latex(position='H', hrules=True,  label='tab:stats', environment='longtable', multicol_align='c', column_format=col_align, caption=cap))


### transformer statistics
df_trans = df[['geometry_transformer','county']].drop_duplicates().reset_index(drop=True).dropna()
gdf_trans = gpd.GeoDataFrame(df_trans, geometry=df_trans['geometry_transformer'].apply(wkt.loads))

tab_counties = pd.DataFrame(gdf_trans.county.value_counts()).rename(columns={'county':'No'})
tab_counties.index = tab_counties.index.str.capitalize()
tab_counties.loc['Total'] = sum(tab_counties.No)

with open(path_stats/'tab_counties.tex','w') as tf:
    tf.write(tab_counties.style.to_latex(position='H', caption='number of transformers per county',  label='tab:counties', hrules=True, column_format='lc',environment='longtable'))
##########################
# how many grid cells per transformer
'''
trans_ncells = df[(df.year==2020)].groupby(['geometry_transformer','county'])['index'].nunique().rename('n_index')#.describe()

gdf_trans = gdf_trans.merge(trans_ncells, right_index = True, left_on = ['geometry_transformer','county'])

import matplotlib.pyplot as plt
shp_file = wd.parent/'data'/'shp'/'Kenya.zip'
Kenya = gpd.read_file(shp_file)
Kenya = Kenya[['NAME_1','geometry']]
Kenya = Kenya.rename(columns={'NAME_1':'county'})
Kenya.county = Kenya.county.str.lower()

df = gpd.GeoDataFrame(df, geometry=df['geometry'].apply(wkt.loads))

cty = "kakamega"
fig, ax = plt.subplots()
df[(df.county==cty) & (df.year==2015)].plot(ax=ax, color="yellow")
gdf_trans[gdf_trans.county == cty].plot(ax=ax, marker="*", markersize=2)
Kenya[Kenya.county == cty].plot(ax=ax, facecolor="None", edgecolor='grey')
for i,row in gdf_trans[gdf_trans.county == cty].iterrows():
    geom_x = row['geometry'].centroid.x
    geom_y = row['geometry'].centroid.y
    ax.annotate(row.n_index,xy=(geom_x, geom_y), xytext=(7, 0), textcoords="offset points")
plt.xlim(37.75, 38.3)
plt.ylim(-1.7,-0.75)
'''