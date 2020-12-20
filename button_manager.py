import RPi.GPIO as GPIO
import signal
from datetime import datetime
import time
import logging

def get_debounced_cb(onstart=None, onend=None):
    last_change = datetime.min

    def f(pin):
        now = datetime.now()
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
        now = datetime.now()
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

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

def add_buttons(buttons):
    for i, cb in buttons:
        GPIO.setup(i, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(i, GPIO.BOTH, cb)

def handle_exit(signum, frame):
    GPIO.cleanup()

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)