import React, { useState } from 'react';
import Layout from '@theme/Layout';

export default function Dashboard() {
    const [liveKey, setLiveKey] = useState('sk_live_hidden_..._9012');
    const [sandboxKey, setSandboxKey] = useState('sk_test_mock_..._5678');
    const [showSandbox, setShowSandbox] = useState(false);
    const [showLive, setShowLive] = useState(false);

    const regenerateKey = (type: 'sandbox' | 'live') => {
        alert(`Regenerating ${type} key... In a real app, this would hit /v1/auth/keys`);
    };

    return (
        <Layout title="Dashboard" description="CAPP API Key Management">
            <main style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
                <h1>Developer Dashboard</h1>
                <p>Manage your CAPP Network API keys for both Sandbox and Production environments.</p>

                <div style={{ marginTop: '2rem', padding: '1.5rem', border: '1px solid #ddd', borderRadius: '8px' }}>
                    <h2>Sandbox Environment</h2>
                    <p>Use these keys to simulate transactions without moving real funds. Balances are mocked.</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
                        <input
                            type={showSandbox ? "text" : "password"}
                            value={sandboxKey}
                            readOnly
                            style={{ width: '100%', padding: '0.5rem', fontFamily: 'monospace' }}
                        />
                        <button onClick={() => setShowSandbox(!showSandbox)} className="button button--secondary">
                            {showSandbox ? 'Hide' : 'Show'}
                        </button>
                        <button onClick={() => regenerateKey('sandbox')} className="button button--danger">
                            Regenerate
                        </button>
                    </div>
                </div>

                <div style={{ marginTop: '2rem', padding: '1.5rem', border: '1px solid #ddd', borderRadius: '8px' }}>
                    <h2>Live Environment</h2>
                    <p><strong>Warning:</strong> These keys move real funds across the CAPP Network.</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
                        <input
                            type={showLive ? "text" : "password"}
                            value={liveKey}
                            readOnly
                            style={{ width: '100%', padding: '0.5rem', fontFamily: 'monospace' }}
                        />
                        <button onClick={() => setShowLive(!showLive)} className="button button--secondary">
                            {showLive ? 'Hide' : 'Show'}
                        </button>
                        <button onClick={() => regenerateKey('live')} className="button button--danger">
                            Regenerate
                        </button>
                    </div>
                </div>
            </main>
        </Layout>
    );
}
