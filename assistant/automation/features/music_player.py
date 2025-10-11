"""
Music Player Module for Voice Assistant

This module provides comprehensive music playback functionality for the voice assistant,
allowing users to play, control, and manage their local music library through voice commands.
It supports multiple audio formats and includes features like shuffle, playlist management,
and volume control.

Key Features:
- Play random music from local directory
- Play specific songs by name
- Playlist management with shuffle
- Playback controls (play, pause, stop, next, previous)
- Volume control
- Multiple audio format support

Dependencies:
- pygame: For audio playback and mixing
- os: For file system operations
- random: For shuffle functionality
"""

import os
import random
import pygame
from assistant.core.speak_selector import speak


# Initialize pygame mixer for audio playback
pygame.mixer.init()


class MusicPlayer:
    """
    A comprehensive music player class for handling local music playback.

    This class manages all aspects of music playback including file discovery,
    playback control, volume management, and playlist handling.

    Attributes:
        music_dir (str): Path to the music directory
        current_track (str): Currently playing track filename
        is_playing (bool): Playback state flag
        is_paused (bool): Pause state flag
        playlist (list): List of tracks in current playlist
        current_index (int): Index of current track in playlist
        volume (float): Current volume level (0.0 to 1.0)
    """

    def __init__(self):
        """
        Initialize the MusicPlayer with default settings.

        Sets up the music directory path and initializes player state variables.
        The default music directory is set to the user's Music folder.
        """
        self.music_dir = r"C:\Users\ARNAB DEY\Music"
        self.current_track = None
        self.is_playing = False
        self.is_paused = False
        self.playlist = []
        self.current_index = 0
        self.volume = 0.7  # Default volume (0.0 to 1.0)

    def get_music_files(self):
        """
        Scan the music directory and retrieve all supported audio files.

        Supported formats include: MP3, WAV, M4A, FLAC, AAC

        Returns:
            list: List of supported music filenames found in the directory

        Raises:
            Prints error message if directory doesn't exist
        """
        supported_formats = (".mp3", ".wav", ".m4a", ".flac", ".aac")
        music_files = []

        # Check if music directory exists
        if not os.path.exists(self.music_dir):
            speak("Music directory not found. Please check the path.")
            return []

        # Scan directory for supported audio files
        for file in os.listdir(self.music_dir):
            if file.lower().endswith(supported_formats):
                music_files.append(file)

        return music_files

    def play_random_music(self):
        """
        Play a random song from the music directory with shuffle functionality.

        This method:
        1. Scans for available music files
        2. Creates a shuffled playlist if none exists
        3. Stops any currently playing music
        4. Plays a random track from available music
        5. Provides voice feedback on playback

        Voice Commands that use this:
        - "play music"
        - "play some music"
        - "shuffle music"
        - "play random music"
        """
        music_files = self.get_music_files()

        if not music_files:
            speak("No music files found in your Music directory.")
            return

        # Create shuffled playlist if empty
        if not self.playlist:
            self.playlist = music_files.copy()
            random.shuffle(self.playlist)

        # Stop currently playing music before starting new track
        if self.is_playing:
            self.stop_music()

        # Select and play random track
        self.current_track = random.choice(self.playlist)
        track_path = os.path.join(self.music_dir, self.current_track)

        try:
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False

            # Extract track name without extension for voice feedback
            track_name = os.path.splitext(self.current_track)[0]
            speak(f"Playing {track_name}")

        except Exception as e:
            speak("Sorry, I couldn't play the music file.")
            print(f"Music playback error: {e}")

    def play_specific_song(self, song_name):
        """
        Play a specific song by searching for matching filenames.

        Performs partial matching on song names - any file containing the
        search term will be considered a match.

        Args:
            song_name (str): The name or part of the name of the song to play

        Voice Commands that use this:
        - "play song [song_name]"
        - "play the song [song_name]"
        """
        music_files = self.get_music_files()

        if not music_files:
            speak("No music files found in your Music directory.")
            return

        # Find songs matching the search term (case-insensitive partial match)
        matching_songs = [f for f in music_files if song_name.lower() in f.lower()]

        if not matching_songs:
            speak(f"Sorry, I couldn't find any song matching '{song_name}'")
            return

        # Stop current playback before starting new track
        if self.is_playing:
            self.stop_music()

        # Play the first matching song found
        self.current_track = matching_songs[0]
        track_path = os.path.join(self.music_dir, self.current_track)

        try:
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False

            track_name = os.path.splitext(self.current_track)[0]
            speak(f"Playing {track_name}")

        except Exception as e:
            speak("Sorry, I couldn't play the music file.")
            print(f"Music playback error: {e}")

    def pause_music(self):
        """
        Pause the currently playing music.

        Only pauses if music is currently playing and not already paused.
        Provides appropriate voice feedback for different states.

        Voice Commands that use this:
        - "pause music"
        - "pause the music"
        - "pause song"
        """
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            speak("Music paused")
        else:
            speak("No music is currently playing")

    def resume_music(self):
        """
        Resume playback of paused music.

        Only resumes if music is currently paused.
        Provides appropriate voice feedback for different states.

        Voice Commands that use this:
        - "resume music"
        - "resume the music"
        - "continue music"
        - "unpause music"
        """
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            speak("Music resumed")
        else:
            speak("No music is currently paused")

    def stop_music(self):
        """
        Stop music playback completely and reset player state.

        This method:
        - Stops the music playback
        - Resets all playback state flags
        - Clears the current track reference
        - Provides voice confirmation

        Voice Commands that use this:
        - "stop music"
        - "stop the music"
        - "stop song"
        """
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_track = None
        speak("Music stopped")

    def next_track(self):
        """
        Play the next track in the current playlist.

        Implements circular playlist navigation - when reaching the end,
        wraps around to the beginning of the playlist.

        Voice Commands that use this:
        - "next track"
        - "next song"
        - "play next"
        """
        if not self.playlist:
            speak("No playlist available")
            return

        # Circular increment of playlist index
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.current_track = self.playlist[self.current_index]
        track_path = os.path.join(self.music_dir, self.current_track)

        try:
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False

            track_name = os.path.splitext(self.current_track)[0]
            speak(f"Playing next track: {track_name}")

        except Exception as e:
            speak("Sorry, I couldn't play the next track.")
            print(f"Music playback error: {e}")

    def previous_track(self):
        """
        Play the previous track in the current playlist.

        Implements circular playlist navigation - when at the beginning,
        wraps around to the end of the playlist.

        Voice Commands that use this:
        - "previous track"
        - "previous song"
        - "play previous"
        - "last song"
        """
        if not self.playlist:
            speak("No playlist available")
            return

        # Circular decrement of playlist index
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.current_track = self.playlist[self.current_index]
        track_path = os.path.join(self.music_dir, self.current_track)

        try:
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False

            track_name = os.path.splitext(self.current_track)[0]
            speak(f"Playing previous track: {track_name}")

        except Exception as e:
            speak("Sorry, I couldn't play the previous track.")
            print(f"Music playback error: {e}")

    def set_volume(self, level):
        """
        Set the music playback volume to a specific level.

        Args:
            level (float): Volume level between 0.0 (silent) and 1.0 (maximum)

        Note:
            Values outside 0.0-1.0 range are automatically clamped
        """
        try:
            # Clamp volume to valid range
            if level < 0:
                level = 0
            elif level > 1:
                level = 1

            self.volume = level
            pygame.mixer.music.set_volume(level)

            # Convert to percentage for voice feedback
            volume_percent = int(level * 100)
            speak(f"Volume set to {volume_percent} percent")

        except Exception as e:
            speak("Sorry, I couldn't adjust the volume")
            print(f"Volume adjustment error: {e}")

    def increase_volume(self):
        """
        Increase music volume by 10%.

        Caps at maximum volume (1.0) if already at or near maximum.

        Voice Commands that use this:
        - "increase music volume"
        - "music volume up"
        - "louder music"
        """
        new_volume = min(1.0, self.volume + 0.1)
        self.set_volume(new_volume)

    def decrease_volume(self):
        """
        Decrease music volume by 10%.

        Caps at minimum volume (0.0) if already at or near minimum.

        Voice Commands that use this:
        - "decrease music volume"
        - "music volume down"
        - "softer music"
        """
        new_volume = max(0.0, self.volume - 0.1)
        self.set_volume(new_volume)

    def get_current_track(self):
        """
        Get the name of the currently playing track.

        Returns:
            str: Name of current track without file extension,
                 or None if no track is playing

        Voice Commands that use this:
        - "what's playing"
        - "current track"
        - "which song is this"
        - "what song is playing"
        """
        if self.current_track:
            return os.path.splitext(self.current_track)[0]
        return None


# Create global music player instance for application-wide use
music_player = MusicPlayer()
