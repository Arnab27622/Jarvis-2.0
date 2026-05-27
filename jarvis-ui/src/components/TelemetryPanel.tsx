import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export interface TelemetryData {
  cpu: number;
  ram: number;
}

const TelemetryPanel: React.FC = () => {
  const [telemetry, setTelemetry] = useState<TelemetryData>({ cpu: 0, ram: 0 });

  useEffect(() => {
    const handleMetrics = (event: CustomEvent<TelemetryData>) => {
      setTelemetry(event.detail);
    };

    // The websocket handler in App.tsx will dispatch a custom event to window
    // so we don't have to drill props if we don't want to, but actually
    // passing it as a prop is better React practice.
    window.addEventListener('sys_metrics', handleMetrics as EventListener);
    
    return () => {
      window.removeEventListener('sys_metrics', handleMetrics as EventListener);
    };
  }, []);

  return (
    <div className="hud-panel widget" style={{ marginTop: '20px' }}>
      <h3 style={{ marginBottom: '15px', color: 'var(--text-secondary)' }}>SYS.METRICS</h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%' }}>
        
        {/* CPU Tracker */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span style={{ minWidth: '40px', color: 'var(--primary-glow)', fontWeight: 'bold' }}>CPU</span>
          <div style={{ flex: 1, background: 'rgba(0,0,0,0.5)', height: '10px', borderRadius: '5px', overflow: 'hidden' }}>
            <motion.div 
              style={{ background: 'var(--primary-glow)', height: '100%' }}
              animate={{ width: `${telemetry.cpu}%` }}
              transition={{ ease: "easeOut", duration: 0.5 }}
            />
          </div>
          <span style={{ minWidth: '40px', textAlign: 'right' }}>{Math.round(telemetry.cpu)}%</span>
        </div>

        {/* RAM Tracker */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span style={{ minWidth: '40px', color: 'var(--primary-glow)', fontWeight: 'bold' }}>RAM</span>
          <div style={{ flex: 1, background: 'rgba(0,0,0,0.5)', height: '10px', borderRadius: '5px', overflow: 'hidden' }}>
            <motion.div 
              style={{ background: 'var(--primary-glow)', height: '100%' }}
              animate={{ width: `${telemetry.ram}%` }}
              transition={{ ease: "easeOut", duration: 0.5 }}
            />
          </div>
          <span style={{ minWidth: '40px', textAlign: 'right' }}>{Math.round(telemetry.ram)}%</span>
        </div>

      </div>
    </div>
  );
};

export default TelemetryPanel;
