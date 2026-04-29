import { useEffect, useState } from 'react';
import { motion } from 'motion/react';

interface RouteAnimationProps {
  children: React.ReactNode;
  delay?: number;
}

export default function RouteAnimation({ children, delay = 0 }: RouteAnimationProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
    >
      {children}
    </motion.div>
  );
}
