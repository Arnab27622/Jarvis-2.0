# final_music_player.py
import os
import random
import threading
import pygame
from pathlib import Path
from typing import List
import time


class FinalMusicPlayer:
    """
    FINAL music player with ultra-minimal interference.
    """
    
    def __init__(self, music_directory: str):
        """Initialize with final anti-interference settings."""
        self.music_directory = Path(music_directory)
        self.supported_formats = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".wma"}
        self.current_song = None
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.25
        
        # Initialize pygame mixer with FINAL settings
        pygame.mixer.quit()
        pygame.mixer.pre_init(
            frequency=48000,    # MAXIMUM separation from clap detection (22050)
            size=-16, 
            channels=2, 
            buffer=4096        # MAXIMUM buffer size
        )
        pygame.mixer.init()
        pygame.mixer.music.set_volume(self.volume)
        
        # Get list of music files
        self.music_files = self._get_music_files()
        
        if not self.music_files:
            print(f"Warning: No supported music files found in {music_directory}")
    
    def _get_music_files(self) -> List[Path]:
        """Get all supported music files from the directory."""
        music_files = []
        
        if not self.music_directory.exists():
            print(f"Warning: Music directory {self.music_directory} does not exist")
            return music_files
        
        # Recursively search for music files
        for file_path in self.music_directory.rglob("*"):
            if (file_path.is_file() and 
                file_path.suffix.lower() in self.supported_formats):
                music_files.append(file_path)
        
        return music_files
    
    def play_random_song(self):
        """Play a random song with maximum anti-interference."""
        if not self.music_files:
            print("No music files available to play")
            return
        
        # Stop current song if playing
        if self.is_playing:
            self.stop()
        
        # Longer pause to let audio system settle
        time.sleep(0.3)
        
        # Select random song
        self.current_song = random.choice(self.music_files)
        
        try:
            print(f"🎵 Playing (Ultra-Low Volume): {self.current_song.name}")
            pygame.mixer.music.load(str(self.current_song))
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            
            # Start monitoring thread
            self._start_monitoring_thread()
            
        except pygame.error as e:
            print(f"Error playing {self.current_song.name}: {e}")
            self.is_playing = False
    
    def _start_monitoring_thread(self):
        """Start a thread to monitor music playback status."""
        def monitor():
            while self.is_playing:
                if not pygame.mixer.music.get_busy() and not self.is_paused:
                    self.is_playing = False
                    print("🎵 Song finished")
                    break
                threading.Event().wait(1.0)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def pause(self):
        """Pause the current song."""
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            print("⏸️ Music paused")
    
    def resume(self):
        """Resume the paused song."""
        if self.is_playing and self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            print("▶️ Music resumed")
    
    def stop(self):
        """Stop the current song."""
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            print("⏹️ Music stopped")
            time.sleep(0.3)  # Longer pause
    
    def toggle_play_pause(self):
        """Toggle between play/pause states."""
        if self.is_playing:
            if self.is_paused:
                self.resume()
            else:
                self.pause()
        else:
            self.play_random_song()
    
    def set_volume(self, volume: float):
        """Set the volume (capped at 20% maximum)."""
        self.volume = max(0.0, min(0.2, volume))  # Cap at 20%
        pygame.mixer.music.set_volume(self.volume)
        print(f"🔊 Volume: {int(self.volume * 100)}% (Ultra-low for interference prevention)")
    
    def get_status(self) -> dict:
        """Get current player status."""
        return {
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "current_song": self.current_song.name if self.current_song else None,
            "volume": self.volume,
            "total_songs": len(self.music_files),
        }


class FinalClapMusicIntegration:
    """
    FINAL integration with minimal interference.
    """
    
    def __init__(self, music_directory: str):
        """Initialize with final settings."""
        self.music_player = FinalMusicPlayer(music_directory)
        self.last_clap_time = 0
        self.cooldown_period = 1.0  # Shorter for better responsiveness
        self.processing_clap = False
        self.pending_single_clap = None
        self.double_clap_timeout = 0.8  # Shorter timeout
    
    def on_clap_detected(self, confidence: float = 0.0):
        """FINAL callback with minimal processing."""
        current_time = time.time()
        
        # Prevent overlapping clap processing
        if self.processing_clap:
            return
            
        # Check cooldown
        if current_time - self.last_clap_time < self.cooldown_period:
            return
        
        # Simplified double-clap logic
        if self.pending_single_clap:
            time_since_first = current_time - self.pending_single_clap
            
            if time_since_first <= self.double_clap_timeout:
                # Double clap detected
                self.pending_single_clap = None
                self._handle_double_clap_immediate(confidence)
                return
            else:
                # Process previous single clap
                self._handle_single_clap_immediate(confidence)
                self.pending_single_clap = None
        
        # Set up for potential double clap
        self.pending_single_clap = current_time
        
        # Handle single clap timeout
        def process_single_clap():
            time.sleep(self.double_clap_timeout)
            if self.pending_single_clap == current_time:
                self.pending_single_clap = None
                self._handle_single_clap_immediate(confidence)
        
        threading.Thread(target=process_single_clap, daemon=True).start()
    
    def _handle_single_clap_immediate(self, confidence: float):
        """Handle single clap with minimal processing."""
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
            # Quick release of processing flag
            def release_flag():
                time.sleep(0.3)
                self.processing_clap = False
            threading.Thread(target=release_flag, daemon=True).start()
    
    def _handle_double_clap_immediate(self, confidence: float):
        """Handle double clap with minimal processing."""
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
            # Quick release of processing flag
            def release_flag():
                time.sleep(0.3)
                self.processing_clap = False
            threading.Thread(target=release_flag, daemon=True).start()
    
    def get_player(self) -> FinalMusicPlayer:
        """Get the music player instance."""
        return self.music_player


# Usage functions
def create_final_clap_music_system(music_directory: str) -> FinalClapMusicIntegration:
    """Create the final clap-music system."""
    return FinalClapMusicIntegration(music_directory)


if __name__ == "__main__":
    # Example usage - keeping minimal as requested
    pass