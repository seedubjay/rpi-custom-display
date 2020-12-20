import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timedelta

cache_path = os.getenv('SPOTIPY_CACHE_PATH')

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='user-modify-playback-state user-read-playback-position user-read-currently-playing user-read-playback-state', show_dialog=True, open_browser=False, cache_path=cache_path))

last_spotify_check = datetime.min
spotify_check_cache = None

def get_spotify_device():
    global last_spotify_check
    global spotify_check_cache

    if datetime.now() - last_spotify_check > timedelta(seconds=15):
        last_spotify_check = datetime.now()
        ids = [d['id'] for d in sp.devices()['devices'] if d['is_active']]
        spotify_check_cache = ids[0] if len(ids) > 0 else None

    return spotify_check_cache

last_song_check = datetime.min
song_check_cache = None

def get_spotify_song(force=False):
    global last_song_check
    global song_check_cache

    if force or datetime.now() - last_song_check > timedelta(seconds=5):
        last_song_check = datetime.now()
        song_check_cache = sp.current_user_playing_track()

    return song_check_cache

def playpause_song():
    song = get_spotify_song(True)
    if song is None: return

    try:
        if song['is_playing']: sp.pause_playback()
        else: sp.start_playback()
        return True
    except:
        return False

def next_song():
    try:
        sp.next_track()
        time.sleep(.1)
        get_spotify_song(True)
        time.sleep(.5)
        get_spotify_song(True)
    except:
        pass

def previous_song():
    try:
        sp.previous_track()
        time.sleep(.1)
        get_spotify_song(True)
        time.sleep(.5)
        get_spotify_song(True)
    except:
        pass