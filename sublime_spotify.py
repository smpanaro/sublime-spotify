import sublime, sublime_plugin
import sys
import threading
import time
import urllib2
from urllib import quote_plus
import json

# Wrap player interactions to compensate for different naming styles and platforms.
class SpotifyPlayer():
    def __init__(self):
        if sys.platform == "win32":
            # import win32com.client
            # c = win32com.client.gencache.EnsureDispatch("iTunes.Application")
            raise NotImplementedError("Sorry, there's no Windows support yet.")
        elif sys.platform == "darwin": # OS X
            from ScriptingBridge import SBApplication
            # Get a reference to the client without launching it. 
            # Spotify will launch automatically when called.
            self.client = SBApplication.alloc().initWithBundleIdentifier_("com.spotify.client")
        else:
            raise NotImplementedError("Sorry, your platform is not supported yet.")
        self.status_updater = None

    def is_running(self):
        return self.client.isRunning()

    def show_status_message(self):
        self.status_updater.run()

    # Player State - determined from the following enum values
    # SpotifyEPlSStopped = 'kPSS',
    # SpotifyEPlSPlaying = 'kPSP',
    # SpotifyEPlSPaused = 'kPSp'
    def _get_state(self):
        return self.client.properties()['playerState'].description()[-6:-2]

    def is_playing(self):
        return self._get_state() == "kPSP"

    def is_stopped(self):
        return self._get_state() == "kPSS"

    def is_paused(self):
        return self._get_state() == "kPSp"

    # Current Track information
    def get_artist(self):
        return self.client.currentTrack().artist()

    def get_album(self):
        return self.client.currentTrack().album()

    def get_song(self):
        return self.client.currentTrack().name()

    def get_position(self):
        return self.client.playerPosition()

    def get_duration(self):
        return self.client.currentTrack().duration()

    # Actions
    def play_pause(self):
        self.client.playpause()

    def play_track(self, track_url, attempts=0):
        if not self.is_running() or not self.is_playing():
            if attempts > 10: return
            sublime.set_timeout(lambda: self.play_track(track_url, attempts+1), 200)
        self.client.playTrack_inContext_(track_url,"Spotify")
        self.show_status_message()

    def play(self, attempts=0):
        if not self.is_running() or not self.is_playing():
            if attempts > 10: return
            sublime.set_timeout(lambda: self.play(attempts+1), 200)
        self.client.play()
        self.show_status_message()

    def pause(self):
        self.client.pause()

    def next(self):
        self.client.nextTrack()
        self.show_status_message()

    def previous(self):
        # Call it twice - once to get back to the beginning 
        # of this song and once to go back to the next.
        self.client.previousTrack()
        self.client.previousTrack()
        self.show_status_message()

    def toggle_shuffle(self):
        if self.client.shufflingEnabled():
            if self.client.shuffling():
                self.client.setShuffling_(False)
            else: 
                self.client.setShuffling_(True)

    def toggle_repeat(self):
        if self.client.repeatingEnabled():
            if self.client.repeating():
                self.client.setRepeating_(False)
            else: 
                self.client.setRepeating_(True)

class SpotifyCommand(sublime_plugin.WindowCommand):
    def __init__(self, window):
        self.window = window
        self.player = PLAYER

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

        res = json.loads(resp)
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
            self.window.show_quick_panel(rows, self.play_track_at_index)

    def play_track_at_index(self, index):
        self.player.play_track(self.urls[index])

class ThreadedRequest(threading.Thread):
    def __init__(self, url, caller):
      threading.Thread.__init__(self)
      self.url = url
      self.caller = caller

    def run(self):
        error = None
        try:
            resp = urllib2.urlopen(self.url)
            content = resp.read()
        except e:
            content = ""
            error = e

        sublime.set_timeout(lambda: self.caller.handle_response(content, error), 10)

class SpotifyStatusUpdater():
    def __init__(self, player):
        self.player = player

        s = sublime.load_settings("Spotify.sublime-settings")
        self.display_duration = int(s.get("status_duration"))
        self.status_format = s.get("status_format")

        self._cached_song = None
        self._cached_artist = None
        self._cached_album = None
        self._cached_duration = None

        self._update_delay = 100 # Udpate every n milliseconds.
        self._cycles_left = self.display_duration * 1000 / self._update_delay

        self._is_displaying = False
        if self.display_duration < 0: self.run()


    def _get_min_sec_string(self,seconds):
        seconds = int(seconds)
        m = seconds/60
        s = seconds - 60*m
        return "%d:%.02d" % (m,s)

    def _get_message(self):
        if not self.player.is_running() or self.player.is_stopped():
            return ""

        if self.player.get_duration() == 30:
            return "Spotify Advertisement"

        if self.player.is_playing(): icon = "|>"
        else: icon = "||"

        # Simple caching. Relies on the odds of two consecutive 
        # songs having the same title being very low.
        # Should limit scripting bridge calls.
        curr_song = self.player.get_song()
        if self._cached_song != curr_song:
            self._cached_song = curr_song
            self._cached_artist = self.player.get_artist()
            self._cached_album = self.player.get_album()
            self._cached_duration = self._get_min_sec_string(self.player.get_duration())

        return unicode(self.status_format).format(
            icon=icon,
            time=self._get_min_sec_string(self.player.get_position()),
            duration=self._cached_duration,
            song=self._cached_song,
            artist=self._cached_artist,
            album=self._cached_album)

    def run(self):
        if not self._is_displaying:
            self._is_displaying = True
            self._run()

    def _run(self):
        if self._cycles_left == 0:
            sublime.status_message('')
            self._cycles_left = self.display_duration * 1000 / self._update_delay
            self._is_displaying = False
            return
        elif self._cycles_left > 0:
            self._cycles_left -= 1

        sublime.status_message(self._get_message())
        sublime.set_timeout(lambda: self._run(), self._update_delay)


# This is kind of funky, but it keeps it so the player and updater
# are singletons. (A new class gets instantiated for each command call
# which would be less than ideal for these objects.)
PLAYER = SpotifyPlayer()
PLAYER.status_updater = SpotifyStatusUpdater(PLAYER)
