import React, { useEffect, useRef } from 'react';
import type { LogEntry } from '../App';
import { User, Cpu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

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

  return (
    <ReactMarkdown
      components={{
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        code({ inline, className, children, ref: _ref, ...props }: React.ClassAttributes<HTMLElement> & React.HTMLAttributes<HTMLElement> & { inline?: boolean }) {
          const match = /language-(\w+)/.exec(className || '');
          return !inline && match ? (
            <SyntaxHighlighter
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              style={vscDarkPlus as any}
              language={match[1]}
              PreTag="div"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          ) : (
            <code className={className} style={{background: 'rgba(0, 240, 255, 0.1)', padding: '2px 4px', borderRadius: '4px'}} {...props}>
              {children}
            </code>
          );
        }
      }}
    >
      {displayedText}
    </ReactMarkdown>
  );
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
