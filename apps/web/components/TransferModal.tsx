'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import Portal from './Portal';
import TransferForm from './TransferForm';

interface TransferModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function TransferModal({ isOpen, onClose }: TransferModalProps) {
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
                            <div className="pointer-events-auto w-full max-w-lg">
                                {/* We inject the form here, but override its internal header with our modal chrome if needed, 
                                    or let the form handle its own layout. 
                                    Looking at TransferForm, it has its own container styling which we might want to strip 
                                    if wrapping it here, but for now we'll just wrap it cleanly. 
                                    Actually, reusing TransferForm logic is best, but visually it has a card look.
                                    Let's handle the styling in TransferForm or strip it. For expediency, we'll
                                    render TransferForm but pass a prop to minimalize it if we modify it, 
                                    or just render it as is.
                                */}
                                <div className="relative">
                                    {/* Close Button Overlay */}
                                    {/* TransferForm has a cancel button but we might want a top-right X too */}
                                    {/* Let's rely on TransferForm's internal structure for now to minimize refactor */}
                                    <TransferForm
                                        onCancel={onClose}
                                        onSuccess={() => {
                                            // Maybe show a success toast?
                                            onClose();
                                        }}
                                    />
                                </div>
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </Portal>
    );
}
