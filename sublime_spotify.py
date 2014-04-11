import sublime, sublime_plugin
import threading
from urllib.request import urlopen
from urllib.parse import quote_plus
import json

import time

from SublimeSpotify.applescript_spotify_player import AppleScriptSpotifyPlayer as SpotifyPlayer
from SublimeSpotify.status_updater import MusicPlayerStatusUpdater

class SpotifyCommand(sublime_plugin.WindowCommand):
    def __init__(self, window):
        self.window = window
        self.player = SpotifyPlayer.Instance()
        if not self.player.status_updater:
            self.player.status_updater = MusicPlayerStatusUpdater(self.player)

class SpotifyPlayCommand(SpotifyCommand):
    def run(self):
        self.player.play()

class SpotifyPauseCommand(SpotifyCommand):
    def run(self):
        self.player.pause()

class SpotifyNextTrackCommand(SpotifyCommand):
    def run(self):
        self.player.next()

class SpotifyPreviousTrackCommand(SpotifyCommand):
    def run(self):
        self.player.previous()

class SpotifyToggleShuffleCommand(SpotifyCommand):
    def run(self):
        self.player.toggle_shuffle()

class SpotifyToggleRepeatCommand(SpotifyCommand):
    def run(self):
        self.player.toggle_repeat()

class SpotifyNowPlaying(SpotifyCommand):
    def run(self):
        self.player.show_status_message()

class SpotifySearchCommand(SpotifyCommand):
    def run(self):
        self.window.show_input_panel("Search Spotify", "", self.do_search, None, None)

    def do_search(self, search):
        search = quote_plus(search)

        url = "http://ws.spotify.com/search/1/track.json?q={search}".format(search=search)
        url_thread = ThreadedRequest(url, self)
        url_thread.setDaemon(True)
        url_thread.start()

    def handle_response(self, resp, error_message):
        if error_message is not None:
            sublime.error_message("Unable to search:\n%s" % error_message)
            return

        res = json.loads(resp.decode('utf-8'))
        if res["info"]["num_results"] == 0:
            self.window.show_input_panel("Search Spotify", "No results found, try again?", self.do_search, None, None)
        else:
            rows = []
            self.urls = []
            for track in res["tracks"]:
                song = track.get("name","")
                artists = ", ".join([a["name"] for a in track.get("artists", [])])
                album = track.get("album", {}).get("name", "")
                rows.append([u"{0} by {1}".format(song, artists), u"{0}".format(album)])
                self.urls.append(track.get("href", ""))
                if len(rows) > 30: break
            self.window.show_quick_panel(rows, self._play_track_at_index)

    def _play_track_at_index(self, index):
        self.player.play_track(self.urls[index])

class ThreadedRequest(threading.Thread):
    def __init__(self, url, caller):
      threading.Thread.__init__(self)
      self.url = url
      self.caller = caller

    def run(self):
        error = None
        try:
            resp = urlopen(self.url)
            content = resp.read()
        except e:
            content = ""
            error = e

        sublime.set_timeout(lambda: self.caller.handle_response(content, error), 10)

