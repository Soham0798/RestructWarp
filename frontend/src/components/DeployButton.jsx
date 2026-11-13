import { useState } from 'react';
import { Rocket, Loader2, ExternalLink, RefreshCw } from 'lucide-react';
import { API_BASE } from '../config';
import { CopyButton } from './GenerationUtils';

const pillStyle = {
    display: 'flex', alignItems: 'center', gap: '5px',
    padding: '5px 12px', borderRadius: '7px', fontSize: '0.75rem', fontWeight: 600,
    whiteSpace: 'nowrap', cursor: 'pointer', textDecoration: 'none',
};

/**
 * Publishes `html` to Vercel via the backend and shows the live URL.
 * While mounted it remembers the project it deployed to, so deploying again
 * (e.g. after a refine) updates the same URL. Unmount it to start a new site.
 */
export default function DeployButton({ html, name }) {
    const [deploying, setDeploying] = useState(false);
    const [site, setSite] = useState(null); // { url, project, html }
    const [error, setError] = useState('');

    const deploy = async () => {
        const token = localStorage.getItem('token');
        if (!token || !html || deploying) return;
        setDeploying(true);
        setError('');
        try {
            const res = await fetch(`${API_BASE}/deploy/vercel`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ html, name, project: site?.project }),
            });
            const body = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Deploy failed (${res.status})`);
            setSite({ url: body.url, project: body.project, html });
        } catch (e) {
            setError(e.message || 'Deploy failed');
        } finally {
            setDeploying(false);
        }
    };

    const stale = site && site.html !== html; // code changed since the last deploy

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {error && (
                <span title={error} style={{
                    color: '#f87171', fontSize: '0.72rem', maxWidth: '260px',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                    {error}
                </span>
            )}
            {site && !deploying && (
                <>
                    <a href={site.url} target="_blank" rel="noopener noreferrer" title={site.url} style={{
                        ...pillStyle, color: '#56d364',
                        background: 'rgba(86,211,100,0.1)', border: '1px solid rgba(86,211,100,0.3)',
                    }}>
                        <ExternalLink size={12} style={{ flexShrink: 0 }} />
                        <span style={{ maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {site.url.replace('https://', '')}
                        </span>
                        {stale && <span style={{ opacity: 0.7 }}>(older version)</span>}
                    </a>
                    <CopyButton text={site.url} size={12} />
                </>
            )}
            {(!site || stale || deploying) && (
                <button type="button" onClick={deploy} disabled={deploying || !html} style={{
                    ...pillStyle, color: 'white', border: '1px solid #4f46e5',
                    background: '#6366f1', opacity: deploying ? 0.7 : 1,
                    cursor: deploying ? 'default' : 'pointer',
                }}>
                    {deploying
                        ? <><Loader2 size={12} className="animate-spin" /> Deploying…</>
                        : site
                            ? <><RefreshCw size={12} /> Redeploy</>
                            : <><Rocket size={12} /> Deploy</>}
                </button>
            )}
        </div>
    );
}
