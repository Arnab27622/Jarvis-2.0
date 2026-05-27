import React, { useEffect, useRef } from 'react';
import type { LogEntry } from '../App';
import { User, Cpu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface DataStreamProps {
  logs: LogEntry[];
}

const TypewriterText: React.FC<{ text: string, duration?: number }> = ({ text, duration }) => {
  const [displayedText, setDisplayedText] = React.useState(duration ? '' : text);

  React.useEffect(() => {
    if (!duration) return;

    // Characters per millisecond
    const delayPerChar = (duration * 1000) / Math.max(text.length, 1);
    let i = 0;


    const interval = setInterval(() => {
      setDisplayedText(text.slice(0, i + 1));
      i++;
      if (i >= text.length) clearInterval(interval);
    }, delayPerChar);

    return () => clearInterval(interval);
  }, [text, duration]);

  return <>{displayedText}</>;
};

const DataStream: React.FC<DataStreamProps> = ({ logs }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="chat-log" ref={scrollRef}>
      <AnimatePresence initial={false}>
        {logs.map((log) => (
          <motion.div 
            key={log.id} 
            className={`log-entry ${log.sender}`}
            initial={{ opacity: 0, x: -20, height: 0 }}
            animate={{ opacity: 1, x: 0, height: 'auto' }}
            transition={{ duration: 0.3 }}
          >
            <div className="log-icon">
              {log.sender === 'user' ? <User size={24} /> : <Cpu size={24} />}
            </div>
            <div className="log-content">
              {log.sender === 'jarvis' ? (
                <TypewriterText text={log.text} duration={log.duration} />
              ) : (
                log.text
              )}
              {log.image && (
                <div style={{ marginTop: '10px' }}>
                  <a href={log.image} target="_blank" rel="noopener noreferrer">
                    <img src={log.image} alt="Generated" style={{ maxWidth: '250px', borderRadius: '8px', cursor: 'pointer', border: '1px solid var(--primary-glow)' }} />
                  </a>
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

export default DataStream;
