
""" Generate absolute photometry plots of the GALEX white dwarf standard star
LDS749B.

The following commands should be copied and pasted into a Python terminal w/
gPhoton installed in order to generate the source data. The function thus
called queries the MCAT for all GALEX observations of LDS749B and constructs
gAperture calls equivalent sky positions and time ranges. The MCAT and
gAperture data are then compiled into a single reference file for comparison.
There is a lot of data, so these will take a long while to run. The functions
write as they go and check objids against what has already been processed, so
you can resume crashed or canceled jobs as long as the output file is the same.

LDS749B w/ 90 arcsecond aperture & large annulus

    from gPhoton.regtestutils import datamaker
    datamaker('FUV',[323.06766667,0.25400000],'LDS749B_dm_FUV_90as.csv',margin=0.001,searchradius=0.001,annulus=[0.025,0.05],radius=0.025)

    from gPhoton.regtestutils import datamaker
    datamaker('NUV',[323.06766667,0.25400000],'LDS749B_dm_NUV_90as.csv',margin=0.001,searchradius=0.001,annulus=[0.025,0.05],radius=0.025)

The following commands will generate the plots. In addition to gPhoton and its
dependencies, you will need matplotlib and scikit-learn.
"""
import numpy as np
import matplotlib.pyplot as plt

import gPhoton.galextools as gt
import gPhoton.dbasetools as db
import gPhoton.MCUtils as mc
from gPhoton.gphoton_utils import read_lc, dmag_errors, data_errors

from sklearn.neighbors import KernelDensity
from sklearn.grid_search import GridSearchCV

# Define I/O directories
outpath = '.'#'calpaper/paper'
inpath = '.'

# Setup reference variables.
scl = 1.4
bands = ['FUV','NUV']

# Read in the calibration data
target = 'LDS749B_90as'
refmag = {'FUV':15.6,'NUV':14.76} # per http://arxiv.org/pdf/1312.3882.pdf
data = {'FUV':read_lc('{path}/LDS749B_dm_FUV_90as.csv'.format(path=inpath)),
        'NUV':read_lc('{path}/LDS749B_dm_NUV_90as.csv'.format(path=inpath))}
radius = 0.025

# Provide some baseline statistics for the sample
ix = {}
for band in data.keys():
    print '{b}: {n} ({m} bad)'.format(b=band,n=len(data[band]['aper4']),
                                     m=len(np.where(data[band]['flags']!=0)[0]))
    ix[band] = np.where((data[band]['flags']==0) & (data[band]['aper4']>0))
    print np.median(np.array(data[band]['aper4'])[ix[band]])

def make_kde(data,datarange,bwrange=[0.01,1]):
    # A function for producing Kernel Density Estimates
    # Based on code from:
    #   https://jakevdp.github.io/blog/2013/12/01/kernel-density-estimation/
    grid = GridSearchCV(KernelDensity(),
        {'bandwidth': np.linspace(bwrange[0],bwrange[1],100)},cv=20,n_jobs=4)
    grid.fit(data[:, None])
    bandwidth = grid.best_params_['bandwidth']
    x = np.linspace(datarange[0],datarange[1],10000)
    kde_skl = KernelDensity(bandwidth=bandwidth)
    kde_skl.fit(data[:, np.newaxis])
    # score_samples() returns the log-likelihood of the samples
    log_pdf = kde_skl.score_samples(x[:, np.newaxis])
    y = np.exp(log_pdf)
    peak = x[np.where(y==y.max())][0]
    return x,y,peak,bandwidth

# Overplot gAperture photometry of LDS749B on the reference magnitude and
# modeled 3-sigma error bounds as a function of exposure time.
nsigma = 3
for band in data.keys():
    tmin,tmax = 0,300
    plt.figure(figsize=(8*scl,4*scl))
    plt.subplots_adjust(left=0.12,right=0.95,wspace=0.1,bottom=0.15,top=0.9)
    plt.errorbar(np.array(data[band]['exptime']),
        np.array(data[band]['mag_mcatbgsub'])-gt.apcorrect1(radius,band),
        fmt='.',color='k',alpha=0.1,
        yerr=[data[band]['mag_mcatbgsub_err_1'],
              data[band]['mag_mcatbgsub_err_2']])
    plt.plot(np.array(data[band]['exptime'])[ix[band]],
        np.array(data[band]['mag_mcatbgsub'])[ix[band]]-
                 gt.apcorrect1(radius,band),'.',
        color='k',alpha=0.2)
    t = np.arange(tmin+1,tmax+1)
    plt.plot(t,refmag[band]*(t/t),'k')
    plt.plot(t,data_errors(refmag[band],band,t,sigma=nsigma)[0],'r--')
    plt.plot(t,data_errors(refmag[band],band,t,sigma=nsigma)[1],'r--')
    plt.xlim(tmin,tmax)
    plt.ylim(refmag[band]-0.5,refmag[band]+1)
    plt.gca().invert_yaxis()
    plt.title('{b}: gAperture Photometry of {target} (n={n})'.format(
        target=target.split('_')[0],b=band,n=len(ix[band][0])),fontsize=18)
    plt.xlabel('Effective Exposure Depth (s)',fontsize=16)
    plt.ylabel('gAperture Magnitude',fontsize=16)
    plt.tick_params(axis='both', which='major', labelsize=14)
    a,b = data_errors(refmag[band],band,
        np.array(data[band]['exptime'])[ix[band]],sigma=nsigma)
    cnt = len(np.where(
        (np.array(data[band]['mag_mcatbgsub'])[ix[band]]-
         gt.apcorrect1(radius,band)>=b) &
        (np.array(data[band]['mag_mcatbgsub'])[ix[band]]-
         gt.apcorrect1(radius,band)<=a))[0])
    print '{b}: {n} of {m} ({p}%) within {s} sigma'.format(
        b=band,n=cnt,m=len(ix[band][0]),p=100*cnt/len(ix[band][0]),s=nsigma)
    plt.text(150, 16.3 if band=='FUV' else 15.4, '{p}% within {s}{sym}'.format(
        p=100*cnt/len(ix[band][0]),s=nsigma,sym=r'$\sigma$'), fontsize=18)
    plt.savefig('{path}/{target}_ABMag_{b}.pdf'.format(path=outpath,
                target=target,b=band),format='pdf',dpi=1000,bbox_inches='tight')
    plt.close()

# Generate distribution plots for gAperture photometry of LDS749B
bincnt=50
fig = plt.figure(figsize=(10*scl,4*scl))
fig.subplots_adjust(left=0.12,right=0.95,wspace=0.1,bottom=0.15,top=0.9)
for i,band in enumerate(data.keys()):
    magrange = [refmag[band]-0.2,refmag[band]+0.7]
    tmin,tmax = 0,350
    plt.subplot(1,2,i+1,xticks=np.arange(round(magrange[0],1),
        round(magrange[1]+0.01,1),0.2),yticks=[])
    mags = np.array(data[band]['mag_mcatbgsub'])-gt.apcorrect1(radius,band)
    plt.hist(mags[ix[band]],bins=bincnt,color='k',histtype='step',
        range=magrange,normed=1)
    plt.axvline(refmag[band], color='g', linestyle='solid', linewidth=4,
        label='Ref: {r} AB Mag'.format(r=round(refmag[band],2)))
    x,y,peak,bandwidth = make_kde(mags[ix[band]],magrange)
    plt.plot(x,y)
    print '{b}: peak={p} ({bw})'.format(b=band,p=peak,bw=bandwidth)
    plt.axvline(peak, color='k', linestyle='dotted', linewidth=2,
        label='KDE Peak: {p}'.format(p=round(peak,2)))
    plt.axvline(np.median(mags[ix[band]]), color='r', linestyle='dashed',
        linewidth=4,
        label='Median: {m}'.format(m=round(np.median(mags[ix[band]]),2)))
    plt.xlim(magrange)
    plt.gca().invert_xaxis()
    plt.legend(loc=2,fontsize=14)
    plt.title('{b}: gAperture Photometry of {target} (n={n})'.format(
        target=target.split('_')[0],b=band,n=len(ix[band][0])),fontsize=16)
    plt.xlabel('gAperture Magnitude',fontsize=14)
    plt.tick_params(axis='both', which='major', labelsize=12)
    plt.savefig('{path}/{target}_ABMag_dist.pdf'.format(path=outpath,
                target=target,b=band),format='pdf',dpi=1000,bbox_inches='tight')
plt.close()

# Overplot MCAT photometry of LDS749B on the reference magnitude and
# modeled 3-sigma error bounds as a function of exposure time.
for band in data.keys():
    tmin,tmax = 0,300#data[band]['t_eff'].min(),data[band]['t_eff'].max()
    plt.figure(figsize=(8*scl,4*scl))
    plt.subplots_adjust(left=0.12,right=0.95,wspace=0.1,bottom=0.15,top=0.9)
    plt.errorbar(np.array(data[band]['exptime']),
        np.array(data[band]['aper4'])-gt.apcorrect1(gt.aper2deg(4),band),fmt='.',color='k',alpha=0.1,
        yerr=[data[band]['mag_bgsub_err_1'],data[band]['mag_bgsub_err_2']])
    plt.plot(np.array(data[band]['exptime'])[ix[band]],
        np.array(data[band]['aper4'])[ix[band]]-
                 gt.apcorrect1(gt.aper2deg(4),band),'.',
        color='k',alpha=0.2)
    t = np.arange(tmin+1,tmax+1)
    plt.plot(t,refmag[band]*(t/t),'k')
    plt.plot(t,data_errors(refmag[band],band,t,sigma=3)[0],'r--')
    plt.plot(t,data_errors(refmag[band],band,t,sigma=3)[1],'r--')
    plt.xlim(tmin,tmax)
    plt.ylim(refmag[band]-0.5,refmag[band]+1)
    plt.gca().invert_yaxis()
    plt.title('{b}: MCAT Photometry of {target} (n={n})'.format(
            target=target.split('_')[0],b=band,n=len(ix[band][0])),fontsize=18)
    plt.xlabel('Effective Exposure Depth (s)',fontsize=16)
    plt.ylabel('gAperture Magnitude',fontsize=16)
    plt.tick_params(axis='both', which='major', labelsize=14)
    a,b = data_errors(refmag[band],
        band,np.array(data[band]['exptime'])[ix[band]],sigma=nsigma)
    cnt = len(np.where((np.array(data[band]['aper4'])[ix[band]]-
                                 gt.apcorrect1(gt.aper2deg(4),band)>=b) &
                       (np.array(data[band]['aper4'])[ix[band]]-
                                 gt.apcorrect1(gt.aper2deg(4),band)<=a))[0])
    print '{b}: {n} of {m} ({p}%) within {s} sigma'.format(
        b=band,n=cnt,m=len(ix[band][0]),p=100*cnt/len(ix[band][0]),s=nsigma)
    plt.text(150, 16.3 if band=='FUV' else 15.4, '{p}% within {s}{sym}'.format(
        p=100*cnt/len(ix[band][0]),s=nsigma,sym=r'$\sigma$'), fontsize=18)

    plt.savefig('{path}/{target}_ABMag_{b}_MCAT.pdf'.format(path=outpath,
                target=target,b=band),format='pdf',dpi=1000,bbox_inches='tight')
    plt.close()

# Generate distribution plots for MCAT photometry of LDS749B
bincnt = 50
fig = plt.figure(figsize=(10*scl,4*scl))
fig.subplots_adjust(left=0.12,right=0.95,wspace=0.1,bottom=0.15,top=0.9)
for i,band in enumerate(data.keys()):
    magrange = [refmag[band]-0.2,refmag[band]+0.6]
    tmin,tmax = 0,350
    plt.subplot(1,2,i+1,xticks=np.arange(round(magrange[0],1),
        round(magrange[1]+0.01,1),0.2),yticks=[])
    mags = np.array(data[band]['aper4'])-gt.apcorrect1(gt.aper2deg(4),band)
    plt.hist(mags[ix[band]],bins=bincnt,color='k',histtype='step',
        range=magrange, normed=1)
    plt.axvline(refmag[band], color='g', linestyle='solid', linewidth=4,
        label='Ref: {r} AB Mag'.format(r=round(refmag[band],2)))
    x,y,peak,bandwidth = make_kde(mags[ix[band]],magrange)
    print '{b}: peak={p} ({bw})'.format(b=band,p=peak,bw=bandwidth)
    plt.plot(x,y)
    plt.axvline(peak, color='k', linestyle='dotted', linewidth=2,
        label='KDE Peak: {p}'.format(p=round(peak,2)))
    plt.axvline(np.median(mags[ix[band]]), color='r', linestyle='dashed',
        linewidth=4,
        label='Median: {m}'.format(m=round(np.median(mags[ix[band]]),2)))
    plt.xlim(magrange)
    plt.gca().invert_xaxis()
    plt.title('{b}: MCAT Photometry of {target} (n={n})'.format(
        target=target.split('_')[0],b=band,n=len(ix[band][0])),fontsize=16)
    plt.xlabel('MCAT Magnitude',fontsize=14)
    plt.tick_params(axis='both', which='major', labelsize=12)
    plt.legend(loc=2,fontsize=14)
    plt.savefig('{path}/{target}_ABMag_dist_MCAT.pdf'.format(path=outpath,
                target=target,b=band),format='pdf',dpi=1000,bbox_inches='tight')
plt.close()
