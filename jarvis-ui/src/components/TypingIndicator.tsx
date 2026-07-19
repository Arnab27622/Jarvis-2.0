import { motion } from 'framer-motion';

const TypingIndicator = () => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9 }}
      style={{ display: 'flex', gap: '4px', padding: '10px 15px', alignItems: 'center', color: 'var(--primary-glow)' }}
    >
      <span style={{ fontSize: '14px', marginRight: '8px', letterSpacing: '2px' }}>PROCESSING</span>
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
          transition={{ duration: 1, repeat: Infinity, repeatType: "reverse", ease: "easeInOut", delay: i * 0.15 }}
          style={{
            width: '6px',
            height: '6px',
            backgroundColor: 'var(--primary-glow)',
            borderRadius: '50%',
            boxShadow: '0 0 5px var(--primary-glow)'
          }}
        />
      ))}
    </motion.div>
  );
};

export default TypingIndicator;
