import sys
import os
import sublime
from subprocess import Popen, PIPE

try:
    from Spotify.singleton import Singleton
except:
    from singleton import Singleton

# Wrap player interactions to compensate for different naming styles and platforms.
@Singleton
class AppleScriptSpotifyPlayer():
    def __init__(self):
        if sys.platform == "win32":
            raise NotImplementedError("Sorry, there's no Windows support yet.")
        elif sys.platform == "darwin": # OS X
            pass
        else:
            raise NotImplementedError("Sorry, your platform is not supported yet.")
        self.status_updater = None

    def is_running(self):
        res = self._execute_command('get running of application "Spotify"')
        return res == "true"

    def show_status_message(self):
        self.status_updater.run()

    def _get_state(self):
        return self._execute_command('tell application "Spotify" to player state')

    def is_playing(self):
        return self._get_state() == "playing"

    def is_stopped(self):
        return self._get_state() == "stopped"

    def is_paused(self):
        return self._get_state() == "paused"

    # Current Track information
    def get_artist(self):
        return self._execute_command('tell application "Spotify" to artist of current track')

    def get_album(self):
        return self._execute_command('tell application "Spotify" to album of current track')

    def get_song(self):
        return self._execute_command('tell application "Spotify" to name of current track')

    def get_position(self):
        numstr = self._execute_command('tell application "Spotify" to player position')
        return int(float(numstr))

    def get_duration(self):
        numstr = self._execute_command('tell application "Spotify" to duration of current track')
        return int(float(numstr))

    # Actions
    def play_pause(self):
        self._execute_command('tell application "Spotify" to playpause')

    def play_track(self, track_url, attempts=0):
        # Wait for the application to launch.
        if not self.is_running():
            if attempts > 10: return
            self._execute_command('tell application "Spotify" to activate')
            sublime.set_timeout(lambda: self.play_track(track_url, attempts+1), 1000)
        else:
            self._execute_command('tell application "Spotify" to play track "{}"'.format(track_url))
            self.show_status_message()

    def play(self, attempts=0):
        if not self.is_running():
            if attempts > 10: return
            self._execute_command('tell application "Spotify" to activate')
            sublime.set_timeout(lambda: self.play(attempts+1), 1000)
        else:
            self._execute_command('tell application "Spotify" to play')
            self.show_status_message()

    def pause(self):
        self._execute_command('tell application "Spotify" to pause')

    def next(self):
        self._execute_command('tell application "Spotify" to next track')
        self.show_status_message()

    def previous(self):
        # Call it twice - once to get back to the beginning
        # of this song and once to go back to the next.
        self._execute_command('tell application "Spotify" to previous track')
        self._execute_command('tell application "Spotify" to previous track')
        self.show_status_message()

    def toggle_shuffle(self):
        if self._execute_command('tell application "Spotify" to shuffling enabled') == "true":
            if self._execute_command('tell application "Spotify" to shuffling') == "false":
                self._execute_command('tell application "Spotify" to set shuffling to true')
            else:
                self._execute_command('tell application "Spotify" to set shuffling to false')

    def toggle_repeat(self):
        if self._execute_command('tell application "Spotify" to repeating enabled'):
            if self._execute_command('tell application "Spotify" to repeating') == "false":
                self._execute_command('tell application "Spotify" to set repeating to true')
            else:
                self._execute_command('tell application "Spotify" to set repeating to false')

    def _execute_command(self, cmd):
        stdout = ""
        if cmd != "":
            bytes_cmd = cmd.encode('latin-1')
            p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate(bytes_cmd)
        return stdout.decode('utf-8').strip()
