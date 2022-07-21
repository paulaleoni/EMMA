## panel IV did

library(tidyverse)
#library(plm)
library(fixest)
library(lubridate)
library(did)

getCurrentFileLocation <-  function()
{
  this_file <- commandArgs() %>% 
    tibble::enframe(name = NULL) %>%
    tidyr::separate(col=value, into=c("key", "value"), sep="=", fill='right') %>%
    dplyr::filter(key == "--file") %>%
    dplyr::pull(value)
  if (length(this_file)==0)
  {
    this_file <- rstudioapi::getSourceEditorContext()$path
  }
  return(dirname(this_file))
}

# set local time to englisch
Sys.setlocale("LC_TIME", "English")

# specify directory
wd <- getCurrentFileLocation()

wd.parent <- dirname(wd)

path_results <- file.path(wd.parent, 'out','results')

# get data
df_path <- file.path(wd.parent,'out','data','dataset_all.csv')
df_panel <- read.csv(df_path)

# prepare data
# drop if population density zero
df_panel <- df_panel %>% filter(pop_dens != 0, !is.na(nl))

df_panel <- df_panel %>% mutate(group = ifelse((len_lmcp == 0) & (len_nonlmcp==0) & (len_preexisting == 0), 'no electricity',
                                   ifelse((len_lmcp >= len_nonlmcp) & (len_lmcp >= len_preexisting),'lmcp',
                                          ifelse((len_nonlmcp >= len_lmcp) & (len_nonlmcp >= len_preexisting),'nonlmcp',
                                                 ifelse((len_preexisting >= len_lmcp) & (len_preexisting >= len_nonlmcp),'preexisting', NA)))))

# keep only those whose distance to transformer is reasonable #0.01 deg = 1111 m
df_panel <- df_panel %>% filter(dist_tr < .03)

# in date format - year-quarter
df_panel['yearquarter'] <- df_panel$yearmonth %>%  
  paste0('01') %>%  
  as.Date(format='%Y%m%d') 
df_panel['date_first_vend_prepaid'] <- df_panel$date_first_vend_prepaid %>%
  paste0('/01') %>% 
  as.Date(format='%Y/%m/%d')
df_panel['start_date'] <- df_panel$start_date %>% 
  as.Date(format='%d-%b-%y')

df_panel <- df_panel %>%  mutate(yearquarter = paste0(year(yearquarter) ,
                                                      quarter(yearquarter)) %>% as.numeric(),
                                 date_first_vend_prepaid = paste0(year(date_first_vend_prepaid) ,
                                                                  quarter(date_first_vend_prepaid)) %>% as.numeric(),
                                 start_date = paste0(year(start_date) ,
                                                      quarter(start_date)) %>% as.numeric())
# need to aggregate data to quarterly level
df_panel <- df_panel %>% group_by(index, yearquarter) %>% summarise(nl=mean(nl),
                                                                    pol = mean(pol),
                                                                    date_first_vend_prepaid = mean(date_first_vend_prepaid),
                                                                    start_date = mean(start_date),
                                                                    group = first(group),
                                                                    lat = mean(lat),
                                                                    lon = mean(lon))

### based on start date

# calculate time to treatment in months
df_start_date <- df_panel %>% 
  mutate(time_to_treatment = start_date - yearquarter) 
max =  -100000
df_start_date[is.na(df_start_date$start_date) & df_start_date$group=='preexisting','time_to_treatment'] = max

staggered_start_date <- feols(fml = log(pol) ~ 1| index + yearquarter | nl ~ i(time_to_treatment,ref = c(-1, max)), 
                              data=df_start_date %>% drop_na(time_to_treatment),
                              vcov=vcov_conley(lat="lat",lon="lon"))


df_start_date[is.na(df_start_date$start_date) & df_start_date$group=='preexisting','start_date'] = 0
sunab_start_date <- feols(fml = log(pol) ~ 1| index +yearquarter | nl ~ sunab(start_date,yearquarter), 
                          data=df_start_date %>% drop_na(start_date), 
                          vcov=vcov_conley(lat="lat",lon="lon"))


## 2x2 did
df_2x2 <- df_panel %>% mutate(year = substr(as.character(yearquarter),1,4) %>% as.numeric())
df_2x2 <- df_2x2 %>% group_by(index, year) %>% summarise(nl=mean(nl),
                                                         pol = mean(pol),
                                                         start_date = mean(start_date),
                                                         start_date = mean(start_date),
                                                         group = first(group),
                                                         lat = mean(lat),
                                                         lon = mean(lon)) %>%
  filter(year %in% c(2015,2020)) %>%
  mutate(post = ifelse(year == 2020,1,0)) 

df_2x2 <- df_2x2 %>% mutate(treat = ifelse(!is.na(start_date),1,
                                           ifelse(group=="preexisting",0,NA)))

did_2x2_start_date <- feols(fml = log(pol) ~ 1 | index + year | nl ~ 1 + i(post,treat,0),
                            data=df_2x2,
                            vcov=vcov_conley(lat="lat",lon="lon"))

# CS
df_cs_start_date <- df_panel

df_cs_start_date['did_group'] <- df_cs_start_date$start_date
# nevertreated
#df_cs[is.na(df_cs$did_group) & (df_cs$group=='preexisting'),'did_group'] <- 0

df_cs_start_date <- df_cs_start_date %>% drop_na(did_group)


df_cs_start_date <- df_cs_start_date %>% mutate(lnpol= log(pol))


#df_cs %>% select(index, yearquarter, nl, lnpol, did_group) %>% arrange(index, yearquarter)

out <- att_gt(yname = "nl",
              gname = "did_group",
              idname = "index",
              tname = "yearquarter",
              xformla = ~1,
              data = df_cs_start_date ,
              est_method = "dr",
              control_group = 'notyettreated', 
              anticipation = 0,
              bstrap=TRUE
)
atts <- tibble(did_group=out$group, yearquarter = out$t, att = out$att)

predictions <- df_cs_start_date %>% left_join(atts) %>% 
  mutate(pred = mean(nl) + att)


cs_start_date <- feols(log(pol) ~ 1 + pred | index + yearquarter,
                       data = predictions,
                       vcov=vcov_conley(lat="lat",lon="lon"))


### based on first vend

# define treatment

df_first_vend <- df_panel %>% 
  mutate(time_to_treatment = date_first_vend_prepaid - yearquarter) 


# keep only rows that have no electricity and
max =  -100000
df_first_vend[is.na(df_first_vend$date_first_vend_prepaid) & df_first_vend$group=='preexisting','time_to_treatment'] = max

staggered_first_vend <- feols(fml = log(pol) ~ 1| index + yearquarter | nl ~ i(time_to_treatment,ref = c(-1, max)), 
                              data=df_first_vend %>% drop_na(time_to_treatment), 
                              vcov=vcov_conley(lat='lat',lon='lon'))

df_first_vend[is.na(df_first_vend$date_first_vend_prepaid) & df_first_vend$group=='preexisting','date_first_vend_prepaid'] = 0
sunab_first_vend <- feols(fml = log(pol)  ~ 1 |index + yearquarter| nl~ sunab(date_first_vend_prepaid,yearquarter)   , 
                          data=df_first_vend %>% drop_na(date_first_vend_prepaid))#,
                         # vcov=vcov_conley(lat="lat",lon="lon"))


aggregate(staggered_start_date$iv_first_stage$nl, agg=c("ATT" = "(time_to_treatment)(::)(-?[[:digit:]])+?"))
aggregate(staggered_start_date$iv_first_stage$nl, agg=c("ATT" = "(.*)"))
summary(staggered_start_date$iv_first_stage$nl, agg=c("ATT" = "(time_to_treatment)(.*)"))
names = sum$model_matrix_info[[1]]$coef_names_full
etable(staggered_start_date$iv_first_stage$nl, agg=c("ATT" = "(.)*"))


aggregate(sunab_first_vend$iv_first_stage$nl,  agg=c("ATT" = "(year.*er)::(-?[[:digit:]]+?):(.*)"))
etable(sunab_first_vend$iv_first_stage$nl,  agg="ATT")
summary(sunab_first_vend$iv_first_stage$nl, agg="cohort")

## 2x2 did
df_2x2 <- df_panel %>% mutate(year = substr(as.character(yearquarter),1,4) %>% as.numeric())
df_2x2 <- df_2x2 %>% group_by(index, year) %>% summarise(nl=mean(nl),
                                                        pol = mean(pol),
                                                        date_first_vend_prepaid = mean(date_first_vend_prepaid),
                                                        start_date = mean(start_date),
                                                        group = first(group),
                                                        lat = mean(lat),
                                                        lon = mean(lon)) %>%
  filter(year %in% c(2015,2020)) %>%
  mutate(post = ifelse(year == 2020,1,0)) 

df_2x2 <- df_2x2 %>% mutate(treat = ifelse(!is.na(date_first_vend_prepaid),1,
                                           ifelse(group=="preexisting",0,NA)))

did_2x2_first_vend <- feols(fml = log(pol) ~ 1 | index + year | nl ~ 1 + i(post,treat,0),
                       data=df_2x2,
                       vcov=vcov_conley(lat="lat",lon="lon"))


#### C & S'A ####
# based on first vending
df_cs_first_vend <- df_panel

df_cs_first_vend['did_group'] <- df_cs_first_vend$date_first_vend_prepaid
# nevertreated
#df_cs[is.na(df_cs$did_group) & (df_cs$group=='preexisting'),'did_group'] <- 0

df_cs_first_vend <- df_cs_first_vend %>% drop_na(did_group)


df_cs_first_vend <- df_cs_first_vend %>% mutate(lnpol= log(pol))


#df_cs %>% select(index, yearquarter, nl, lnpol, did_group) %>% arrange(index, yearquarter)

out <- att_gt(yname = "nl",
              gname = "did_group",
              idname = "index",
              tname = "yearquarter",
              xformla = ~1,
              data = df_cs_first_vend ,
              est_method = "dr",
              control_group = 'notyettreated', 
              anticipation = 0,
              bstrap=TRUE
)
#summary(out)

#aggte(out, type='group')
#aggte(out, type='dynamic')
#agg.simple <- aggte(out, type='simple')

#ggdid(aggte(out, type='dynamic'))

# try to get fitted values - rethink about this
atts <- tibble(did_group=out$group, yearquarter = out$t, att = out$att)

predictions <- df_cs_first_vend %>% left_join(atts) %>% 
  mutate(pred = mean(nl) + att)

predictions %>% mutate(res = nl-pred) %>% summary()

cs_first_vend <- feols(log(pol) ~ 1 + pred | index + yearquarter,
            data = predictions,
            vcov=vcov_conley(lat="lat",lon="lon"))


#### export results ####


etable(sunab_first_vend, staggered_first_vend,cs_first_vend, did_2x2_first_vend,
       vcov = vcov_conley(lat="lat",lon="lon"),
       headers = c('Sun & Abraham',
                   'TWFE',
                   "C & S'A - first attempt",
                   " 2x2 did"),
       placement= 'H', adjustbox = NULL, fit_format = "$\\widehat{__var__}$",
       title = 'treat: first vending at transformer level',
       file=file.path(path_results, 'treat_first_vend.tex'),replace = TRUE)

etable(sunab_first_vend, staggered_first_vend, agg='(time_to_treatment)',  vcov = vcov_conley(lat="lat",lon="lon"), stage=1,
       headers = c('Sun & Abraham',
                   'TWFE'),
       placement= 'H', adjustbox = 1, fit_format = "$\\widehat{__var__}$",
       title = 'treat: first vending at transformer level')#,
       #file=file.path(path_results, 'treat_first_vend_first.tex'),replace = TRUE)

etable(sunab_start_date, staggered_start_date,cs_start_date, did_2x2_start_date,
       vcov = vcov_conley(lat="lat",lon="lon"),
       headers = c('Sun & Abraham',
                   'TWFE',
                   "C & S'A - first attempt",
                   "2x2 did"),
       placement= 'H', adjustbox = NULL, fit_format = "$\\widehat{__var__}$",
       title = 'treat: start date at transformer level',
       file=file.path(path_results, 'treat_start_date.tex'),replace = TRUE)

# export staggered did results
etable(staggered_first_vend, staggered_start_date,
       headers = c('treat: first vending at transformer level',
                   'treat: start date of construction at transformer level'),
       placement= 'H', adjustbox = 1, fit_format = "$\\widehat{__var__}$",
       title = 'staggered did - treat: first vending at transformer level',
       file=file.path(path_results, 'staggered_did.tex'),replace = TRUE)



