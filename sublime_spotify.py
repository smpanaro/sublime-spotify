import sublime, sublime_plugin
import sys
import threading
import time

# Wrap player interactions to compensate for different naming styles and platforms.
class SpotifyPlayer():
    def __init__(self):
        if sys.platform == "win32":
            # import win32com.client
            # c = win32com.client.gencache.EnsureDispatch("iTunes.Application")
            pass
        elif sys.platform == "darwin": # OS X
            print "importing os x shit"
            from ScriptingBridge import SBApplication
            # Get a reference to the client without launching it. 
            # Spotify will launch automatically when called.
            self.client = SBApplication.alloc().initWithBundleIdentifier_("com.spotify.client")
            self.status_updater = SpotifyStatusUpdater(self)
            self.status_updater.setDaemon(False)
            self.status_updater.start()

    def is_running(self):
        return self.client.isRunning()

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

    def play(self, attempts=0):
        self.client.play()
        # One edge case: calling play when spotify is not launched.
        # Spotify can take a few seconds to start up. Call play after that.
        # Will only work if a song was previously playing.
        if not self.is_playing() and attempts < 5:
            sublime.set_timeout(lambda: self.play(attempts+1), 100)

    def pause(self):
        self.client.pause()

    def next(self):
        self.client.nextTrack()

    def previous(self):
        self.client.previousTrack()

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

class SpotifyCommand(sublime_plugin.TextCommand):
    def __init__(self, view):
        self.view = view
        self.player = PLAYER

# class SpotifyPlayPauseCommand(SpotifyCommand):
#     def run(self, edit):
#         self.player.play_pause()

class SpotifyPlayCommand(SpotifyCommand):
    def run(self, edit):
        self.player.play()

class SpotifyPauseCommand(SpotifyCommand):
    def run(self, edit):
        self.player.pause()

class SpotifyNextTrackCommand(SpotifyCommand):
    def run(self, edit):
        self.player.next()

class SpotifyPreviousTrackCommand(SpotifyCommand):
    def run(self, edit):
        self.player.previous()

class SpotifyToggleShuffleCommand(SpotifyCommand):
    def run(self, edit):
        self.player.toggle_shuffle()

class SpotifyToggleRepeatCommand(SpotifyCommand):
    def run(self, edit):
        self.player.toggle_repeat()

class SpotifyStatusUpdater(threading.Thread):
    def __init__(self, player):
        self.player = player
        self.seconds_paused = 0.0
        self.update_interval = .2 # seconds
        threading.Thread.__init__(self)

    def _get_min_sec_string(self,seconds):
        seconds = int(seconds)
        m = seconds/60
        s = seconds - 60*m
        return "%d:%.02d" % (m,s)

    def _get_message(self):
        if not self.player.is_running() or self.player.is_stopped():
            return ""

        if self.player.get_duration() == 30:
            return "\t\tSpotify Advertisement"


        if self.player.is_playing(): icon = "|>"
        else: icon = "||"
        return "\t\t{icon} - {song} - {artist} - {album} - {time}/{duration} ".format(
            icon=icon,
            time=self._get_min_sec_string(self.player.get_position()),
            duration=self._get_min_sec_string(self.player.get_duration()),
            song=self.player.get_song(),
            artist=self.player.get_artist(),
            album=self.player.get_album() )

    # must be called on the main thread
    def set_status_message(self, message):
        # print sublime.status_message()
        sublime.status_message(message)

    def run(self):
        while True:
            time.sleep(self.update_interval)

            if self.player.is_running() and self.player.is_playing():
                self.seconds_paused = 0.0
            else:
                self.seconds_paused += self.update_interval
                if self.seconds_paused > 5:
                    sublime.set_timeout(lambda: self.set_status_message(""), 0)
                    continue

            msg = self._get_message()
            sublime.set_timeout(lambda: self.set_status_message(msg), 0)


PLAYER = SpotifyPlayer()
