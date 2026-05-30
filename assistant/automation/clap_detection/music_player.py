"""
Module for a minimal, low-interference music player controlled by clap detection.
"""

import os
import random
import threading
import pygame
from pathlib import Path
from typing import List
import time


class FinalMusicPlayer:
    """
    Handles audio playback with optimized settings to minimize system interference.
    """
    
    def __init__(self, music_directory: str):
        """Initializes the mixer and scans the directory for supported audio files."""
        self.music_directory = Path(music_directory)
        self.supported_formats = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".wma"}
        self.current_song = None
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.25
        
        pygame.mixer.quit()
        pygame.mixer.pre_init(
            frequency=48000,
            size=-16, 
            channels=2, 
            buffer=4096
        )
        pygame.mixer.init()
        pygame.mixer.music.set_volume(self.volume)
        
        self.music_files = self._get_music_files()
        
        if not self.music_files:
            print(f"Warning: No supported music files found in {music_directory}")
    
    def _get_music_files(self) -> List[Path]:
        """Recursively retrieves all supported audio files from the directory."""
        music_files = []
        
        if not self.music_directory.exists():
            print(f"Warning: Music directory {self.music_directory} does not exist")
            return music_files
        
        for file_path in self.music_directory.rglob("*"):
            if (file_path.is_file() and 
                file_path.suffix.lower() in self.supported_formats):
                music_files.append(file_path)
        
        return music_files
    
    def play_random_song(self) -> None:
        """Selects and plays a random track from the library."""
        if not self.music_files:
            print("No music files available to play")
            return
        
        if self.is_playing:
            self.stop()
        
        time.sleep(0.3)
        
        self.current_song = random.choice(self.music_files)
        
        try:
            print(f"🎵 Playing (Ultra-Low Volume): {self.current_song.name}")
            pygame.mixer.music.load(str(self.current_song))
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            
            self._start_monitoring_thread()
            
        except pygame.error as e:
            print(f"Error playing {self.current_song.name}: {e}")
            self.is_playing = False
    
    def _start_monitoring_thread(self) -> None:
        """Spawns a background thread to detect when a song finishes."""
        def monitor():
            while self.is_playing:
                if not pygame.mixer.music.get_busy() and not self.is_paused:
                    self.is_playing = False
                    print("🎵 Song finished")
                    break
                threading.Event().wait(1.0)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def pause(self) -> None:
        """Pauses the currently playing track."""
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            print("⏸️ Music paused")
    
    def resume(self) -> None:
        """Resumes playback of a paused track."""
        if self.is_playing and self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            print("▶️ Music resumed")
    
    def stop(self) -> None:
        """Stops playback entirely."""
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            print("⏹️ Music stopped")
            time.sleep(0.3)
    
    def toggle_play_pause(self) -> None:
        """Switches between play and pause states."""
        if self.is_playing:
            if self.is_paused:
                self.resume()
            else:
                self.pause()
        else:
            self.play_random_song()
    
    def set_volume(self, volume: float) -> None:
        """Sets the playback volume, capped at 20%."""
        self.volume = max(0.0, min(0.2, volume))
        pygame.mixer.music.set_volume(self.volume)
        print(f"🔊 Volume: {int(self.volume * 100)}% (Ultra-low for interference prevention)")
    
    def get_status(self) -> dict:
        """Returns the current state of the player."""
        return {
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "current_song": self.current_song.name if self.current_song else None,
            "volume": self.volume,
            "total_songs": len(self.music_files),
        }


class FinalClapMusicIntegration:
    """
    Bridges clap detection events to music player actions.
    """
    
    def __init__(self, music_directory: str):
        """Initializes the integration with clap timing logic."""
        self.music_player = FinalMusicPlayer(music_directory)
        self.last_clap_time = 0
        self.cooldown_period = 1.0
        self.processing_clap = False
        self.pending_single_clap = None
        self.double_clap_timeout = 0.8
    
    def on_clap_detected(self, confidence: float = 0.0):
        """Processes clap events to trigger play/pause or track skipping."""
        current_time = time.time()
        
        if self.processing_clap:
            return
            
        if current_time - self.last_clap_time < self.cooldown_period:
            return
        
        if self.pending_single_clap:
            time_since_first = current_time - self.pending_single_clap
            
            if time_since_first <= self.double_clap_timeout:
                self.pending_single_clap = None
                self._handle_double_clap_immediate(confidence)
                return
            else:
                self._handle_single_clap_immediate(confidence)
                self.pending_single_clap = None
        
        self.pending_single_clap = current_time
        
        def process_single_clap():
            time.sleep(self.double_clap_timeout)
            if self.pending_single_clap == current_time:
                self.pending_single_clap = None
                self._handle_single_clap_immediate(confidence)
        
        threading.Thread(target=process_single_clap, daemon=True).start()
    
    def _handle_single_clap_immediate(self, confidence: float):
        """Executes play/pause toggle."""
        if self.processing_clap:
            return
        
        self.processing_clap = True
        current_time = time.time()
        self.last_clap_time = current_time
        
        print(f"👏 Single clap detected! (Confidence: {confidence * 100:.1f}%)")
        
        try:
            self.music_player.toggle_play_pause()
        except Exception as e:
            print(f"Error in single clap action: {e}")
        finally:
            def release_flag():
                time.sleep(0.3)
                self.processing_clap = False
            threading.Thread(target=release_flag, daemon=True).start()
    
    def _handle_double_clap_immediate(self, confidence: float):
        """Executes random track skip."""
        if self.processing_clap:
            return
        
        self.processing_clap = True
        current_time = time.time()
        self.last_clap_time = current_time
        
        print(f"👏👏 Double clap detected! (Confidence: {confidence * 100:.1f}%)")
        
        try:
            self.music_player.play_random_song()
        except Exception as e:
            print(f"Error in double clap action: {e}")
        finally:
            def release_flag():
                time.sleep(0.3)
                self.processing_clap = False
            threading.Thread(target=release_flag, daemon=True).start()
    
    def get_player(self) -> FinalMusicPlayer:
        """Returns the underlying music player instance."""
        return self.music_player


def create_final_clap_music_system(music_directory: str) -> FinalClapMusicIntegration:
    """Factory function to initialize the clap-controlled music system."""
    return FinalClapMusicIntegration(music_directory)


if __name__ == "__main__":
    pass
