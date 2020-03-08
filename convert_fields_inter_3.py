import struct
from PIL import Image
import fir_filter
import dll
from math import sin, cos, pi


rate = 315/88/108

sync_start = 0
sync_start_prev = 0
sync_cnt = 0
backport_cnt = 0
colorburst_cnt = 0
backport_post_cnt = 0
line_cnt = 0

in_sync = False
in_backporch = False
in_colorburst = False
in_backport_post = False
in_line = False
in_field = False

line_has_color = False

fields = []
lines = []
line = []

colorburst = []
cos_filter = fir_filter.FirFilterLowPassRect(64, 0.044/8)
sin_filter = fir_filter.FirFilterLowPassRect(64, 0.044/8)
y_filter = fir_filter.FirFilterLowPassRect(64, 0.143/8)

# Line sync is 63, so +- 10%
#LINE_SYNC_MIN = 57
LINE_SYNC_MIN = 50 * 8
LINE_SYNC_MAX = 69 * 8

#FIELD_SYNC_LEN = 362
FIELD_SYNC_MIN = 350 * 8
FIELD_SYNC_MAX = 370 * 8

FIELD_CNT_MIN = 253
FIELD_CNT_MAX = 254

line_value = []
prev_line_value = []

PRE_START_ACTIVE_VIDEO_LINES = 11

FRAME_HEIGHT = (FIELD_CNT_MAX - PRE_START_ACTIVE_VIDEO_LINES) * 2

line_max_val = 0
line_min_val = 1000000

print('Processing input.')
with open('upsampled.raw', 'rb') as f:
    b = f.read()
j = 0
for i in range(len(b)):
    pair = b[i*2:i*2+2]
    value = struct.unpack('<H', pair)[0]
    if in_backporch == False and in_line == False:
        if value < 250:
            # We're in a sync of some sort. Measure how long the sync lasts.
            if sync_cnt == 0:
                sync_start_prev = sync_start
                sync_start = i
            sync_cnt += 1
        else:
            if sync_cnt != 0:
                # Done with the sync. How long did it last:
                #print('Sync length %d. Since last sync:%d' % (sync_cnt, sync_start - sync_start_prev))
                if sync_cnt >= LINE_SYNC_MIN and sync_cnt <= LINE_SYNC_MAX:
                    #print('Line sync. Lines so far: %d' % (len(lines)))
                    in_backporch = True
                    in_field = False

                elif sync_cnt >= FIELD_SYNC_MIN and sync_cnt <= FIELD_SYNC_MAX:
                    #print('Field sync')
                    if not in_field:
                        #print('New field. Existing field len %d' % (len(lines)))
                        if len(lines) < FIELD_CNT_MIN or len(lines) > FIELD_CNT_MAX:
                            pass
                            #print('Invalid previous field. Skipping')
                        else:
                            fields.append(lines[PRE_START_ACTIVE_VIDEO_LINES:])
                            if len(fields) == 2:
                                break
                        lines = []
                    in_field = True

                sync_cnt = 0


    if in_backporch:
        backport_cnt += 1

    if backport_cnt > 65:
        backport_cnt = 0
        in_backporch = False
        in_colorburst = True
        colorburst = []

    if in_colorburst:
        colorburst.append(value)
        colorburst_cnt += 1

    if colorburst_cnt > 270:
        colorburst_cnt = 0
        in_colorburst = False
        in_backport_post = True
        # Does it look like this was a colorburst? Ideally would run through a
        # filter or detector or something but for now just check if there was
        # significant variation in the min and max excursion of the signal.
        def figure_out_things():
            global line_has_color
            mi, ma = 1000000, 0
            a = 0
            for v in colorburst:
                a += v
                if v < mi: mi = v
                if v > ma: ma = v
            a /= len(colorburst)
            s = ma - mi
            if s < 100:
                # Probably not a colorburst.
                return
            else:
                line_has_color = True
                # Normalize and offset so the delay locked loop can sync with it.
                burst_offset = []
                for v in colorburst:
                    burst_offset.append((v-a)/s*2)
                # Calibrate the delay locked loop.
                #print(burst_offset)
                dll.lock(burst_offset)
        #print('Colorburst over at i %d' % (i))
        figure_out_things()

    # It's important from this point on that the DLL osscilator tick one for
    # each sample so that it remains in lock with the colorburst signal, even if
    # we're not decoding color at the moment.
    if in_backport_post:
        dll.tick()
        backport_post_cnt += 1

    if backport_post_cnt > 151:
        backport_post_cnt = 0
        in_backport_post = False
        in_line = True
        line_max_val = 0
        line_min_val = 1000000
        print(len(lines))

    if in_line:
        cos_osc, sin_osc = dll.tick()
        
        if value > line_min_val: line_min_val = value
        if value < line_max_val: line_max_val = value
        
        offset_px = max(value - 530, 0)
        scaled_px = min(int(offset_px / 6.046875), 255)
        scaled_px /= 255
        line_value.append(scaled_px)

        deg33 = 11*pi/60

        if len(prev_line_value) > line_cnt:
            averaged_px = ( -1 * prev_line_value[line_cnt] + scaled_px ) / 2
        else:
            averaged_px = scaled_px

        u_mult = cos_osc * averaged_px
        v_mult = sin_osc * averaged_px

        # Filter the u and v to 600 kHz since that's what the limit of vision
        # bandwidth is and to remove the demodulation sidebands.
        # Filter the y to 4.2 since that's the NTSC vision bandwidth limit.
        # (Note that we're assuming we're sampling at 13.5 MHz which means that
        #  the original picture has a bandwidth of 6.75 Mhz)
        uu = cos_filter.filter(u_mult) * 2
        vv = sin_filter.filter(v_mult) * 2
        yy = y_filter.filter(scaled_px)

        # Given y and scaled u and v, turn back into RGB.
        rr  = vv/0.877 + yy
        bb  = uu/0.493 + yy
        gg = -0.509*(rr-yy) - 0.194*(bb-yy) + yy
        line.append((int(rr*255),int(gg*255),int(bb*255)))
        line_cnt += 1

    #if line_cnt > 714 * 8:
    if line_cnt > 714 * 8:
        line_cnt = 0
        in_line = False
        lines.append(line)
        prev_line_value = line_value
        line_value = []
        print('Line min %d max %d' % (line_min_val, line_max_val))
        #print('Line %d min %d max %d' % (len(lines), min(line), max(line)))
        line = []
        #print('Reading line %d' % (len(lines)))

print('Done')
print('Creating image.')
im = Image.new('RGB', (715, FRAME_HEIGHT))
for f in range(2):
    for y, line in enumerate(fields[f]):
        #for x, px in enumerate(line):
        for x in range(len(line)//8):
            px = line[x*8]
            im.putpixel((x,y*2+f), px)
im.save('image.png')
print('Done')