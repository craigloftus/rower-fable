"""June's garment pattern in the approved model's X/Y/Z coordinates."""
import numpy as np

def hem(p):
    return .066+.013*(np.abs(p[:,0])/.075)**1.7

def singlet(p):
    x,y,z=p.T
    front=np.clip((z+.050)/.025,0,1)
    front=front*front*(3-2*front)
    collar_front=.261+.048*(np.abs(x)/.052)**2
    collar_back=.291+.025*(np.abs(x)/.053)**2
    collar=collar_back*(1-front)+collar_front*front
    width=.074-.012*np.exp(-((y-.251)/.039)**2)+.042*np.clip((.14-y)/.075,0,1)
    return np.maximum.reduce([np.abs(x)-width,y-collar,hem(p)-y,y-.311])

def shorts(p):
    x,y,z=p.T
    bottom=-.069-.005*np.clip(np.abs(x)/.105,0,1)
    # The relaxed forearms pass beside the waist in the source A-pose.
    # Keep them out of the shorts mask before the seated garment is fitted.
    return np.maximum.reduce([y-hem(p),bottom-y,np.abs(x)-.118,y-.084])
