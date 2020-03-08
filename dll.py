import math
from math import sin
from math import pi
import fir_filter

rate = 315/88/108
filtered = []

def offset_and_normalize(x):
    return x/2 + 1/2

filter = fir_filter.FirFilterLowPassRect(64, 0.01)
phase_shift = 0
dir = 1
xrp, ap, bp = 0, 0, 0
t = 0

def lock(samples):
    global phase_shift, dir, xrp, ap, bp, t
    #print('DLL locking with %d samples' % (len(samples)))
    phase_shift = 0
    dir = 1
    xrp, ap, bp, t = 0, 0, 0, 0
    for i in range(len(samples)):
        incoming_signal = samples[i]
        ref_osscilator  = math.cos(2*math.pi*t*rate+phase_shift)

        # Phase comparator
        a, b = [round(offset_and_normalize(x)) for x in (incoming_signal, ref_osscilator)]
        xr = a ^ b

        # If the xor detector fired,
        if xr == 1 and xrp == 0:
            # determine which signal caused the change. This indicates which is leading or lagging in phase.
            if ap != a:
                dir = -1
            else:
                dir = 1

        phase_offset = filter.filter(xr)

        # Adjust phase of reference osscilator based on phase offset_and_normalize
        phase_shift -= phase_offset * 0.05 * dir

        #print('samp: %f xor: %f dir: %f phase_offset: %f phase_shift: %f' % (incoming_signal, xr, dir, phase_offset, phase_shift))
        xrp, ap, bp = xr, a, b
        t += 1

def tick():
    global t
    deg33 = 11*pi/60
    v1 = math.cos(2*math.pi*t*rate+phase_shift-deg33+pi)
    v2 = -1 * math.sin(2*math.pi*t*rate+phase_shift-deg33+pi)
    t += 1
    return v1, v2
