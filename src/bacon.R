
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
path_figures <- file.path(wd.parent, 'out','figures')

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
df_panel <- df_panel %>% filter(dist_tr < .02)

# in date format - year-quarter
df_panel['yearquarter'] <- df_panel$yearmonth %>%  
  paste0('01') %>%  
  as.Date(format='%Y%m%d') 
df_panel['date_first_vend_prepaid'] <- df_panel$date_first_vend_prepaid %>%
  paste0('/01') %>% 
  as.Date(format='%Y/%m/%d')
df_panel['start_date'] <- df_panel$start_date %>% 
  as.Date(format='%d-%b-%y')

df_panel <- df_panel %>%  mutate(yearquarter = paste0(year(yearquarter), 
                                                      ifelse(quarter(yearquarter) == 1, '.0',
                                                             ifelse(quarter(yearquarter) == 2, ".25",
                                                                    ifelse(quarter(yearquarter) == 3, ".5",".75")))
                                                      ) %>% as.numeric(),
                                 date_first_vend_prepaid = paste0(year(date_first_vend_prepaid) ,
                                                                  ifelse(quarter(date_first_vend_prepaid) == 1, '.0',
                                                                         ifelse(quarter(date_first_vend_prepaid) == 2, ".25",
                                                                                ifelse(quarter(date_first_vend_prepaid) == 3, ".5",".75")))
                                                                  ) %>% as.numeric(),
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
### based on first vend

# define treatment

df_first_vend <- df_panel %>% 
  mutate(time_to_treatment = date_first_vend_prepaid - yearquarter) 

max_treat = max(df_first_vend$date_first_vend_prepaid,na.rm=TRUE)
df_first_vend <- df_first_vend %>% 
  mutate(time_to_treatment = ifelse(date_first_vend_prepaid >= max_treat, 100000, time_to_treatment))

df_first_vend[!is.na(df_first_vend$date_first_vend_prepaid),'date_first_vend_prepaid']

staggered_first_vend <- feols(fml = nl ~ 1 + i(time_to_treatment,ref = c(-.25, 100000)) | index + yearquarter , 
                              data=df_first_vend , 
                              vcov=vcov_conley(lat='lat',lon='lon'))
'''
agg_stag_first_vend <- aggregate(staggered_first_vend, agg=c("ATT" = "(.*)"))

summary(sunab_first_vend, agg = "att")
summary(staggered_first_vend, agg = "(.*)")

sunab_first_vend <- feols(fml = nl~ sunab(date_first_vend_prepaid,yearquarter)|index + yearquarter, 
                          data=df_first_vend %>% filter(!is.na(date_first_vend_prepaid)))
summary(sunab_first_vend, agg = "att")
aggregate(sunab_first_vend, agg="att", vcov=vcov_conley(lat="lat",lon="lon"))
aggregate(staggered_first_vend, agg=c("ATT" = "(.*)"))

iplot(list(staggered_first_vend, sunab_first_vend), sep=0.1)
legend("topleft", col = c(1, 2), pch = c(20, 17), 
       legend = c("TWFE", "Sun & Abraham (2020)"))
'''

# becon de comp
# late vs. early is the problem
#install.packages("bacondecomp")
library(bacondecomp)

df_first_vend <- df_first_vend %>% mutate(post = ifelse(time_to_treatment < 0, 1, 0))
#df_first_vend$yearquarter <- df_first_vend$yearquarter %>% as.integer()

#df_first_vend %>% select(index, yearquarter, date_first_vend_prepaid, time_to_treatment, post) %>% filter(!is.na(post))


bacon_res <- bacon(pol ~ post, 
      data = df_first_vend %>% filter(!is.na(post)),
      id_var = "index",
      time_var = "yearquarter")
'''
                      type  weight  avg_est
1 Earlier vs Later Treated 0.45785  0.02306
2 Later vs Earlier Treated 0.49204 -0.03403
3     Treated vs Untreated 0.05012  0.04377
'''
0.45875 * 0.02306 + 0.49204 * -0.03403 + 0.05012 * 0.04377  # not significant

library(ggplot2)

ggplot(bacon_res) +
  aes(x = weight, y = estimate, color = factor(type), shape = factor(type)) +
  geom_point() +
  geom_hline(yintercept = 0) + 
  theme_minimal() +
  labs(x = "Weight", y = "Estimate", color = "Type", shape="Type")


fe <- feols(fml = log(pol) ~ 1 + post | index + yearquarter , 
                              data=df_first_vend , 
                              vcov=vcov_conley(lat='lat',lon='lon'))

0.45876 * 0.02269 + 0.49084 * -0.03358 + 0.0504 * 0.04361  # not significant

bacon_res[bacon_res['type'] != "Later vs Earlier Treated",] %>% 
  mutate(est_wei = estimate*weight) %>% select(est_wei) %>% sum()
