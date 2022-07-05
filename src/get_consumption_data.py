'''
extract some parameters on transformer from consumption data
output: 
consumption.csv
transformer_ids.csv
'''


import pandas as pd
from pathlib import Path
from zipfile import ZipFile
import re


##### load data #############
wd = Path.cwd()

zipf = ZipFile(wd.parent/'data'/'consumption'/'post_pre_paid.zip')

post = pd.read_csv(zipf.open('Postpaid_AFDB_TX_Data_20220126.txt'), sep = '|')
pre = pd.read_csv(zipf.open('Prepaid_AFDB_TX_Data_20220126.txt'), sep = '|')

zipf = ZipFile(wd.parent/'data'/'consumption'/'cons_data_all.zip')
cons = pd.read_csv(zipf.open('cons_data_all.csv'))

#### link ids ####

pp = pd.concat([post,pre],ignore_index=True)

pp.columns = pp.columns.str.lower()

pp['vending_date'] = pp.billing_date
pp.loc[pp.vending_date.isnull(),'vending_date'] = pp.loc[pp.vending_date.isnull(),'date_of_vend']
pp = pp.drop(['billing_date','date_of_vend'], axis=1)

pp = pp.drop_duplicates(subset=['county','txnumber','transno','full_name','serial_num','account_no'])

cons = cons.drop_duplicates(subset=['county','zrefrence','name','meternumber'])

pp_counties = pp.county.str.lower().unique()
cons_counties = cons.county.str.lower().unique()

pp = pp[pp.county.str.lower().isin(cons_counties)]
cons = cons[cons.county.str.lower().isin(pp_counties)]

mgd = pp.merge(cons, left_on='serial_num', right_on='meternumber', how='inner')

ids = mgd[['county_y','zrefrence','transno','txnumber']].drop_duplicates().rename(columns = {'county_y':'county'})

ids.loc[ids.transno == 'Kwni Market','transno'] = '41755 kwini market'

ids.to_csv(wd.parent/'out'/'data'/'transformer_ids.csv', index=False)

###### get first vending dates prepaid ##########

pre.columns = pre.columns.str.lower()
pre['date_of_vend'] = pd.to_datetime(pre['date_of_vend'])
pre['installation_date'] = pd.to_datetime(pre['installation_date'])
firsts = pre.groupby(['transno'])[['date_of_vend','installation_date']].min().rename(columns = {'date_of_vend':'date_first_vend_prepaid','installation_date':'date_first_inst_prepaid'}).reset_index()

firsts.loc[firsts.transno == 'Kwni Market','transno'] = '41755 kwini market'

ids.loc[ids.zrefrence.notnull(),'county'].value_counts()
'''
KERICHO         81
TAITA TAVETA    32
KITUI           29
KAKAMEGA        23
'''
ids.loc[ids.transno.notnull(),'county'].value_counts()

preid = firsts.merge(ids[['zrefrence','transno','county']], on='transno', how='outer')

preid['date_first_vend_prepaid'] = preid['date_first_vend_prepaid'].dt.strftime('%Y/%m')
preid['date_first_inst_prepaid'] = preid['date_first_inst_prepaid'].dt.strftime('%Y/%m')

preid['tr_number'] = preid['transno'].apply(lambda row: re.findall(r'\d+',row)[0])

preid.to_csv(wd.parent/'out'/'data'/'consumption_firsts.csv',index=False)