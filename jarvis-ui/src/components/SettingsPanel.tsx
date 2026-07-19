import { useState, useEffect } from 'react';
import { Settings, X, Save } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const SettingsPanel = ({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) => {
  const [settings, setSettings] = useState({
    tts_voice: 'am_michael',
    tts_speed: 1.08,
    theme: 'cyan'
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetch('/api/settings')
        .then(res => res.json())
        .then(data => setSettings(data))
        .catch(err => console.error("Failed to load settings:", err));
    }
  }, [isOpen]);

  const handleSave = () => {
    setLoading(true);
    fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    }).then(() => {
      setLoading(false);
      onClose();
      // Apply theme locally
      document.documentElement.setAttribute('data-theme', settings.theme);
    }).catch(err => {
      console.error("Failed to save settings:", err);
      setLoading(false);
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            exit={{ opacity: 0 }}
            style={{
              position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
              background: 'rgba(0,0,0,0.5)', zIndex: 100
            }}
            onClick={onClose}
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            style={{
              position: 'fixed', top: 0, right: 0, width: '350px', height: '100vh',
              background: 'var(--panel-bg)', borderLeft: '1px solid var(--border-color)',
              backdropFilter: 'blur(10px)', zIndex: 101, padding: '20px',
              display: 'flex', flexDirection: 'column', gap: '20px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Settings /> SYSTEM CONFIG</h2>
              <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-primary)', cursor: 'pointer' }}><X /></button>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <label>VOICE MODULE</label>
              <select 
                className="hud-input" 
                value={settings.tts_voice}
                onChange={e => setSettings({...settings, tts_voice: e.target.value})}
              >
                <option value="am_michael">AM_MICHAEL (M)</option>
                <option value="af_sarah">AF_SARAH (F)</option>
                <option value="bf_emma">BF_EMMA (F)</option>
                <option value="am_adam">AM_ADAM (M)</option>
              </select>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <label>SPEECH RATE: {settings.tts_speed}x</label>
              <input 
                type="range" 
                min="0.5" max="2.0" step="0.05"
                value={settings.tts_speed}
                onChange={e => setSettings({...settings, tts_speed: parseFloat(e.target.value)})}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <label>UI THEME</label>
              <select 
                className="hud-input" 
                value={settings.theme}
                onChange={e => setSettings({...settings, theme: e.target.value})}
              >
                <option value="cyan">COLD LUXURY (DEFAULT)</option>
                <option value="amber">TERMINAL BRUTALISM</option>
                <option value="minimal">EDITORIAL MINIMALIST</option>
                <option value="oled">OLED BLACK</option>
              </select>
            </div>
            
            <button className="hud-btn" style={{ marginTop: 'auto', display: 'flex', justifyContent: 'center', gap: '10px' }} onClick={handleSave} disabled={loading}>
              <Save /> {loading ? 'SAVING...' : 'SAVE & APPLY'}
            </button>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default SettingsPanel;
