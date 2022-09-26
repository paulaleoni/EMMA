library(tidyverse)
#library(plm)
library(fixest)
library(lubridate)
library(xtable)


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
df_path <- file.path(wd.parent,'out','data','dataset_yearly.csv')
df <- read.csv(df_path)

# prepare data
# drop if population density zero
df <- df %>% filter(pop_dens != 0, nl >= 0)
# define groups
df <- df %>% mutate(group = ifelse((len_lmcp == 0) & (len_nonlmcp==0) & (len_preexisting == 0), 'no electricity',
                                   ifelse((len_lmcp >= len_nonlmcp) & (len_lmcp >= len_preexisting),'lmcp',
                                          ifelse((len_nonlmcp >= len_lmcp) & (len_nonlmcp >= len_preexisting),'nonlmcp',
                                                 ifelse((len_preexisting >= len_lmcp) & (len_preexisting >= len_nonlmcp),'preexisting', NA)))))

#df %>% filter(group=='preexisting') %>% select(starts_with('n_'), starts_with('len'),group) %>% distinct()

# define treatment
df <- df %>% mutate(treat_lmcp_no = ifelse(group=='lmcp',1,
                                                   ifelse(group=='no electricity',0,NA)),
                            treat_electricity = ifelse(group=='no electricity',0,1),
                            treat_lmcp_nonlmcp = ifelse(group=='lmcp',1,
                                                        ifelse(group=='nonlmcp',0,NA)),
                            treat_lmcp_preexisting = ifelse(group=='lmcp',1,
                                                            ifelse(group=='preexisting',0,NA)),
                            treat_nonlmcp_no = ifelse(group=='nonlmcp',1,
                                                      ifelse(group=='no electricity',0,NA)),
                            treat_preexisting_no = ifelse(group=='preexisting',1,
                                                          ifelse(group=='no electricity',0,NA)))

#### 2x2 did ####

# keep 2015 and 2020 data
df_2x2 <- df %>% filter(year %in% c(2015,2020))
df_2x2 <- df_2x2 %>% mutate(post = ifelse(year == 2020,1,0))


# distribution of groups
n_years <- df_2x2 %>% select(year) %>% distinct() %>% nrow()
group_distribution <- df_2x2 %>% group_by(group) %>% summarise(n= n()/n_years)
out_path <- file.path(path_results, "did_group_dist.tex")
print(xtable(group_distribution, caption = "distribution of groups in grid", digits=0), 
      file = out_path, compress = FALSE, type='latex', include.rownames = FALSE)


# estimation

treatments <- c("treat_lmcp_no","treat_lmcp_preexisting","treat_lmcp_nonlmcp",
                "treat_electricity","treat_nonlmcp_no","treat_preexisting_no")

ivs <- list()
rfs <- list()

for(treat in treatments){
  #print(treat)
  fml_iv <- as.formula(paste0("log(pol) ~1 | index + year | nl ~ 1 + i(post,",treat,",0)"))
  ivs[[treat]] <- feols(fml = fml_iv , 
                        data=df_2x2, vcov=vcov_conley(lat='lat',lon='lon'))
  fml_rf <- as.formula(paste0("log(pol) ~ 1 + i(post,",treat,",0) | index + year"))
  rfs[[treat]] <- feols(fml = fml_rf , 
                        data=df_2x2, vcov=vcov_conley(lat='lat',lon='lon'))
}

# export results
etable(ivs, stage=1, 
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2,se.row=TRUE,
       title = 'first stage',
       file=file.path(path_results, 'did_2x2_first.tex'),replace = TRUE)

etable(ivs, stage=2, 
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2, fit_format = "$\\widehat{__var__}$",se.row=TRUE,
       title = 'second stage',
       file=file.path(path_results, 'did_2x2_second.tex'),replace = TRUE)

etable(rfs,
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2, se.row=TRUE,
       title = 'reduced form',
       file=file.path(path_results, 'did_2x2_rf.tex'),replace = TRUE)

#### different years ####

df_2x2 <- df %>% filter(year %in% c(2014,2015,2020))
df_2x2 <- df_2x2 %>% group_by(index, year) %>% ungroup(year) %>% 
  mutate(lag_pol = ifelse(year %in% c(2014,2015),lag(pol),pol),
         mean_pol = (pol + lag_pol)/2) #%>% select(index, year, pol, lag_pol, mean_pol)
df_2x2 <- df_2x2 %>% mutate(post = ifelse(year == 2020,1,0))

ivs <- list()
rfs <- list()

for(treat in treatments){
  #print(treat)
  fml_iv <- as.formula(paste0("log(mean_pol) ~1 | index + year | nl ~ 1 + i(post,",treat,",0)"))
  ivs[[treat]] <- feols(fml = fml_iv , 
                        data=df_2x2, vcov=vcov_conley(lat='lat',lon='lon'))
  fml_rf <- as.formula(paste0("log(mean_pol) ~ 1 + i(post,",treat,",0) | index + year"))
  rfs[[treat]] <- feols(fml = fml_rf , 
                        data=df_2x2, vcov=vcov_conley(lat='lat',lon='lon'))
}

# export results
etable(ivs, stage=1, 
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2,se.row=TRUE,
       title = 'first stage - 14/15 vs 2020',
       file=file.path(path_results, 'did_altyears_first.tex'),replace = TRUE)

etable(ivs, stage=2, 
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2, fit_format = "$\\widehat{__var__}$",se.row=TRUE,
       title = 'second stage - 14/15 vs 2020',
       file=file.path(path_results, 'did_altyears_second.tex'),replace = TRUE)

etable(rfs,
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2, se.row=TRUE,
       title = 'reduced form - 14/15 vs 2020',
       file=file.path(path_results, 'did_altyears_rf.tex'),replace = TRUE)

#### alternative treatment definition ####

df_alt_treat <- df %>% filter(year %in% c(2015,2020)) %>%
  mutate(lmcp = ifelse(n_lmcp > 0, 1,
                       ifelse(group=="no electricity",0,NA)),
         post = ifelse(year==2020,1,0))


did_alt_treat <- feols(fml = log(pol) ~ 1 | index + year | nl ~ 1 + i(post,lmcp,0), 
                      data=df_alt_treat, vcov=vcov_conley(lat='lat',lon='lon'))

etable(did_alt_treat$iv_first_stage$nl, did_alt_treat,
       headers=c('first stage','second stage'),
       placement= 'H', adjustbox = NULL, fit_format = "$\\widehat{__var__}$",se.row=TRUE,
       title = 'alternative treatment definition: any lmcp vs no electricity',
       file=file.path(path_results, 'did_alt_treat.tex'),replace = TRUE)


#### change in pollution ####

df_change <- df %>% filter(year %in% c(2015,2020))

cols <- df_change %>% group_by(index, year)  %>% select(index, year, pol, nl, group, lat, lon)
df_change <- df_change %>% group_by(index, year) %>% ungroup(year) %>% 
  summarise(row = row_number()) %>%
  cbind(cols[,c('pol','nl','group','lat','lon')]) %>% 
  mutate(dpol = pol - lag(pol),
         dnl = nl - lag(nl)) %>% drop_na(dpol)

# estimation

#treatments <- df_change %>% ungroup() %>% select(starts_with('treat')) %>% colnames()
treatments <- c("treat_lmcp_no","treat_lmcp_preexisting","treat_lmcp_nonlmcp",
                "treat_electricity","treat_nonlmcp_no","treat_preexisting_no")

ivs <- list()
rfs <- list()

for(treat in treatments){
  #print(treat)
  fml_iv <- as.formula(paste0("dpol ~1 | dnl ~ ",treat))
  ivs[[treat]] <- feols(fml = fml_iv , 
                        data=df_change, vcov=vcov_conley(lat='lat',lon='lon'))
  fml_rf <- as.formula(paste0("dpol ~1 +  ",treat))
  rfs[[treat]] <- feols(fml = fml_rf , 
                        data=df_change, vcov=vcov_conley(lat='lat',lon='lon'))
}


# export results

etable(ivs, stage=1, 
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2,se.row=TRUE,
       title = 'first stage - changes',
       file=file.path(path_results, 'did_change_first.tex'),replace = TRUE)

etable(ivs, stage=2, 
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2, fit_format = "$\\widehat{__var__}$",se.row=TRUE,
       title = 'second stage - changes',
       file=file.path(path_results, 'did_change_second.tex'),replace = TRUE)

etable(rfs,
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2, se.row=TRUE,
       title = 'reduced form - changes',
       file=file.path(path_results, 'did_change_rf.tex'),replace = TRUE)

#### separate regression for high/low population based on median ####
median_pop_group <- df %>% filter(year %in% c(2015,2020)) %>% 
  group_by(group,index) %>% summarise(pop = mean(pop_dens)) %>% ungroup(index) %>% 
  summarise(pop_group_med = median(pop)) 

df_pop <- df %>% left_join(median_pop_group, by='group') %>% 
  mutate(pop_cat = ifelse(pop_dens >= pop_group_med,"high","low"))


df_pop <- df_pop %>% filter(year %in% c(2015,2020))
df_pop <- df_pop %>% mutate(post = ifelse(year == 2020,1,0))

treatments <- c("treat_lmcp_no","treat_lmcp_preexisting","treat_lmcp_nonlmcp",
                "treat_electricity","treat_nonlmcp_no","treat_preexisting_no")

iv_high <- list()
iv_low <- list()

for(treat in treatments){
  #print(treat)
  fml_iv <- as.formula(paste0("log(pol) ~1 | index + year | nl ~ 1 + i(post,",treat,",0)"))
  iv_high[[treat]] <- feols(fml = fml_iv , 
                        data=df_pop %>% filter(pop_cat == "high"), vcov=vcov_conley(lat='lat',lon='lon'))
  iv_low[[treat]] <- feols(fml = fml_iv , 
                            data=df_pop %>% filter(pop_cat == "low"), vcov=vcov_conley(lat='lat',lon='lon'))
}

etable(iv_high, stage=2, 
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2, fit_format = "$\\widehat{__var__}$",se.row=TRUE,
       title = 'second stage - high population density',
       file=file.path(path_results, 'did_highpop_second.tex'),replace = TRUE)

etable(iv_low, stage=2, 
       headers = c('lmcp vs no elec',
                   'lmcp vs preexisting',
                   'lmcp vs nonlmcp',
                   'elec vs no elec',
                   'nonlmcp vs no elec',
                   'preexisting vs no elec'),
       placement= 'H', adjustbox = 1.2, fit_format = "$\\widehat{__var__}$",se.row=TRUE,
       title = 'second stage - low population density',
       file=file.path(path_results, 'did_lowpop_second.tex'),replace = TRUE)
