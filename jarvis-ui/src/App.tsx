import React, { useEffect, useState, useRef } from 'react';
import DataStream from './components/DataStream';
import StatusPanel from './components/StatusPanel';
import TelemetryPanel from './components/TelemetryPanel';
import AlertManager from './components/AlertManager';
import SettingsPanel from './components/SettingsPanel';
import { Terminal, Loader, Settings } from 'lucide-react';

export type LogEntry = {
  id: string;
  sender: 'user' | 'jarvis';
  text: string;
  timestamp: number;
  duration?: number;
  image?: string;
  message_id?: string;
};

export type ToastAlert = {
  id: string;
  text: string;
  timestamp: number;
};

const Clock = () => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return <span>{time.toLocaleTimeString()}</span>;
};

function App() {
  const [logs, setLogs] = useState<LogEntry[]>(() => {
    try {
      const saved = localStorage.getItem('jarvis_chat_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [alerts, setAlerts] = useState<ToastAlert[]>([]);
  const [input, setInput] = useState('');
  const [battery, setBattery] = useState({ percent: 100, plugged: true });
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [glitch, setGlitch] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [permissionRequest, setPermissionRequest] = useState<{text: string} | null>(null);
  const ws = useRef<WebSocket | null>(null);

  const playBeep = (freq = 800, type = 'sine' as OscillatorType, duration = 0.1) => {
    try {
      const CustomWindow = window as Window & typeof globalThis & { webkitAudioContext?: typeof AudioContext };
      const audioCtx = new (CustomWindow.AudioContext || CustomWindow.webkitAudioContext!)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      oscillator.type = type;
      oscillator.frequency.value = freq;
      gainNode.gain.setValueAtTime(0.05, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      oscillator.start();
      oscillator.stop(audioCtx.currentTime + duration);
    } catch {
      // Ignore audio errors if blocked by browser policy
    }
  };
  
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  useEffect(() => {
    localStorage.setItem('jarvis_chat_history', JSON.stringify(logs));
  }, [logs]);

  useEffect(() => {
    // Load initial theme from backend
    fetch('/api/settings')
      .then(res => res.json())
      .then(data => {
        if (data.theme) {
          document.documentElement.setAttribute('data-theme', data.theme);
        }
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    // Connect to WebSocket using the appropriate port
    // During dev (Vite on 5173), we connect to backend on 1410
    // During prod (FastAPI serves on 1410), we connect to same host/port
    const host = window.location.hostname;
    const wsUrl = `ws://${host}:1410/ws`;
    
    ws.current = new WebSocket(wsUrl);
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const payload = data.data;
      
      switch (data.type) {
        case 'speak':
          setIsProcessing(false);
          playBeep(600, 'triangle', 0.2);
          setLogs(prev => {
            const lastLog = prev[prev.length - 1];
            if (payload.message_id && lastLog && lastLog.message_id === payload.message_id) {
              return [
                ...prev.slice(0, -1),
                {
                  ...lastLog,
                  text: lastLog.text + payload.text,
                  duration: (lastLog.duration || 0) + (payload.duration || 0)
                }
              ];
            } else {
              return [...prev, {
                id: Math.random().toString(36).substr(2, 9),
                sender: 'jarvis',
                text: payload.text,
                timestamp: payload.timestamp || Date.now(),
                duration: payload.duration,
                image: payload.image,
                message_id: payload.message_id
              }];
            }
          });
          break;
        case 'user_voice':
        case 'user_text':
          setLogs(prev => [...prev, {
            id: Math.random().toString(36).substr(2, 9),
            sender: 'user',
            text: payload.text,
            timestamp: payload.timestamp || Date.now()
          }]);
          break;
        case 'notify':
          setIsProcessing(false);
          playBeep(400, 'sine', 0.3);
          setAlerts(prev => [...prev, {
            id: Math.random().toString(36).substr(2, 9),
            text: payload.text,
            timestamp: payload.timestamp || Date.now()
          }]);
          break;
        case 'battery':
          setBattery({
            percent: payload.percent,
            plugged: payload.plugged
          });
          break;
        case 'listening':
          setIsListening(payload.listening);
          break;
        case 'processing':
          setIsProcessing(payload.state);
          break;
        case 'error':
          setIsProcessing(false);
          setGlitch(true);
          playBeep(150, 'sawtooth', 0.5);
          setTimeout(() => setGlitch(false), 800);
          break;
        case 'cmd_done':
          setIsProcessing(false);
          playBeep(1200, 'sine', 0.1);
          break;
        case 'permission_request':
          setPermissionRequest({ text: payload.text });
          playBeep(400, 'square', 0.5); // Urgent sound
          break;
        case 'sys_metrics':
          window.dispatchEvent(new CustomEvent('sys_metrics', { detail: payload }));
          break;
      }
    };
    
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || !ws.current) return;
    
    ws.current.send(JSON.stringify({
      type: 'command',
      data: { text: input.trim() }
    }));
    
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') setInput('');
  };

  return (
    <>
      <div className="bg-mesh"></div>
      <div className={`hud-container ${glitch ? 'glitch-effect' : ''}`}>
        <header className="hud-header hud-panel">
          <h1><Terminal size={28} /> JARVIS 2.0_</h1>
          <div className="status-indicators" style={{ display: 'flex', alignItems: 'center' }}>
            <span style={{ color: isOnline ? 'inherit' : 'var(--alert-glow)' }}>
              SYS.{isOnline ? 'ONLINE' : 'OFFLINE'}
            </span>
            <span>SEC.M5</span>
            <Clock />
            <Settings 
              size={24} 
              style={{ cursor: 'pointer', color: 'var(--primary-glow)', marginLeft: '10px' }} 
              onClick={() => setIsSettingsOpen(true)} 
            />
          </div>
        </header>
        
        <main className="hud-main hud-panel">
          <DataStream logs={logs} isProcessing={isProcessing} />
        </main>
        
        <aside className="hud-sidebar">
          <StatusPanel battery={battery} isListening={isListening} />
          <TelemetryPanel />
        </aside>
        
        <footer className="hud-footer hud-panel">
          <form onSubmit={handleSend} className="input-container">
            <Terminal size={20} color="var(--primary-glow)" />
            <input 
              type="text" 
              className="hud-input" 
              placeholder={isProcessing ? "PROCESSING..." : "AWAITING MANUAL OVERRIDE..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isProcessing}
              autoFocus
            />
            {isProcessing ? (
              <Loader className="spin-slow" size={24} color="var(--primary-glow)" />
            ) : (
              <button type="submit" className="hud-btn">EXECUTE</button>
            )}
          </form>
        </footer>
        
        <AlertManager alerts={alerts} setAlerts={setAlerts} />
        <SettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        
        {/* Permission Request Modal */}
        {permissionRequest && (
          <div style={{
            position: 'absolute', bottom: '20px', right: '20px', zIndex: 1000,
            display: 'flex', justifyContent: 'flex-end', alignItems: 'flex-end'
          }}>
            <div className="hud-panel widget" style={{ 
              maxWidth: '400px', 
              border: '1px solid var(--alert-glow)',
              backgroundColor: 'rgba(20, 5, 5, 0.9)',
              boxShadow: '0 8px 32px rgba(255, 75, 75, 0.2)'
            }}>
              <h3 style={{ color: 'var(--alert-glow)', borderBottom: '1px solid rgba(255, 75, 75, 0.2)', paddingBottom: '10px', fontSize: '16px' }}>
                SECURITY OVERRIDE REQUEST
              </h3>
              <p style={{ marginTop: '15px', color: '#e0ffff', fontSize: '14px', fontFamily: 'var(--font-mono)' }}>{permissionRequest.text}</p>
              <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                <button 
                  className="hud-btn" 
                  style={{ flex: 1, borderColor: 'var(--alert-glow)', color: 'var(--alert-glow)' }}
                  onClick={() => {
                    ws.current?.send(JSON.stringify({ type: 'permission_response', data: { approved: false } }));
                    setPermissionRequest(null);
                  }}
                >DENY</button>
                <button 
                  className="hud-btn" 
                  style={{ flex: 1, backgroundColor: 'var(--alert-glow)', color: '#000', borderColor: 'var(--alert-glow)' }}
                  onClick={() => {
                    ws.current?.send(JSON.stringify({ type: 'permission_response', data: { approved: true } }));
                    setPermissionRequest(null);
                  }}
                >APPROVE</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default App;
