import RPi.GPIO as GPIO
import time
import lifxlan
import math
import sys
import os
import datetime
import requests
import logging
import socket
import uuid
from demo_opts import get_device
from luma.core.render import canvas
from PIL import ImageFont

import signal


# logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s - %(message)s'
)
# ignore PIL debug messages
logging.getLogger('PIL').setLevel(logging.ERROR)

socket.setdefaulttimeout(3)

margin=4

light = lifxlan.Light("D0:73:D5:58:62:32", "192.168.2.239")

def getFont(size):
    return ImageFont.truetype(os.path.join(sys.path[0], "courier-prime-sans.ttf"), size=size)

def get_debounced_cb(onstart=None, onend=None):
    last_change = datetime.datetime.min

    def f(pin):
        now = datetime.datetime.now()
        nonlocal last_change
        last_change = now
        time.sleep(.01)
        if last_change == now:
            if GPIO.input(pin) == 0:
                if onstart is not None: onstart()
            else:
                if onend is not None: onend()
    return f

def get_click_cb(onclick=None, onlong=None, hold_time=.5):
    last_start = None

    def start():
        nonlocal last_start
        logging.debug("click start")
        now = datetime.datetime.now()
        last_start = now
        time.sleep(hold_time)
        if last_start == now:
            if onlong is not None:
                logging.debug("long press")
                last_start = None
                onlong()

    def end():
        nonlocal last_start
        logging.debug("click end")
        if last_start is not None:
            last_start = None
            if onclick is not None:
                logging.debug("short press")
                onclick()
    
    return get_debounced_cb(start, end)

active_page = None
time_until_clock = 0

def show_rowing():
    global active_page
    global time_until_clock

    if active_page == "technical_info":
        active_page = None
        time_until_clock = 0
        return

    flag_page = requests.get("http://m.cucbc.org").text
    f = flag_page.split("\n")
    flag_colour = f[3][25:-14]

    light_page = requests.get("http://m.cucbc.org/lighting").text
    l = light_page.split("\n")
    today_date = datetime.datetime.strptime(l[2][-14:-4], "%Y-%m-%d").date()
    today_down = datetime.datetime.strptime(l[4][26:31], "%H:%M").time()
    today_up = datetime.datetime.strptime(l[5][24:29], "%H:%M").time()
    tmr_down = datetime.datetime.strptime(l[7][26:31], "%H:%M").time()
    tmr_up = datetime.datetime.strptime(l[8][24:29], "%H:%M").time()

    g = [(today_date, today_down, today_up), (today_date + datetime.timedelta(days=1), tmr_down, tmr_up)]

    active_page = "flag"
    time_until_clock = 5
    with canvas(device) as draw:
        draw.text((margin, margin + 2), flag_colour, fill="white", font=getFont(20))
        for i in range(2):
            draw.text((margin, margin + 25 + 16*i), g[i][0].strftime("%d/%m"), fill="white", font=getFont(12))
            draw.text((margin + 42, margin + 25 + 16*i), g[i][1].strftime("%H:%M"), fill="white", font=getFont(12))
            draw.text((margin + 84, margin + 25 + 16*i), g[i][2].strftime("%H:%M"), fill="white", font=getFont(12))

last_internet_check = datetime.datetime.min
connected_to_internet_cache = False
def connected_to_internet():
    global last_internet_check
    global connected_to_internet_cache

    if datetime.datetime.now() - last_internet_check > datetime.timedelta(seconds=10):
        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8",53))
            connected_to_internet_cache = True
        except socket.error as ex:
            logging.debug(ex)
            connected_to_internet_cache = False
        last_internet_check = datetime.datetime.now()
    return connected_to_internet_cache

def show_technical_info():
    global active_page
    global time_until_clock

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]

    mac = ":".join(["{:02x}".format((uuid.getnode() >> i) & 0xff) for i in range(0,48,8)][::-1])

    active_page = "technical_info"
    time_until_clock = 15

    with canvas(device) as draw:
        draw.text((margin,margin), ip, fill="white", font=getFont(14))
        draw.text((margin,margin + 14), mac, fill="white", font=getFont(12))

timer_total = datetime.timedelta()
timer_last_start = None

def start_timer():
    global time_until_clock
    global active_page
    global timer_total
    global timer_last_start
    if active_page != "timer":
        active_page = "timer"
        time_until_clock = 0
        timer_total = datetime.timedelta()
        timer_last_start = None
            
    if timer_last_start is None:
        timer_last_start = datetime.datetime.now()
    else:
        timer_total += datetime.datetime.now() - timer_last_start
        timer_last_start = None

def stop_timer():
    global active_page
    active_page = None

def get_color_change(duration, brightness=0, temp=0):
    def f():
        color = [*light.get_color()]
        color[2] = min(max(color[2]+int(brightness*65536),0),65535)
        color[3] = min(max(color[3]+temp,2500),9000)
        if color[2] > 0 and light.get_power() == 0: light.set_power("on")
        light.set_color(color, duration, True)
    return f

buttons = [
    (13, get_click_cb(lambda: light.set_power(65535-light.get_power(), .5))),
    (19, get_click_cb(get_color_change(.1,brightness=.1), get_color_change(.3,brightness=1))),
    (6, get_click_cb(get_color_change(.1,brightness=-.1), get_color_change(.3,brightness=-1))),
    (5, get_click_cb(get_color_change(.1,temp=500))),
    (26, get_click_cb(get_color_change(.1,temp=-500))),
    (16, get_click_cb(show_rowing, show_technical_info, 3)),
    (20, get_click_cb(start_timer, stop_timer)),
    (21, get_click_cb(onlong=lambda: os.system("shutdown -h now"), hold_time=8))
]

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for i, cb in buttons:
    GPIO.setup(i, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(i, GPIO.BOTH, cb)

def main():
    global time_until_clock
    global active_page
    global timer_total
    global timer_last_start

    today_last_time = None
    today_last_date = None

    while True:
        now = datetime.datetime.now()
        if active_page == "timer":
            elapsed = timer_total + (now - timer_last_start if timer_last_start is not None else datetime.timedelta())
            hours, rem = divmod(elapsed.total_seconds(), 3600)
            hours = int(hours)
            minutes, rem = divmod(rem, 60)
            minutes = int(minutes)
            seconds, tenths = divmod(rem, 1)
            seconds = int(seconds)
            tenths = int(tenths*10)
            if hours > 0:
                today_time = f'{hours:02}:{minutes:02}'
                today_date = f'         {seconds:02}'
            else:
                today_time = f'{minutes:02}:{seconds:02}'
                today_date = ''
        else:
            today_date = now.strftime("%d %b %Y")
            today_time = now.strftime("%H:%M") if now.microsecond < 500000 else now.strftime("%H %M")
        if (today_time != today_last_time or today_date != today_last_date) and time_until_clock < .0001:
            if active_page != "timer": active_page = None
            today_last_time = today_time
            today_last_date = today_date
            with canvas(device) as draw:
                cy = min(device.height, 64) / 2

                draw.text((margin, 12), today_time, fill="white", font=getFont(33))
                draw.text((margin, 42), today_date, fill="white", font=getFont(15))

                if not connected_to_internet():
                    draw.ellipse((device.width-4-margin,margin,device.width-margin,margin+4), fill="white")

        time.sleep(0.1)
        time_until_clock = max(time_until_clock - .1, 0)

def handle_exit(signum, frame):
    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

if __name__ == "__main__":
    device = get_device()
    main()
