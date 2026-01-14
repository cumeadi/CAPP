
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import Portal from './Portal';
import BridgeWidget from './BridgeWidget';

interface BridgeModalProps {
    isOpen: boolean;
    onClose: () => void;
    address: string;
}

export default function BridgeModal({ isOpen, onClose }: BridgeModalProps) {
    return (
        <Portal>
            <AnimatePresence>
                {isOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={onClose}
                            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 transition-all"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none p-4"
                        >
                            <div className="relative pointer-events-auto">
                                <button
                                    onClick={onClose}
                                    className="absolute -top-12 right-0 p-2 text-text-tertiary hover:text-white transition-colors"
                                >
                                    <X className="w-6 h-6" />
                                </button>
                                <BridgeWidget />
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </Portal>
    );
}


