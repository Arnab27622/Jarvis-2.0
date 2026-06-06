import React, { useEffect, useRef, useState } from 'react';
import type { LogEntry } from '../App';
import { User, Cpu, Copy, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import TypingIndicator from './TypingIndicator';

interface DataStreamProps {
  logs: LogEntry[];
  isProcessing?: boolean;
}

const CopyButton = ({ textToCopy }: { textToCopy: string }) => {
  const [copied, setCopied] = React.useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(textToCopy);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      style={{
        position: 'absolute', top: '8px', right: '8px',
        background: 'rgba(0, 0, 0, 0.5)', border: '1px solid var(--primary-glow)',
        color: 'var(--primary-glow)', borderRadius: '4px', padding: '4px 8px',
        cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px',
        fontSize: '12px', zIndex: 10
      }}
    >
      {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? 'Copied!' : 'Copy'}
    </button>
  );
};

const TypewriterText: React.FC<{ text: string, duration?: number }> = ({ text, duration }) => {
  const [displayedText, setDisplayedText] = React.useState(duration ? '' : text);

  React.useEffect(() => {
    if (!duration) {
      return;
    }

    const tokens: Array<{type: 'text' | 'code', content: string}> = [];
    const regex = /(```[\s\S]*?```)/g;
    let lastIndex = 0;
    let match;
    let totalTextLength = 0;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        const textContent = text.substring(lastIndex, match.index);
        tokens.push({ type: 'text', content: textContent });
        totalTextLength += textContent.length;
      }
      tokens.push({ type: 'code', content: match[0] });
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < text.length) {
      const textContent = text.substring(lastIndex);
      tokens.push({ type: 'text', content: textContent });
      totalTextLength += textContent.length;
    }

    if (totalTextLength === 0) {
      // Avoid synchronous setState warning by pushing to the next tick
      setTimeout(() => setDisplayedText(text), 0);
      return;
    }

    const delayPerChar = (duration * 1000) / totalTextLength;
    const startTick = Date.now();

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTick;
      const targetTextChars = Math.floor(elapsed / delayPerChar);
      
      let currentOutput = "";
      let textCharsRevealed = 0;

      for (let i = 0; i < tokens.length; i++) {
        const token = tokens[i];
        if (token.type === 'code') {
          // Instantly reveal code blocks
          currentOutput += token.content;
        } else {
          // Reveal text smoothly
          const charsAvailable = token.content.length;
          const charsToTake = Math.min(charsAvailable, targetTextChars - textCharsRevealed);
          
          if (charsToTake > 0) {
            currentOutput += token.content.substring(0, charsToTake);
            textCharsRevealed += charsToTake;
          }
          
          // If we haven't fully revealed this text block, stop processing future blocks
          if (charsToTake < charsAvailable) {
            break;
          }
        }
      }

      setDisplayedText(currentOutput);

      if (textCharsRevealed >= totalTextLength) {
        clearInterval(interval);
        setDisplayedText(text);
      }
    }, 20); // 20ms polling is smooth and accurate

    return () => clearInterval(interval);
  }, [text, duration]);

  return (
    <ReactMarkdown
      components={{
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        code({ inline, className, children, ref: _ref, ...props }: React.ClassAttributes<HTMLElement> & React.HTMLAttributes<HTMLElement> & { inline?: boolean }) {
          const match = /language-(\w+)/.exec(className || '');
          return !inline && match ? (
            <div style={{ position: 'relative' }}>
              <CopyButton textToCopy={String(children).replace(/\n$/, '')} />
              <SyntaxHighlighter
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                style={vscDarkPlus as any}
                language={match[1]}
                PreTag="div"
                customStyle={{ width: '100%', overflowX: 'auto', boxSizing: 'border-box', maxWidth: '100%', paddingTop: '30px' }}
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            </div>
          ) : (
            <code className={className} style={{background: 'rgba(0, 240, 255, 0.1)', padding: '2px 4px', borderRadius: '4px', whiteSpace: 'pre-wrap', wordBreak: 'break-word'}} {...props}>
              {children}
            </code>
          );
        }
      }}
    >
      {!duration ? text : displayedText}
    </ReactMarkdown>
  );
};

const DataStream: React.FC<DataStreamProps> = ({ logs, isProcessing }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (!scrollRef.current) return;
    
    // Create a ResizeObserver to automatically scroll down whenever the 
    // contents of the chat log change their height (e.g. typewriter effect)
    const resizeObserver = new ResizeObserver(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    });
    
    // Also scroll immediately on mount or log changes
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    
    // Observe the first child (the AnimatePresence container) to detect all height shifts
    if (scrollRef.current.firstElementChild) {
      resizeObserver.observe(scrollRef.current.firstElementChild);
    }
    
    return () => resizeObserver.disconnect();
  }, [logs, isProcessing]);

  const filteredLogs = logs.filter(log => 
    log.text.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <div style={{ marginBottom: '15px' }}>
        <input 
          type="text" 
          placeholder="SEARCH COMMUNICATION LOGS..." 
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="hud-input"
          style={{ width: '100%', fontSize: '14px', padding: '5px' }}
        />
      </div>
      <div className="chat-log" ref={scrollRef}>
        <AnimatePresence initial={false}>
          {filteredLogs.map((log) => (
            <motion.div 
              key={log.id} 
              className={`log-entry ${log.sender}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              title={new Date(log.timestamp).toLocaleTimeString()}
            >
            <div className="log-icon">
              {log.sender === 'user' ? <User size={24} /> : <Cpu size={24} />}
            </div>
            <div className="log-content">
              {log.sender === 'user' && (
                <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginRight: '10px' }}>
                  &gt; COMMAND:
                </span>
              )}
              {log.sender === 'jarvis' ? (
                <div style={{
                  borderLeft: '4px solid var(--primary-glow)',
                  paddingLeft: '15px',
                  background: 'rgba(0, 240, 255, 0.05)',
                  padding: '10px 15px',
                  borderRadius: '0 4px 4px 0',
                  fontFamily: 'var(--font-main)'
                }}>
                  <TypewriterText text={log.text} duration={log.duration} />
                </div>
              ) : (
                <span style={{ fontFamily: 'var(--font-main)', color: 'var(--text-primary)' }}>{log.text}</span>
              )}
              {log.image && (
                <div style={{ marginTop: '10px' }}>
                  <a href={log.image} target="_blank" rel="noopener noreferrer">
                    <img src={log.image} alt="Generated" style={{ maxWidth: '250px', borderRadius: '4px', cursor: 'pointer', border: '1px solid var(--primary-glow)' }} />
                  </a>
                </div>
              )}
            </div>
          </motion.div>
          ))}
          {isProcessing && <TypingIndicator key="typing-indicator" />}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default DataStream;
