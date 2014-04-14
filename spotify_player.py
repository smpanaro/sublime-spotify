import sys
import os
import sublime

sublime3 = int(sublime.version()) >= 3000
if sublime3:
    from Spotify.singleton import Singleton
else:
    from ScriptingBridge import SBApplication
    from singleton import Singleton

# Wrap player interactions to compensate for different naming styles and platforms.
@Singleton
class SpotifyPlayer():
    def __init__(self):
        if sys.platform == "win32":
            # import win32com.client
            # c = win32com.client.gencache.EnsureDispatch("iTunes.Application")
            raise NotImplementedError("Sorry, there's no Windows support yet.")
        elif sys.platform == "darwin": # OS X
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
        return self.client.properties()["playerState"].description()[-6:-2]

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
