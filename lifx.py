import lifxlan
from datetime import datetime, timedelta
import time

light = lifxlan.Light("D0:73:D5:58:62:32", "192.168.2.239")

color_cache = [0,0,0,0]
color_cache_time = datetime(1970,1,1)

def get_color_change(duration, brightness=0, temp=0):
    def f():
        global color_cache
        global color_cache_time
        if datetime.now() - color_cache_time > timedelta(minutes=1):
            color_cache = [*light.get_color()]
        color_cache_time = datetime.now()

        color_cache[2] = min(max(color_cache[2]+int(brightness*65536),0),65535)
        color_cache[3] = min(max(color_cache[3]+temp,1500),9000)
        if color_cache[2] > 0: light.set_power("on", True)
        light.set_color(color_cache, 1000*duration, True)
        if color_cache[2] == 0:
            time.sleep(duration+.1)
            light.set_power("off", True)
    return f

def alternate_power():
    light.set_power(65535-light.get_power(), 500)