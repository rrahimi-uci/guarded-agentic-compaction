import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
from scipy.stats import beta
def U(k,n,conf):
    if n==0 or k>=n: return 1.0
    if k==0: return 1-(1-conf)**(1/n)
    return float(beta.ppf(conf,k+1,n-k))
G=lambda m: 1-0.1/(m*11)
print('U(0,92) m=1 grid',U(0,92,G(1)))
print('U(0,91) m=1 grid',U(0,91,G(1)),'U(0,90)',U(0,90,G(1)),'U(0,89)',U(0,89,G(1)),'U(0,46)',U(0,46,G(1)),'U(0,26)',U(0,26,G(1)))
print('U(0,92) m=2 grid',U(0,92,G(2)))
print('U(0,92) m=5 grid',U(0,92,G(5)))
n=1
while U(0,n,G(2))>0.05: n+=1
print('n_min m=2',n)
n=1
while U(0,n,G(1))>0.05: n+=1
print('n_min m=1',n)
print('time-forward U(0,132) single 0.9',U(0,132,0.9),'grid',U(0,132,G(1)))
print('primary compiled-only 0/90 one-sided 95%',U(0,90,0.95))
for r,(k,n) in {'hf':(1,200),'pandas':(2,200),'streamlit':(0,160),'pytorch':(0,200)}.items(): print(r,U(k,n,G(1)))
print('pooled 760/3',U(3,760,G(1)),'all 3560/50',U(50,3560,G(1)))
# alpha at which m=2 is compiler-wide
print('m=2 alpha threshold', U(0,92,G(2)))
