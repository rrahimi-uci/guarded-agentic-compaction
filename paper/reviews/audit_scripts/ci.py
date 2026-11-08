import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
from scipy.stats import beta
def cp(k,n,a=0.025):
    lo=0 if k==0 else beta.ppf(a,k,n-k+1); hi=1 if k==n else beta.ppf(1-a,k+1,n-k); return lo,hi
n=630;g=17;l=18
gl,gh=cp(g,n); ll,lh=cp(l,n)
print('train interval pp', round(100*(gl-lh),2), round(100*(gh-ll),2))
gl,gh=cp(g,n,0.0125); ll,lh=cp(l,n,0.0125)
print('train interval pp (97.5% two-sided each)', round(100*(gl-lh),2), round(100*(gh-ll),2))
