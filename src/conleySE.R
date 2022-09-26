# https://gist.github.com/devmag/f18ec223df7aef78402b

#####VECTORISED FUNCTION

library(data.table)
library(geosphere)
library(foreign)
library(lfe)
library(reshape)


iterateObs<-function(y1,e1,X1,fordist,coefficients,cutoff=250000) {
  
  ##recognise whether it is lat/long or single dimension (i.e. time) for distance computation
  if(ncol(fordist)==2) {
    distances<-lapply(1:nrow(X1), function(k) distHaversine(fordist[k,],as.matrix(fordist)))
    XeeXhs<-lapply(1:nrow(X1), function(k) (  t(t(X1[k,])) %*% matrix(nrow=1,ncol=nrow(X1),data=e1[k])   * (matrix(nrow=length(coefficients),ncol=1,1)%*% (t(e1) * (distances[[k]]<=cutoff)))) %*% X1) 
    
  } else {
    abstimediff <-lapply(1:nrow(fordist), function(k) abs(fordist[k]-fordist) )
    window<-lapply(1:nrow(fordist), function(k) ((abstimediff[[k]] <= cutoff) * (1-abstimediff[[k]])/(cutoff+1)) * (fordist!=fordist[k])  )	
    
    XeeXhs<-lapply(1:nrow(X1), function(k) (  t(t(X1[k,])) %*% matrix(nrow=1,ncol=nrow(X1),data=e1[k])   * (matrix(nrow=length(coefficients),ncol=1,1)%*% (t(e1) * (t(window[[k]]))))) %*% X1) 
  }
  XeeXhs <- Reduce("+", XeeXhs)
  
  XeeXhs
}
###try to vectorise the function



conleyHAC<-function(y,yhat,X,coords,coefficients=NULL,timeid,panelid, dist_cutoff=200000,lag_cutoff=3) {
  
  e<-y-yhat
  XeeX = matrix(data=0, nrow=length(coefficients),ncol=length(coefficients))
  times<-names(table(timeid))
  n=length(y)
  X<-as.matrix(X)
  
  ###spatial correlation correction
  XeeXhs<-lapply(times, function(x) iterateObs(y1=y[timeid==x],e1=e[timeid==x],X1=matrix(X[timeid==x,]),fordist=as.matrix(coords[timeid==x,]),coefficients,cutoff=dist_cutoff))
  
  ##first reduce
  XeeX <- Reduce("+", XeeXhs)
  
  invXX = solve(t(X)%*%X) * n
  
  XeeX_spatial = XeeX / n
  
  V = (invXX %*% XeeX_spatial %*% invXX) / n
  
  V
  
  
  #####serial correlation correction
  panel<-names(table(panelid))
  XeeXhs<-lapply(panel, function(x) iterateObs(y[panelid==x],e[panelid==x],matrix(X[panelid==x,]),matrix(timeid[panelid==x]),coefficients,cutoff=lag_cutoff))
  XeeX <- XeeX+Reduce("+", XeeXhs)
  
  XeeX_spatial_HAC = XeeX / n
  
  V = (invXX %*% XeeX_spatial_HAC %*% invXX) / n
  
  V
  
}


###function call
#setwd("/Users/thiemo/AeroFS/Research/Fracking Growth/SPATIAL")
#df<-data.table(read.dta(file="testspatial.dta"))

##download sample data from http://freigeist.devmag.net/wp-content/testspatial.dta_.zip

##create residuals
#df.lm<-felm(formula = log(EmpClean) ~ post08shale | FIPS + year | (0) | STATE_FIPS, data = df)

###CONLEY ERRORS for COEFFICIENT post08shale

#conleyHAC(df.lm$response,df.lm$fitted.values,df$post08anywell,df[,c("latitude","longitude"),with=F],coefficients=df.lm$coefficients,timeid=df$year,panelid=df$FIPS,dist_cutoff=10000,lag_cutoff=10)
