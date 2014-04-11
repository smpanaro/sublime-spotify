# encoding: utf-8
from __future__ import unicode_literals

import sublime
import random

sublime3 = int(sublime.version()) >= 3000
if sublime3:
    set_timeout_async = sublime.set_timeout_async
else:
    set_timeout_async = sublime.set_timeout

class MusicPlayerStatusUpdater():
    def __init__(self, player):
        self.player = player

        s = sublime.load_settings("Spotify.sublime-settings")
        self.display_duration = int(s.get("status_duration"))
        self.status_format = s.get("status_format")

        self._cached_song = None
        self._cached_artist = None
        self._cached_album = None
        self._cached_duration = None

        self._update_delay = 400 # Udpate every n milliseconds.
        self._cycles_left = self.display_duration * 1000 // self._update_delay

        self.bars = ["▁","▂","▄","▅"]

        self._is_displaying = False
        if self.display_duration < 0 and self.player.is_running(): self.run()

    def _get_min_sec_string(self,seconds):
        m = seconds//60
        s = seconds - 60*m
        return "%d:%.02d" % (m,s)

    def _get_message(self):

        if self.player.is_playing():
            icon = "►"
            random.shuffle(self.bars)
        else:
            icon = "∣∣"

        # Simple caching. Relies on the odds of two consecutive
        # songs having the same title being very low.
        # Should limit scripting calls.
        curr_song = self.player.get_song()
        if self._cached_song != curr_song:
            self._cached_song = curr_song
            self._cached_artist = self.player.get_artist()
            self._cached_album = self.player.get_album()
            self._cached_duration_secs = self.player.get_duration()
            self._cached_duration = self._get_min_sec_string(self._cached_duration_secs)

        if self._cached_duration_secs >= 29 and self._cached_duration_secs <= 31:
            return "Spotify Advertisement"

        return self.status_format.format(
            equalizer="".join(self.bars),
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
            sublime.status_message("")
            self._cycles_left = self.display_duration * 1000 / self._update_delay
            self._is_displaying = False
            return
        elif self._cycles_left > 0:
            self._cycles_left -= 1

        if self.player.is_running() and not self.player.is_stopped():
            sublime.status_message(self._get_message())
            set_timeout_async(lambda: self._run(), self._update_delay)
        else:
            self._is_displaying = False
