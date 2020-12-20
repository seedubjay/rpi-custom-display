import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

cache_path = os.environ['SPOTIPY_CACHE_PATH']

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='user-modify-playback-state user-read-playback-position user-read-currently-playing user-read-playback-state', show_dialog=True, open_browser=False, cache_path=cache_path))

