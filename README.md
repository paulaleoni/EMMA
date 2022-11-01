# Can Rural Electrification Reduce Air Pollution? A Staggered Treatment Adoption Analysis

This repository contains code related to my master thesis. I make use of variation in treatment timing, i.e. access to electricity, to quantify the impact on fine particulate matter. I find evidence, that household transform their lighting strategy by switching form kerosene lamps to cleaner and brighter electric light bulbs. This reduces the concentration of particulate matter in that region. 

## Structure

## Data

I combine satellite-derived images of fine particulate matter and nightlight with data on the timing of electricity connections. 

The nightlight data is based on the Visible and Infrared Imaging Suite (VIIRS) Day Night Band (DNB) (see https://eogdata.mines.edu/products/vnl/#v1). The python script src/get_nightlight_data.py downloads the relevant files automatically and transforms the raster type data into a panel dataframe and outputs a single csv file.

The dataset by van Donkelaar et al. (2021) combines data of NASA's MODIS, MISR, and SeaWIFS instruments on aerosol optical depth to derive an estimate of PM$_{2.5}$. The dataset is not scrabable and needs to be downloaded by hand. The script src/get_pollution_data.py merges the individual files into a single csv file.

Together with population data from the \textit{Gridded Population of the World} dataset from the \textit{Center for International Earth Science Information Network} the script src/merge_raster_data.py performs spatial joins of the gridded data sources.

The file src/merge_all.py merges the relevant transformer information to the dataset.

## Analysis


