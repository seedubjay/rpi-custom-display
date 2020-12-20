from datetime import datetime, timedelta
from multiprocessing import Process, Value
import os

BLACKLIST_FILE = '/home/pi/blacklist_end'

end_time = datetime(1970,1,1)
with open(BLACKLIST_FILE, 'w') as f:
    f.write(f"{int(end_time.timestamp())}")
os.chmod(BLACKLIST_FILE, 0o644)

def add_time(minutes):
    global end_time
    end_time = max(datetime.now(), end_time) + timedelta(minutes=minutes)
    with open(BLACKLIST_FILE, 'w') as f:
        f.write(f"{int(end_time.timestamp())}")
