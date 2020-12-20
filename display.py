import sys
from dotenv import load_dotenv
load_dotenv(dotenv_path= sys.path[0] + '/spotipy.env')

import time
import math
import os
from datetime import datetime, timedelta
import requests
import logging
import socket
import uuid
from demo_opts import get_device
from luma.core.render import canvas
from PIL import ImageFont

from lifx import get_color_change, alternate_power
from spotify import *
import blacklist
from button_manager import add_buttons, get_click_cb

# logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)-15s - %(message)s'
)
# ignore PIL debug messages
logging.getLogger('PIL').setLevel(logging.ERROR)

socket.setdefaulttimeout(3)

margin=4

def getFont(size):
    return ImageFont.truetype(os.path.join(sys.path[0], "courier-prime-sans.ttf"), size=size)

FONT_ASPECT_RATIO = .6

active_page = None
time_until_clock = 0

spotify_mode = False

def get_click_cb_by_song(light_cb, song_cb):
    global spotify_mode
    def f(pin):
        if spotify_mode: song_cb(pin)
        else: light_cb(pin)
    return f

def show_spotify():
    global spotify_mode
    global active_page
    global time_until_clock

    if active_page == "technical_info":
        active_page = None
        time_until_clock = 0
        return

    spotify_mode = not spotify_mode
    if spotify_mode:
        song = get_spotify_song(True)
        if song is None: spotify_mode = False
    logging.info(f"show song: {spotify_mode}")

def show_rowing():
    global active_page
    global time_until_clock

    if active_page == "blacklist":
        return

    if active_page == "technical_info":
        active_page = None
        time_until_clock = 0
        return

    flag_page = requests.get("http://m.cucbc.org").text
    f = flag_page.split("\n")
    flag_colour = f[3][25:-14]

    light_page = requests.get("http://m.cucbc.org/lighting").text
    l = light_page.split("\n")
    today_date = datetime.strptime(l[2][-14:-4], "%Y-%m-%d").date()
    today_down = datetime.strptime(l[4][26:31], "%H:%M").time()
    today_up = datetime.strptime(l[5][24:29], "%H:%M").time()
    tmr_down = datetime.strptime(l[7][26:31], "%H:%M").time()
    tmr_up = datetime.strptime(l[8][24:29], "%H:%M").time()

    g = [(today_date, today_down, today_up), (today_date + timedelta(days=1), tmr_down, tmr_up)]

    active_page = "flag"
    time_until_clock = 5
    with canvas(device) as draw:
        draw.text((margin, margin + 2), flag_colour, fill="white", font=getFont(20))
        for i in range(2):
            draw.text((margin, margin + 25 + 16*i), g[i][0].strftime("%d/%m"), fill="white", font=getFont(12))
            draw.text((margin + 42, margin + 25 + 16*i), g[i][1].strftime("%H:%M"), fill="white", font=getFont(12))
            draw.text((margin + 84, margin + 25 + 16*i), g[i][2].strftime("%H:%M"), fill="white", font=getFont(12))

def show_technical_info():
    global active_page
    global time_until_clock

    if active_page == 'blacklist': return

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("bbc.co.uk", 80))
    ip = s.getsockname()[0]

    mac = ":".join(["{:02x}".format((uuid.getnode() >> i) & 0xff) for i in range(0,48,8)][::-1])

    active_page = "technical_info"
    time_until_clock = 15

    with canvas(device) as draw:
        draw.text((margin,margin), ip, fill="white", font=getFont(14))
        draw.text((margin,margin + 14), mac, fill="white", font=getFont(12))

timer_total = timedelta()
timer_last_start = None

def start_timer():
    global time_until_clock
    global active_page
    global timer_total
    global timer_last_start

    if active_page == "blacklist": return

    if active_page != "timer":
        active_page = "timer"
        time_until_clock = 0
        timer_total = timedelta()
        timer_last_start = None
            
    if timer_last_start is None:
        timer_last_start = datetime.now()
    else:
        timer_total += datetime.now() - timer_last_start
        timer_last_start = None

def stop_timer():
    global active_page
    if active_page == "timer": active_page = None

def add_time_to_blacklist():
    global active_page

    # if active_page != "blacklist":
    #     os.system(f"pihole --wild $(cat {os.path.join(sys.path[0], 'blacklist.txt')})")
    #     os.system("systemctl stop lighttpd")
    
    active_page = "blacklist"
    blacklist.add_time(10)

def safe_playpause():
    if not playpause_song(): spotify_mode = False

add_buttons([
    (13, get_click_cb_by_song(
        get_click_cb(alternate_power),
        get_click_cb(safe_playpause)
    )),
    (19, get_click_cb(get_color_change(.1,brightness=-.1), get_color_change(.3,brightness=-1))),
    (6, get_click_cb(get_color_change(.1,brightness=.1), get_color_change(.3,brightness=1))),
    (5, get_click_cb_by_song(
        get_click_cb(get_color_change(.1,temp=-500)),
        get_click_cb(previous_song)
    )),
    (26, get_click_cb_by_song(
        get_click_cb(get_color_change(.1,temp=500)),
        get_click_cb(next_song)
    )),
    (16, get_click_cb(show_spotify, show_technical_info, 3)),
    (20, get_click_cb(start_timer, stop_timer)),
    (21, get_click_cb(add_time_to_blacklist))
])

DATE_SCROLL_START_HANG = 5
DATE_SCROLL_END_HANG = 2
DATE_SCROLL_SECONDS_PER_CHAR = 1
DATE_SCROLL_MAX_LENGTH = 13

if __name__ == "__main__":
    device = get_device()

    today_last_time = None
    today_last_date = None

    date_update_time = None

    while True:
        today_time = None
        today_date = None
        now = datetime.now()
        if active_page == "timer":
            elapsed = timer_total + (now - timer_last_start if timer_last_start is not None else timedelta())
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
        elif active_page == "blacklist":
            remaining = blacklist.end_time - datetime.now()
            if remaining < timedelta():
                active_page = None
            else:
                hours, rem = divmod(remaining.total_seconds()+60, 3600)
                hours = int(hours)
                minutes, rem = divmod(rem, 60)
                minutes = int(minutes)
                today_time = f'{hours:02}:{minutes:02}'
                today_date = 'STFU AND WORK'

        if active_page == None:
            song = get_spotify_song()
            if song is None: spotify_mode = False
            if spotify_mode: today_date = song['item']['name']
            else: today_date = now.strftime("%d %b %Y")
            today_time = now.strftime("%H:%M") if now.microsecond < 500000 else now.strftime("%H %M")


        if True or (today_time != today_last_time or today_date != today_last_date) and time_until_clock < .0001:
            if active_page not in ["timer", "blacklist"]: active_page = None
            today_last_time = today_time
            if today_date != today_last_date:
                date_update_time = datetime.now()
            today_last_date = today_date
            with canvas(device) as draw:
                cy = min(device.height, 64) / 2

                draw.text((margin, 12), today_time, fill="white", font=getFont(33))

                if len(today_date) <= 13:
                    draw.text((margin, 42), today_date, fill="white", font=getFont(15))
                else:
                    overhang = len(today_date) - DATE_SCROLL_MAX_LENGTH
                    cycle = (datetime.now() - date_update_time).total_seconds()
                    cycle %= DATE_SCROLL_START_HANG + DATE_SCROLL_END_HANG + DATE_SCROLL_SECONDS_PER_CHAR * overhang
                    cycle -= DATE_SCROLL_START_HANG
                    draw.text((margin - min(max(cycle,0),DATE_SCROLL_SECONDS_PER_CHAR*overhang)*FONT_ASPECT_RATIO*15, 42), today_date, fill="white", font=getFont(15))

        time.sleep(max((now + timedelta(seconds=.1) - datetime.now()).total_seconds(), 0))
        time_until_clock = max(time_until_clock - .1, 0)
