import React from 'react';
import { Battery, BatteryCharging, Mic, MicOff } from 'lucide-react';
import { motion } from 'framer-motion';

interface StatusPanelProps {
  battery: { percent: number; plugged: boolean };
  isListening: boolean;
}

const StatusPanel: React.FC<StatusPanelProps> = ({ battery, isListening }) => {
  return (
    <>
      <div className="hud-panel widget">
        <h3 style={{ marginBottom: '15px', color: 'var(--text-secondary)' }}>PWR.SYSTEM</h3>
        <div className="battery-widget">
          <svg className="tech-ring spin-slow" width="150" height="150" viewBox="0 0 150 150">
            <circle cx="75" cy="75" r="70" fill="none" stroke="var(--border-color)" strokeWidth="2" />
            <circle cx="75" cy="75" r="60" fill="none" stroke="var(--border-color)" strokeWidth="1" strokeDasharray="5,5" />
            <motion.circle 
              cx="75" cy="75" r="70" 
              fill="none" 
              stroke={battery.plugged ? "var(--primary-glow)" : (battery.percent < 20 ? "var(--alert-glow)" : "var(--primary-glow)")}
              strokeWidth="4" 
              strokeDasharray={`${(battery.percent / 100) * 440} 440`}
              strokeLinecap="round"
              initial={{ strokeDasharray: "0 440" }}
              animate={{ strokeDasharray: `${(battery.percent / 100) * 440} 440` }}
              transition={{ duration: 1, ease: "easeOut" }}
              style={{ transformOrigin: 'center', transform: 'rotate(-90deg)' }}
            />
          </svg>
          <div className="battery-text" style={{ color: battery.percent < 20 && !battery.plugged ? 'var(--alert-glow)' : 'var(--text-primary)'}}>
            {battery.percent}%
          </div>
        </div>
        <div style={{ marginTop: '15px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          {battery.plugged ? <BatteryCharging size={24} color="var(--primary-glow)" /> : <Battery size={24} />}
          <span>{battery.plugged ? 'AC CONNECTED' : 'BATTERY DISCHARGING'}</span>
        </div>
      </div>

      <div className="hud-panel widget">
        <h3 style={{ marginBottom: '15px', color: 'var(--text-secondary)' }}>AUDIO.RECEPTOR</h3>
        <div style={{ position: 'relative', width: '100px', height: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {isListening && (
            <motion.div
              style={{ position: 'absolute', width: '100%', height: '100%', borderRadius: '50%', background: 'var(--primary-glow)', opacity: 0.2 }}
              animate={{ scale: [1, 1.5, 1], opacity: [0.2, 0, 0.2] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          )}
          <svg className={`tech-ring ${isListening ? 'spin-reverse' : ''}`} width="100" height="100" viewBox="0 0 100 100" style={{ position: 'absolute' }}>
            <circle cx="50" cy="50" r="45" fill="none" stroke={isListening ? "var(--primary-glow)" : "var(--border-color)"} strokeWidth="2" strokeDasharray="20,10,5,10" />
          </svg>
          {isListening ? <Mic size={32} color="var(--primary-glow)" /> : <MicOff size={32} color="var(--text-secondary)" />}
        </div>
        <div style={{ marginTop: '15px', color: isListening ? 'var(--primary-glow)' : 'var(--text-secondary)' }}>
          {isListening ? 'AWAITING INPUT...' : 'STANDBY MODE'}
        </div>
      </div>
    </>
  );
};

export default StatusPanel;
