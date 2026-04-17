# Jarvis 2.0 Command Reference

This document lists all the voice commands supported by Jarvis 2.0. Commands are processed in `assistant/interface/commands.py`.

---

## 🚀 Application Control
- **"open [app name]"**: Launch a specific application.
  - *Example: "Jarvis, open Notepad"*
- **"close"**: Close the currently active window.
  - *Example: "Jarvis, close notepad"*

---

## ⏰ Alarms & Reminders
- **"set alarm [time]"**: Create a new alarm.
  - *Example: "Jarvis, set alarm for 7:00 AM"*
- **"list alarms"**: Show all pending alarms.
  - *Example: "Jarvis, show my alarms"*
- **"cancel all alarms"**: Delete all active alarms.
  - *Example: "Jarvis, cancel all alarms"*
- **"remind me to [task] at [time]"**: Create a new reminder.
  - *Example: "Jarvis, remind me to drink water in 30 minutes"*
- **"list reminders"**: Show all pending reminders.
  - *Example: "Jarvis, what are my reminders?"*
- **"cancel all reminders"**: Clear all active reminders.
  - *Example: "Jarvis, clear reminders"*

---

## 🪟 Window Management
- **"minimize" / "minimise"**: Hide the active window.
  - *Example: "Jarvis, minimize the window"*
- **"maximize" / "maximise"**: Expand the active window.
  - *Example: "Jarvis, maximize the browser"*
- **"restore"**: Restore window from minimized/maximized state.
  - *Example: "Jarvis, restore window"*
- **"switch window"**: Cycle through open applications.
  - *Example: "Jarvis, switch window"*

---

## 🌐 Browser Controls
- **"new tab"**: Open a new browser tab.
  - *Example: "Jarvis, open a new tab"*
- **"incognito" / "private tab"**: Open a private browsing session.
  - *Example: "Jarvis, open incognito tab"*
- **"bookmark this"**: Save the current page.
  - *Example: "Jarvis, bookmark this page"*
- **"reload" / "refresh"**: Refresh the current page.
  - *Example: "Jarvis, reload page"*
- **"go back" / "go forward"**: Navigate through browser history.
  - *Example: "Jarvis, go back"*
- **"duplicate tab"**: Open the current URL in a new tab.
  - *Example: "Jarvis, duplicate this tab"*
- **"developer tools"**: Open browser inspection tools.
  - *Example: "Jarvis, open dev tools"*

---

## 🎵 Music & Media
- **"play [random] music"**: Start playing music from your library.
  - *Example: "Jarvis, play some music"*
- **"play song [name]"**: Search for and play a specific track.
  - *Example: "Jarvis, play song Never Gonna Give You Up"*
- **"pause / resume / stop music"**: Control music playback.
  - *Example: "Jarvis, pause the music"*
- **"next / previous track"**: Skip between songs in your playlist.
  - *Example: "Jarvis, play next track"*
- **"increase / decrease music volume"**: Adjust music-specific volume.
  - *Example: "Jarvis, louder music"*
*   **"what's playing"**: Ask for the current track name.
  - *Example: "Jarvis, which song is this?"*

---

## 📺 YouTube Automation
- **"play [topic] on youtube"**: Search and play a specific video.
  - *Example: "Jarvis, play Interstellar soundtrack on youtube"*
- **"search for [topic] on youtube"**: Show search results page.
  - *Example: "Jarvis, search for python tutorials on youtube"*
- **"pause / resume / replay video"**: Control YouTube playback.
  - *Example: "Jarvis, pause video"*
- **"next / previous video"**: Skip between videos in a queue.
  - *Example: "Jarvis, next video"*
- **"mute / unmute video"**: Toggle video audio.
  - *Example: "Jarvis, mute video"*
- **"skip [forward/backward] video"**: Jump 10 seconds.
  - *Example: "Jarvis, skip video"*
- **"turn on / off subtitles"**: Toggle closed captions.
  - *Example: "Jarvis, turn on subtitles"*

---

## 🛠️ System Utilities
- **"screenshot"**: Capture and save the screen.
  - *Example: "Jarvis, take a screenshot"*
- **"check internet speed"**: Run a network speed test.
  - *Example: "Jarvis, check internet speed"*
- **"mic / speaker health test"**: Verify audio hardware status.
  - *Example: "Jarvis, run mic health test"*
- **"brightness [up/down]"**: Adjust screen brightness.
  - *Example: "Jarvis, increase brightness"*
- **"increase / decrease volume"**: Change system volume level.
  - *Example: "Jarvis, decrease volume"*
- **"system info"**: Get battery and memory status.
  - *Example: "Jarvis, system info"*
- **"check running apps"**: List all active processes.
  - *Example: "Jarvis, check running apps"*
- **"check ip address"**: Show your current network IP.
  - *Example: "Jarvis, check my ip address"*

---

## ⌨️ Text & Editing
- **"write [text]"**: Type out dictated text into the active field.
  - *Example: "Jarvis, write This is an automated message."*
- **"press enter"**: Execute the Enter key.
  - *Example: "Jarvis, press enter"*
- **"select all / cut / copy / paste"**: Standard text manipulation.
  - *Example: "Jarvis, copy this"*
- **"undo / redo"**: Reverse or repeat last action.
  - *Example: "Jarvis, undo it"*

---

## 🔍 Information & Weather
- **"search the web for [topic]"**: Detailed AI-enhanced web search.
  - *Example: "Jarvis, search the web for who is the CEO of Tesla"*
- **"search for [topic] on google"**: Standard Google search.
  - *Example: "Jarvis, search for local cafes on google"*
- **"search for [topic] on wikipedia"**: Get summary from Wikipedia.
  - *Example: "Jarvis, search for Quantum Physics on wikipedia"*
- **"check temperature / weather"**: Get local weather conditions.
  - *Example: "Jarvis, check the temperature"*
- **"check the weather of [location]"**: Look up weather elsewhere.
  - *Example: "Jarvis, check the weather of Tokyo"*
- **"tell me news"**: Headlines for today.
  - *Example: "Jarvis, what's today's news?"*
- **"tell me a joke"**: Get a random joke.
  - *Example: "Jarvis, tell me a joke"*

---

## 🧠 Memory & AI
- **"remember that [info]"**: Save information to long-term memory.
  - *Example: "Jarvis, remember that my car keys are in the kitchen drawer"*
- **"what did i ask you to remember"**: Recall saved information.
  - *Example: "Jarvis, what did i ask you to remember?"*
- **"create an image of [prompt]"**: Generate AI images.
  - *Example: "Jarvis, generate an image of a futuristic city in Mars"*
- **[Any other query]**: Jarvis will use its LLM "brain" to respond.
  - *Example: "Jarvis, how does a black hole work?"*

---

## 🔌 System Power
- **"shutdown"**: Shut down the system in 10 seconds.
  - *Example: "Jarvis, shutdown"*
- **"restart"**: Restart the system in 10 seconds.
  - *Example: "Jarvis, restart"*
- **"go to sleep" / "stop"**: Close command mode and wait for wake word.
  - *Example: "Jarvis, go to sleep"*
