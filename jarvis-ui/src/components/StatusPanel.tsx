import React from 'react';
import { Battery, BatteryCharging, Mic, MicOff } from 'lucide-react';
import { motion } from 'framer-motion';

interface StatusPanelProps {
  battery: { percent: number; plugged: boolean };
  isListening: boolean;
}

const visualizerBars = [...Array(12)].map(() => ({
  height: `${Math.random() * 15 + 5}px`,
  duration: 0.5 + Math.random() * 0.5,
  delay: Math.random() * 0.2
}));

const StatusPanel: React.FC<StatusPanelProps> = ({ battery, isListening }) => {
  return (
    <>
      <div className="hud-panel widget hover-glow">
        <h3 style={{ marginBottom: '24px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>PWR.SYSTEM</h3>
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
              transition={{ type: "spring", stiffness: 50, damping: 20 }}
              style={{ transformOrigin: 'center', transform: 'rotate(-90deg)' }}
            />
          </svg>
          <div className="battery-text" style={{ 
            color: battery.percent < 20 && !battery.plugged ? 'var(--alert-glow)' : 'var(--text-primary)',
            display: 'flex', flexDirection: 'column', alignItems: 'center'
          }}>
            <span>{battery.percent}%</span>
            <span style={{ fontSize: '10px', color: 'var(--text-secondary)', letterSpacing: '1px' }}>CHARGE</span>
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
        
        {/* Audio Visualizer */}
        <div style={{ display: 'flex', gap: '3px', marginTop: '15px', height: '20px', alignItems: 'flex-end' }}>
          {visualizerBars.map((bar, i) => (
            <motion.div
              key={i}
              style={{
                width: '4px',
                background: isListening ? 'var(--primary-glow)' : 'var(--border-color)',
                borderRadius: '2px',
                height: isListening ? '10px' : '4px'
              }}
              animate={isListening ? {
                height: ['4px', bar.height, '4px'],
              } : { height: '4px' }}
              transition={isListening ? {
                duration: bar.duration,
                repeat: Infinity,
                repeatType: 'reverse',
                ease: "easeInOut",
                delay: bar.delay
              } : {}}
            />
          ))}
        </div>
      </div>
    </>
  );
};

export default StatusPanel;
