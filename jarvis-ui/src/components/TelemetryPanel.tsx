import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export interface TelemetryData {
  cpu: number;
  ram: number;
  disk: number;
  gpu: number;
  network: {
    upload: number;
    download: number;
  };
}

const TelemetryPanel: React.FC = () => {
  const [telemetry, setTelemetry] = useState<TelemetryData>({ cpu: 0, ram: 0, disk: 0, gpu: 0, network: { upload: 0, download: 0 } });

  useEffect(() => {
    const handleMetrics = (event: CustomEvent<TelemetryData>) => {
      setTelemetry(event.detail);
    };

    window.addEventListener('sys_metrics', handleMetrics as EventListener);
    
    return () => {
      window.removeEventListener('sys_metrics', handleMetrics as EventListener);
    };
  }, []);

  const formatNetworkSpeed = (bytesPerSec: number) => {
    if (bytesPerSec === 0) return '0 B/s';
    const k = 1024;
    const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    const i = Math.floor(Math.log(bytesPerSec) / Math.log(k));
    return parseFloat((bytesPerSec / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const renderProgressBar = (label: string, value: number, color: string = 'var(--primary-glow)') => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
      <span style={{ minWidth: '40px', color: color, fontWeight: 'bold' }}>{label}</span>
      <div style={{ flex: 1, background: 'rgba(0,0,0,0.5)', height: '10px', borderRadius: '5px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.05)' }}>
        <motion.div 
          style={{ background: color, height: '100%', boxShadow: `0 0 10px ${color}` }}
          animate={{ width: `${value}%` }}
          transition={{ ease: "easeOut", duration: 0.5 }}
        />
      </div>
      <span style={{ minWidth: '40px', textAlign: 'right' }}>{Math.round(value)}%</span>
    </div>
  );

  return (
    <div className="hud-panel widget hover-glow">
      <h3 style={{ marginBottom: '24px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>SYS.METRICS</h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%' }}>
        {renderProgressBar('CPU', telemetry.cpu || 0)}
        {renderProgressBar('RAM', telemetry.ram || 0)}
        {renderProgressBar('GPU', telemetry.gpu || 0)}
        {renderProgressBar('DSK', telemetry.disk || 0)}
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginTop: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>NET.UP</span>
            <span>{formatNetworkSpeed(telemetry.network?.upload || 0)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>NET.DN</span>
            <span>{formatNetworkSpeed(telemetry.network?.download || 0)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TelemetryPanel;
