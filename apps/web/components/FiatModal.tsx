import React, { useEffect, useRef } from 'react';
import { Transak } from '@transak/transak-sdk';
import { X } from 'lucide-react';

interface FiatModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function FiatModal({ isOpen, onClose }: FiatModalProps) {
    const transakRef = useRef<any>(null);

    useEffect(() => {
        if (isOpen && !transakRef.current) {
            const transakConfig = {
                apiKey: process.env.NEXT_PUBLIC_TRANSAK_API_KEY || '4fcd6904-706b-4e32-9a97-90028198f62f', // Default staging key if env not set
                environment: 'STAGING', // STAGING/PRODUCTION
                defaultCryptoCurrency: 'ETH',
                themeColor: '#000000', // Example dark theme
                hostURL: window.location.origin,
                widgetHeight: '625px',
                widgetWidth: '500px',
                widgetUrl: 'https://global-stg.transak.com', // Required by newer SDK versions
                referrer: window.location.origin, // Required field
            };

            const transak = new Transak(transakConfig);

            transak.init();

            // event listeners
            // @ts-ignore - 'on' is static in some versions
            Transak.on(Transak.EVENTS.TRANSAK_WIDGET_CLOSE, () => {
                transak.close();
                transakRef.current = null;
                onClose();
            });

            // @ts-ignore
            Transak.on(Transak.EVENTS.TRANSAK_ORDER_SUCCESSFUL, (orderData: any) => {
                console.log('Transak Order Success', orderData);
                // transak.close();
                // transakRef.current = null;
                // onClose();
            });

            transakRef.current = transak;
        }

        // Cleanup if component unmounts or isOpen changes to false unexpectedly (though widget close handles most cleanup)
        return () => {
            if (!isOpen && transakRef.current) {
                transakRef.current.close();
                transakRef.current = null;
            }
        }
    }, [isOpen, onClose]);


    // Logic to handle cleanup when isOpen becomes false via prop (e.g. parent force close)
    useEffect(() => {
        if (!isOpen && transakRef.current) {
            transakRef.current.close();
            transakRef.current = null;
        }
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        // Transak SDK injects an iframe. We might not need a visual wrapper if Transak handles the modal overlay itself.
        // However, the Transak SDK's `init()` usually opens a modal.
        // So we just return null here as the SDK manages the DOM elements?
        // Actually, looking at docs, Transak SDK attaches to the body.
        // We should just manage the 'init' call.
        // But to ensure React 'controls' it, we might want it to be idempotent.
        null
    );
}
