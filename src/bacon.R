## applies bacon decomposition based on Goodman-Bacon 2021
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
df_path <- file.path(wd.parent,'out','data','dataset_quarter.csv')
df_panel <- read.csv(df_path)

# prepare data
# drop if population density zero
df_panel <- df_panel %>% filter(dist_tr <= 0.02, !is.na(nl))



### based on first vend

# define treatment

df_first_vend <- df_panel %>% 
  mutate(time_to_treatment = (yearquarter - date_first_vend_prepaid)*4) 

#max_treat = max(df_first_vend$date_first_vend_prepaid,na.rm=TRUE)
#df_first_vend <- df_first_vend %>% 
#  mutate(time_to_treatment = ifelse(date_first_vend_prepaid >= max_treat, -100000, time_to_treatment)) %>%
 # filter(yearquarter < max_treat)

staggered_first_vend <- feols(fml = log(pol) ~ 1| index + yearquarter | nl ~ i(time_to_treatment, ref = c(-1,-100000)), 
                              data=df_first_vend,
                              vcov=vcov_cluster("geometry_transformer"))

df_first_vend <- df_first_vend %>% mutate(post = ifelse(yearquarter >= date_first_vend_prepaid, 1, 0))


fe <- feols(fml = nl ~ 1 + post | index + yearquarter , 
                              data=df_first_vend , 
                              vcov=vcov_conley(lat='lat',lon='lon'))
# becon de comp
# late vs. early is the problem
#install.packages("bacondecomp")
library(bacondecomp)

#df_first_vend$yearquarter <- df_first_vend$yearquarter %>% as.integer()

#df_first_vend %>% select(index, yearquarter, date_first_vend_prepaid, time_to_treatment, post) %>% filter(!is.na(post))


bacon_res <- bacon(nl ~ post, 
      data = df_first_vend %>% filter(!is.na(post)),
      id_var = "index",
      time_var = "yearquarter")
'''
                      type  weight  avg_est
1 Earlier vs Later Treated 0.50025 -0.33125
2 Later vs Earlier Treated 0.45408  0.92865
3     Treated vs Untreated 0.04567 -1.197647
'''
0.45875 * 0.02306 + 0.49204 * -0.03403 + 0.05012 * 0.04377  # not significant

library(ggplot2)

ggplot(bacon_res) +
  aes(x = weight, y = estimate, color = factor(type), shape = factor(type)) +
  geom_point() +
  geom_hline(yintercept = 0) + 
  scale_color_grey() +
  theme_minimal() +
  labs(x = "Weight", y = "Estimate", color = "Type", shape="Type")



0.45876 * 0.02269 + 0.49084 * -0.03358 + 0.0504 * 0.04361  # not significant

bacon_res[bacon_res['type'] != "Later vs Earlier Treated",] %>% 
  mutate(est_wei = estimate*weight) %>% select(est_wei) %>% sum()
