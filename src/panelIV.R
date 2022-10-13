## panel IV did

library(tidyverse)
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

# load conley function
#setwd("C:/Users/paula/OneDrive/Documents/400_VWL/411 Master/EMMA/empirics/src")
source(file.path(wd, "helper-conley.R"))

# get data
df_path <- file.path(wd.parent,'out','data','dataset_all.csv')
df_panel <- read.csv(df_path)

# prepare data
# drop if population density zero
df_panel <- df_panel %>% filter(pop_dens != 0, !is.na(nl))

#df_panel <- df_panel %>% mutate(group = ifelse((len_lmcp == 0) & (len_nonlmcp==0) & (len_preexisting == 0), 'no electricity',
 #                                  ifelse((len_lmcp >= len_nonlmcp) & (len_lmcp >= len_preexisting),'lmcp',
  #                                        ifelse((len_nonlmcp >= len_lmcp) & (len_nonlmcp >= len_preexisting),'nonlmcp',
   #                                              ifelse((len_preexisting >= len_lmcp) & (len_preexisting >= len_nonlmcp),'preexisting', NA)))))

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
                                                                                ifelse(quarter(date_first_vend_prepaid) == 3, 
                                                                                       ".5",".75")))
                                                                  ) %>% as.numeric(),
                                 start_date = paste0(year(start_date) ,
                                                     ifelse(quarter(start_date) == 1, '.0',
                                                            ifelse(quarter(start_date) == 2, ".25",
                                                                   ifelse(quarter(start_date) == 3, 
                                                                          ".5",".75")))
                                 ) %>% as.numeric())

#df_panel  %>% group_by(date_first_vend_prepaid) %>% summarise(n())
df_panel %>% select(index, date_first_vend_prepaid) %>% distinct() %>% group_by(date_first_vend_prepaid) %>% summarise(n())
#df_panel <- df_panel %>% filter(date_first_vend_prepaid >= 2016)

# need to aggregate data to quarterly level
df_panel <- df_panel %>% group_by(index, yearquarter) %>% summarise(nl=mean(nl),
                                                                    pol = mean(pol),
                                                                    date_first_vend_prepaid = mean(date_first_vend_prepaid),
                                                                    start_date = mean(start_date),
                                                                    #group = first(group),
                                                                    lat = mean(lat),
                                                                    lon = mean(lon),
                                                                    transformer = first(geometry_transformer)) #%>% 
  #filter(yearquarter > 2014)


### based on first vend

# define treatment

df_first_vend <- df_panel %>% 
  mutate(time_to_treatment = yearquarter - date_first_vend_prepaid) 

max_treat = max(df_first_vend$date_first_vend_prepaid,na.rm=TRUE)
df_first_vend <- df_first_vend %>% 
  mutate(time_to_treatment = ifelse(date_first_vend_prepaid >= max_treat, 100000, time_to_treatment))

staggered_first_vend <- feols(fml = log(pol) ~ 1| index + yearquarter | nl ~ i(time_to_treatment,ref = c(-.25, 100000)), 
                              data=df_first_vend, 
                              vcov=vcov_conley(lat='lat',lon='lon'))

staggered_rf <- feols(fml = log(pol) ~ i(time_to_treatment,ref = c(-.25, 100000))| index + yearquarter , 
                              data=df_first_vend, 
                              vcov=vcov_conley(lat='lat',lon='lon'))
######################

'''
data <- df_first_vend %>% drop_na(time_to_treatment) %>% ungroup()


#staggered_first_vend <- feols(fml = log(pol) ~ 1 + nl| index + yearquarter, 
                         #     data=data, 
                          #    vcov=vcov_conley(lat="lat",lon="lon"))


timeid <- data %>% select(yearquarter)
panelid <-data %>% select(index)

fe <- data %>% select(index, yearquarter)
coords <- data %>% select(lon, lat)


#X <- data %>% select(rows) %>% as.matrix()

#Xdem <- demean(X,as.matrix(fe))

nl <- data %>% select(nl) %>% as.matrix()

nl_dem <- demean(nl,as.matrix(fe))

beta <- staggered_first_vend$coeftable[,1] %>% as.matrix()

betaX <- nl_dem %*% beta

y <- data %>% mutate(logpol=log(pol)) %>% select(logpol)
ydem <- demean(y, as.matrix(fe)) 



e <- ydem - nl_dem %*% beta

 
X <- staggered_first_vend$iv_first_stage$nl$fitted.values_demean


ses <- conley_ses(X,e,as.matrix(coords), dist_cutoff = 2.259, id = panelid, time=timeid)

#ses$Spatial_HAC
#staggered_first_vend$cov.scaled

sqrt(diag(ses$Spatial_HAC))
staggered_first_vend$coeftable
'''




###########################
#post_first_vend <- feols(fml = log(pol) ~ 1| index + yearquarter | nl ~ post, 
                       #  data=df_first_vend, 
                        # vcov=vcov_conley(lat='lat',lon='lon'))

#df_first_vend[is.na(df_first_vend$date_first_vend_prepaid) & df_first_vend$group=='preexisting','date_first_vend_prepaid'] = 0
sunab_first_vend <- feols(fml = log(pol)  ~ 1 |index + yearquarter| nl~ 
                            sunab(cohort = date_first_vend_prepaid,period=yearquarter, ref.p = c(-1)), 
                          data=df_first_vend %>% drop_na(date_first_vend_prepaid),
                          #vcov=vcov_conley(lat="lat",lon="lon")
                          )

sunab_rf <- feols(fml = log(pol)~ sunab(cohort = date_first_vend_prepaid,period=yearquarter, ref.p = c(-1))|
                    index + yearquarter, 
                          data=df_first_vend %>% drop_na(date_first_vend_prepaid),
                          #vcov=vcov_conley(lat="lat",lon="lon")
                  )

#sunab_first_vend$coeftable[,2] <- vcov_conley(sunab_first_vend)
## 2x2 did
df_2x2 <- df_panel %>% mutate(year = substr(as.character(yearquarter),1,4) %>% as.numeric())
df_2x2 <- df_2x2 %>% group_by(index, year) %>% summarise(nl=mean(nl),
                                                        pol = mean(pol),
                                                        date_first_vend_prepaid = mean(date_first_vend_prepaid),
                                                        start_date = mean(start_date),
                                                        #group = first(group),
                                                        lat = mean(lat),
                                                        lon = mean(lon),
                                                        transformer = first(transformer)) %>%
  filter(year %in% c(2015,2020)) %>%
  mutate(post = ifelse(year == 2020,1,0)) 

# take last group treated as never-treated - set treatment date above maximum date
max_treat = max(df_2x2$date_first_vend_prepaid,na.rm=TRUE)
df_2x2 <- df_2x2 %>% 
  mutate(date_first_vend_prepaid = ifelse(date_first_vend_prepaid >= max_treat, 100000, date_first_vend_prepaid))
df_2x2 <- df_2x2 %>% mutate(treat = ifelse(date_first_vend_prepaid==100000,0,
                                           ifelse(!is.na(date_first_vend_prepaid),1,0)))

did_2x2_first_vend <- feols(fml = log(pol) ~ 1 | index + year | nl ~ 1 + i(post,treat,0),
                       data=df_2x2,
                       vcov=vcov_conley(lat="lat",lon="lon"))

did_2x2_rf <- feols(fml = log(pol) ~ i(post,treat,0)| index + year ,
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

#df_cs_first_vend <- df_cs_first_vend %>% mutate(nl_dem=demean(nl,as.matrix(fe)))


#df_cs %>% select(index, yearquarter, nl, lnpol, did_group) %>% arrange(index, yearquarter)

out <- att_gt(yname = "nl",
              gname = "did_group",
              idname = "index",
              tname = "yearquarter",
              xformla = ~1 ,
              data = df_cs_first_vend ,
              est_method = "dr", #dr
              control_group = 'notyettreated', 
              anticipation = 0,
              bstrap=TRUE,
              clustervars="transformer"
)

out_rf <- att_gt(yname = "lnpol",
              gname = "did_group",
              idname = "index",
              tname = "yearquarter",
              xformla = ~1 ,
              data = df_cs_first_vend ,
              est_method = "dr", #dr
              control_group = 'notyettreated', 
              anticipation = 0,
              bstrap=TRUE,
              clustervars="transformer"
)
#summary(out)

#aggte(out, type='group')
#aggte(out, type='dynamic')
#agg.simple <- aggte(out, type='simple')

# try to get fitted values - rethink about this
atts <- tibble(did_group=out$group, yearquarter = out$t, att = out$att)


cs_coefs <-  df_cs_first_vend %>% group_by(yearquarter, did_group) %>% 
  summarise(nl_gt=mean(nl)) %>% inner_join(atts) %>% mutate(pred = nl_gt+att)


predictions <- df_cs_first_vend %>% drop_na(did_group) %>%
  left_join(cs_coefs) %>% mutate(res = nl-pred) %>% drop_na(pred) #%>% summary()



cs_first_vend <- feols(log(pol) ~ 1 + pred | index + yearquarter,
            data = predictions,
            vcov=vcov_conley(lat="lat",lon="lon"))



timeid <- predictions %>% ungroup() %>% select(yearquarter)
panelid <-predictions %>% ungroup() %>% select(index)

fe <- predictions %>% ungroup() %>% select(index, yearquarter)
coords <- predictions %>% ungroup() %>% select(lon, lat)


nl <- predictions %>% ungroup() %>% select(nl) %>% as.matrix()
nl_dem <- demean(nl,as.matrix(fe))

beta <- cs_first_vend$coeftable[,1] %>% as.matrix()

betaX <- nl_dem %*% beta

y <- predictions %>% ungroup() %>% select(lnpol)
ydem <- demean(y, as.matrix(fe)) 


e <- ydem - nl_dem %*% beta


X <- predictions$pred %>% as.matrix()


ses <- conley_ses(X,e,as.matrix(coords), dist_cutoff = 2.2, id = panelid, time=timeid)

sqrt(diag(ses$Spatial_HAC))

cs_first_vend$coeftable[,2] <- sqrt(diag(ses$Spatial_HAC))


### figures of estimates ###

#ggdid(aggte(out, type="dynamic"))
cs_dyn <- aggte(out, type='dynamic')
cs_dyn_rf <- aggte(out_rf, type='dynamic')

estimates <- tibble(time = cs_dyn$egt, coef = cs_dyn$att.egt, se = cs_dyn$se.egt, specification = "CS")
estimates_rf <- tibble(time = cs_dyn_rf$egt, coef = cs_dyn_rf$att.egt, se = cs_dyn_rf$se.egt, specification = "CS")

stag_coefs <- staggered_first_vend$iv_first_stage$nl$coefficients
stag_coefs_rf <- staggered_rf$coefficients

stag_se <- staggered_first_vend$iv_first_stage$nl$se
stag_se_rf <- staggered_rf$se

stag_est <- tibble(time = names(stag_coefs), coef = stag_coefs,se = stag_se, 
                   #CIlow = confint(staggered_first_vend$iv_first_stage$nl)[,1],
                   #CIhigh = confint(staggered_first_vend$iv_first_stage$nl)[,2],
                   specification = "TWFE" )

stag_est_rf <- tibble(time = names(stag_coefs_rf), coef = stag_coefs_rf, se = stag_se_rf, 
                   specification = "TWFE" )

stag_est$time <- gsub("time_to_treatment::","",stag_est$time) %>% as.numeric()
stag_est_rf$time <- gsub("time_to_treatment::","",stag_est_rf$time) %>% as.numeric()


sunab_est <- aggregate(sunab_first_vend$iv_first_stage$nl, "(year.*er)::(-?[[:digit:]]?.?[[:digit:]]+)",
                       #vcov = vcov_conley(lat="lat",lon="lon")
                       ) 
sunab_est_rf <- aggregate(sunab_rf, "(year.*er)::(-?[[:digit:]]?.?[[:digit:]]+)",
                       #vcov = vcov_conley(lat="lat",lon="lon")
                       )

#degrees_freedom(sunab_first_vend$iv_first_stage$nl, type="t",vcov = vcov_conley(lat="lat",lon="lon")) 

sunab_est <- tibble(time = row.names(sunab_est), specification = "SA", coef = sunab_est[,1], se = sunab_est[,2],
                    #CIlow = 0,
                    #CIhigh = 0
                    )
sunab_est_rf <- tibble(time = row.names(sunab_est_rf), specification = "SA", coef = sunab_est_rf[,1], se = sunab_est_rf[,2])

sunab_est$time <- gsub("yearquarter::","",sunab_est$time) %>% as.numeric()
sunab_est_rf$time <- gsub("yearquarter::","",sunab_est_rf$time) %>% as.numeric()


alpha = 0.05
estimates <- estimates %>% rbind(stag_est) %>% 
  rbind(sunab_est) %>% mutate(lb = coef - 1.96 * se , ub = coef + 1.96 * se )

estimates_rf <- estimates_rf %>% rbind(stag_est_rf) %>% rbind(sunab_est_rf) %>% mutate(lb = coef - 1.96 * se ,
                                                                                       ub = coef + 1.96 * se )


pd <- position_dodge(width=0.15)

ggplot(estimates,aes(time, coef, shape=specification, alpha=specification)) + 
  geom_hline(yintercept=0, color="grey") +
  #geom_vline(xintercept=0, color="grey") +
  geom_point(position = pd, size=1) +
  geom_errorbar(aes(ymin=lb,ymax=ub), width = 0.1,position = pd) +  
  scale_shape_manual(values = c(19,5,6)) +
  theme_classic() + 
  labs(title = "Average Effect by Length of Exposure", color="") + 
  xlab("") + ylab("") + #facet_wrap(~specification, ncol=1, strip.position = "right")
  #xlim(-6,7) + 
  theme(text = element_text(size=6), legend.position = c(0.5,0.9), legend.direction = "horizontal")
  
ggsave(file.path(path_figures, "event_study_estimators.png"), dpi = 600)

ggplot(estimates_rf,aes(time, coef, color=specification)) + 
  geom_hline(yintercept=0, color="grey") +
  #geom_vline(xintercept=0, color="grey") +
  geom_point(position = pd, size=.1) +
  geom_errorbar(aes(ymin=lb,ymax=ub), width = 0.1,position = pd) +  
  theme_classic() + 
  labs(title = "Average Effect by Length of Exposure", color="") + 
  xlab("") + ylab("") + #facet_wrap(~specification, ncol=1, strip.position = "right")
  #xlim(-6,7) + 
  theme(text = element_text(size=6), legend.position = c(0.5,0.9), legend.direction = "horizontal")

ggsave(file.path(path_figures, "event_study_estimators_rf.png"), dpi = 600)


ggdid(cs_dyn, width=0.1, xgap=4) + 
  theme(axis.text.x = element_blank(), axis.ticks.x = element_blank(), 
        text = element_text(size=6)) 
ggsave(file.path(path_figures, "trend_first_vend.png"))

#ggplot() + geom_point(aes(cs_dyn$egt, cs_dyn$att.egt))


#iplot(staggered_first_vend$iv_first_stage$nl$)
#iplot(sunab_first_vend$iv_first_stage$nl)

#coefplot(staggered_first_vend$iv_first_stage$nl)

#### export results ####


etable(cs_first_vend, sunab_first_vend, staggered_first_vend,did_2x2_first_vend,
       vcov = vcov_conley(lat="lat",lon="lon"),
       fitstat = c("n","ar2","f.stat","ivf1.stat"),
       se.row=TRUE,
       headers = c("Callaway & Sant'Anna",
                   'Sun & Abraham',
                   'dynamic TWFE',
                   " 2x2 did"),
       placement= 'H', adjustbox = TRUE, fit_format = "$\\widehat{__var__}$",
       dict = c("resest", pred="$\\widehat{nl}$"),label="tab:estimates",
       title = 'results of second stage',
       file=file.path(path_results, 'treat_first_vend.tex'),replace = TRUE)


# export first stage results
agg_stag_first_vend <- aggregate(staggered_first_vend$iv_first_stage$nl, agg=c("ATT" = "(.*)"))
agg_sunab_first_vend <- aggregate(sunab_first_vend$iv_first_stage$nl, agg=c("ATT" = "att"))
#agg_did_2x2_first_vend <- aggregate(staggered_first_vend$iv_first_stage$nl, agg=c("ATT" = "(.*)"))

staggered_first_vend$iv_first_stage$nl$coeftable <- agg_stag_first_vend
sunab_first_vend$coeftable <- agg_sunab_first_vend
  

etable(staggered_first_vend$iv_first_stage$nl)
etable(sunab_first_vend$iv_first_stage$nl, agg = c("ATT" = "(.*)"))

#sunab_first_vend <- feols(fml = log(pol)  ~ 1 + sunab(date_first_vend_prepaid,yearquarter)|index + yearquarter, 
 #                         data=df_first_vend)
summary(sunab_first_vend, agg="ATT")

etable(staggered_first_vend$iv_first_stage$nl,did_2x2_first_vend$iv_first_stage$nl)

summary(staggered_first_vend$iv_first_stage$nl)
#names = sum$model_matrix_info[[1]]$coef_names_full
etable(staggered_first_vend$iv_first_stage$nl, agg=c("ATT" = "(time_to_treatment)(::)(-?[[:digit:]])+?"))


aggregate(sunab_first_vend$iv_first_stage$nl,  agg=c("ATT" = "att"),
          vcov = vcov_conley(lat="lat",lon="lon"))
summary(sunab_first_vend$iv_first_stage$nl,  agg=c("ATT" = "(.)*"))
summary(sunab_first_vend$iv_first_stage$nl, agg="(yearquarter)")

aggte(out, type='simple', alp = 0.025)

