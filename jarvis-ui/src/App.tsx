import React, { useEffect, useState, useRef } from 'react';
import DataStream from './components/DataStream';
import StatusPanel from './components/StatusPanel';
import AlertManager from './components/AlertManager';
import { Terminal } from 'lucide-react';

export type LogEntry = {
  id: string;
  sender: 'user' | 'jarvis';
  text: string;
  timestamp: number;
  duration?: number;
};

export type ToastAlert = {
  id: string;
  text: string;
  timestamp: number;
};

function App() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [alerts, setAlerts] = useState<ToastAlert[]>([]);
  const [input, setInput] = useState('');
  const [battery, setBattery] = useState({ percent: 100, plugged: true });
  const [isListening, setIsListening] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  
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
          setLogs(prev => [...prev, {
            id: Math.random().toString(36).substr(2, 9),
            sender: 'jarvis',
            text: payload.text,
            timestamp: payload.timestamp || Date.now(),
            duration: payload.duration
          }]);
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
    <div className="hud-container">
      <header className="hud-header hud-panel">
        <h1><Terminal size={28} /> JARVIS 2.0_</h1>
        <div className="status-indicators">
          <span>SYS.ONLINE</span>
          <span>SEC.M5</span>
          <span>{new Date().toLocaleTimeString()}</span>
        </div>
      </header>
      
      <main className="hud-main hud-panel">
        <DataStream logs={logs} />
      </main>
      
      <aside className="hud-sidebar">
        <StatusPanel battery={battery} isListening={isListening} />
      </aside>
      
      <footer className="hud-footer hud-panel">
        <form onSubmit={handleSend} className="input-container">
          <Terminal size={20} color="var(--primary-glow)" />
          <input 
            type="text" 
            className="hud-input" 
            placeholder="AWAITING MANUAL OVERRIDE..." 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
          />
          <button type="submit" className="hud-btn">EXECUTE</button>
        </form>
      </footer>
      
      <AlertManager alerts={alerts} setAlerts={setAlerts} />
    </div>
  );
}

export default App;
