import React, { useEffect } from 'react';
import type { ToastAlert } from '../App';
import { motion, AnimatePresence } from 'framer-motion';
import { Info } from 'lucide-react';

interface AlertManagerProps {
  alerts: ToastAlert[];
  setAlerts: React.Dispatch<React.SetStateAction<ToastAlert[]>>;
}

const AlertManager: React.FC<AlertManagerProps> = ({ alerts, setAlerts }) => {
  useEffect(() => {
    if (alerts.length > 0) {
      const timer = setTimeout(() => {
        setAlerts((prev) => prev.slice(1));
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [alerts, setAlerts]);

  return (
    <div className="toast-container">
      <AnimatePresence>
        {alerts.map((alert) => (
          <motion.div 
            key={alert.id} 
            className="toast"
            initial={{ opacity: 0, x: 50, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 50, scale: 0.9 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          >
            <Info size={24} color="var(--primary-glow)" />
            <span>{alert.text}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

export default AlertManager;
