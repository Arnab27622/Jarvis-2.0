# Jarvis 2.0 - Sci-Fi HUD React Interface

This directory contains the React/Vite-based frontend for **Jarvis 2.0**. It is styled as a premium, sci-fi inspired Head-Up Display (HUD) utilizing Vanilla CSS for maximum styling flexibility, customized layout tokens, glassmorphic blur effects, and neon alert states.

## 🚀 Key Features

* **Biometric Authentication Overlay (`AuthScreen.tsx`)**
  Displays live visual scanning state feedback, webcam status logs, and authentication diagnostics received in real time from the OpenCV/dlib face detection engine.
* **Dual-Stream Typewriter (`DataStream.tsx`)**
  A custom typewriter effect that splits LLM streams: spoken conversational text types out character-by-character synchronized with the TTS audio playback, while markdown code blocks render instantly with syntax highlighting to prevent blocking UI execution.
* **Live Telemetry Dashboard (`TelemetryPanel.tsx`)**
  Monitors host performance in real time (CPU, RAM, GPU load, Disk usage, and smooth Network upload/download speeds) via WebSocket updates.
* **Secure Override Gate (App Permission Modal)**
  Interactive visual dialog for approving or denying CoderAgent tool execution requests (e.g., executing shell scripts or compiling binaries).
* **Settings Panel (`SettingsPanel.tsx`)**
  Quick controls for system configurations, visual theme presets (synced and saved dynamically via FastAPI backend REST APIs), and TTS voice speed settings.
* **Status Panels (`StatusPanel.tsx`)**
  Real-time indicators showing speech-recognition mic status ("LISTENING", "PROCESSING") and battery charge states.

## 🛠️ Technology Stack

* **Core**: React 19, TypeScript, Vite, HTML5
* **Styling**: Custom Vanilla CSS (configured via variable tokens in `index.css`)
* **Animations**: Framer Motion (for smooth panel slides, entry glows, and loading states)
* **Icons**: Lucide React
* **Markdown parsing**: React Markdown, React Syntax Highlighter

## 💻 Development & Build

### 1. Install Dependencies
```bash
npm install
```

### 2. Run Development Server
```bash
npm run dev
```
Starts the Vite dev server (usually at `http://localhost:5173`). In dev mode, the WebSocket client automatically routes requests to the FastAPI backend running on port `1410`.

### 3. Build Production Bundle
```bash
npm run build
```
Compiles TypeScript and bundles static assets into `dist/`. The Python backend statically mounts this folder, serving it directly on `http://localhost:1410`.
