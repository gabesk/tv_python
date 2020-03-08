import struct
from PIL import Image
# Input single is 16 bits (10 bits of signal) at 13.5 MHz, since that's what
# https://en.wikipedia.org/wiki/Rec._601 says is standard.
# Upsample 8x to make it easier to decode colorburst, which gives a new
# frequency of 108 Mhz.
# Wikipedia says https://en.wikipedia.org/wiki/Upsampling to do that,
# Create a sequence, {\displaystyle \scriptstyle x_{L}[n],} \scriptstyle x_{L}[n], comprising the original samples, {\displaystyle \scriptstyle x[n],} \scriptstyle x[n], separated by L − 1 zeros. This alone is sometimes referred to as upsampling.
# That means, for every sample, insert 7 more 0'sample
print('Reading input.')
with open('raw.raw', 'rb') as f:
    b = f.read()
print('Done.')


print('Packing.')
packed_bytes = struct.pack('<%dH' % len(b), *b)
print('Done.')

print('Writing.')
with open('upsampled.raw', 'wb') as fout:
    fout.write(packed_bytes)
print('Done.')

new = []
print('Upsampling.')
for i in range(len(b)//2):
    pair = b[i*2:i*2+2]
    value = struct.unpack('<H', pair)[0]
    new.append(value)
    for j in range(7):
        new.append(0)
print('Done.')

# Then,
# Interpolation: Smooth out the discontinuities with a lowpass filter, which replaces the zeros.
# With http://t-filter.engineerjs.com/,
# Make a filter that stops everything < 6 MHz
# Making the stop band start at 8 MHz gives a filter with 61 taps. This will be slow.
filter_taps = [
  -0.004883951371494766,
  0.00047711859401443146,
  0.0018848850019747613,
  0.004198417700537643,
  0.007296925331924457,
  0.010937375910235502,
  0.014751169736903321,
  0.01826833485940584,
  0.020961666850240396,
  0.02230659915625455,
  0.021857132876340068,
  0.01933468218069784,
  0.014711287861297478,
  0.008198467467677453,
  0.00034429456398476685,
  -0.008051428630637302,
  -0.015974654253240246,
  -0.022301336282313462,
  -0.025921249410251458,
  -0.025877277613806784,
  -0.021498908482659482,
  -0.012510165659366681,
  0.0009025528811847956,
  0.018068013407253235,
  0.03786125697346522,
  0.0588118565991858,
  0.07922783521233905,
  0.0973725902650215,
  0.11164995697754293,
  0.12077473407942968,
  0.12391267698484011,
  0.12077473407942968,
  0.11164995697754293,
  0.0973725902650215,
  0.07922783521233905,
  0.0588118565991858,
  0.03786125697346522,
  0.018068013407253235,
  0.0009025528811847956,
  -0.012510165659366681,
  -0.021498908482659482,
  -0.025877277613806784,
  -0.025921249410251458,
  -0.022301336282313462,
  -0.015974654253240246,
  -0.008051428630637302,
  0.00034429456398476685,
  0.008198467467677453,
  0.014711287861297478,
  0.01933468218069784,
  0.021857132876340068,
  0.02230659915625455,
  0.020961666850240396,
  0.01826833485940584,
  0.014751169736903321,
  0.010937375910235502,
  0.007296925331924457,
  0.004198417700537643,
  0.0018848850019747613,
  0.00047711859401443146,
  -0.004883951371494766
    ]
print(len(filter_taps))

#/*
#
#FIR filter designed with
# http://t-filter.appspot.com
#
#sampling frequency: 108000000 Hz
#
#* 0 Hz - 6000000 Hz
#  gain = 1
#  desired ripple = 5 dB
#  actual ripple = 4.073222846575726 dB
#
#* 8000000 Hz - 54000000 Hz
#  gain = 0
#  desired attenuation = -40 dB
#  actual attenuation = -40.20843600802444 dB
#
#*/

SAMPLEFILTER_TAP_NUM = 61

history = [0] * SAMPLEFILTER_TAP_NUM
last_index = 0

def SampleFilter_init():
    for i in range(SAMPLEFILTER_TAP_NUM):
        history[i] = 0;
    last_index = 0

def SampleFilter_put(input):
    global last_index
    history[last_index] = input
    last_index += 1
    if last_index == SAMPLEFILTER_TAP_NUM:
        last_index = 0

def SampleFilter_get():
    acc = 0
    index = last_index
    for i in range(SAMPLEFILTER_TAP_NUM):
        if index != 0:
            index = index - 1
        else:
            index = SAMPLEFILTER_TAP_NUM-1
        acc += history[index] * filter_taps[i]

    return max(0,min(int(acc), 65535))

interpolated = []
print('Interpolate.')
SampleFilter_init()
for samp in new:
    SampleFilter_put(samp)
    interpolated.append(SampleFilter_get() * 8)
print('Done.')

print('Packing.')
packed_bytes = struct.pack('<%dH' % len(interpolated), *interpolated)
print('Done.')

print('Writing.')
with open('upsampled.raw', 'wb') as fout:
    fout.write(packed_bytes)
print('Done.')














