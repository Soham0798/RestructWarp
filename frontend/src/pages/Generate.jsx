import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import {
    Globe, Layers, Server, Sparkles, Send, RefreshCw, Eye, Code2,
    Loader2, ChevronRight, Copy, Check, X, Zap, Activity, FileCode,
    Terminal, Play, StopCircle, MessageSquare, Bot, User as UserIcon,
    FolderTree, ChevronDown, ChevronRight as ChevRight,
    Maximize2, Minimize2
} from 'lucide-react';
import { API_BASE } from '../config';

// ─── Constants ────────────────────────────────────────────────────────────────

const TYPES = [
    { id: 'website', label: 'Website', icon: Globe, desc: 'Landing page / SaaS site', color: '#6366f1', bg: 'rgba(99,102,241,0.12)' },
    { id: 'fullstack', label: 'Full Stack', icon: Layers, desc: 'React + FastAPI project', color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)' },
    { id: 'backend', label: 'Backend API', icon: Server, desc: 'FastAPI + SQLite REST API', color: '#ec4899', bg: 'rgba(236,72,153,0.12)' },
];

const EXAMPLES = [
    { emoji: '🍕', text: 'Pizza delivery startup with loyalty rewards' },
    { emoji: '💸', text: 'Fintech budgeting app with AI insights' },
    { emoji: '🎓', text: 'Online learning platform with live classes' },
    { emoji: '🏋️', text: 'Gym management SaaS with trainer booking' },
    { emoji: '🩺', text: 'Telemedicine platform for rural clinics' },
    { emoji: '🎮', text: 'Indie game studio portfolio with merch shop' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function parseOutput(output, type) {
    if (type === 'website') return { html: output, files: null };
    if (type === 'fullstack') {
        // Streaming path: output is set to the raw previewHtml string (HTML, not JSON)
        if (typeof output === 'string') {
            // If it looks like HTML (streamed frontend), treat it directly as html
            const trimmed = output.trim();
            if (trimmed.startsWith('<') || trimmed.toLowerCase().startsWith('<!doctype')) {
                return { html: output, files: { 'src/index.html': output } };
            }
            // Otherwise it may be a JSON-serialised fullstack object
            try {
                const parsed = JSON.parse(output);
                return {
                    html: parsed.frontend?.preview || null,
                    files: { ...(parsed.backend || {}), ...(parsed.frontend?.files || {}) }
                };
            } catch {
                // Fallback: still treat as HTML (it's the frontend code)
                return { html: output, files: { 'src/index.html': output } };
            }
        }
        // Already an object
        return {
            html: output.frontend?.preview || null,
            files: { ...(output.backend || {}), ...(output.frontend?.files || {}) }
        };
    }
    if (typeof output === 'string') {
        try { output = JSON.parse(output); } catch { return { html: null, files: { 'output.txt': output } }; }
    }
    if (type === 'backend') return { html: null, files: output };
    return { html: null, files: output };
}

/**
 * Strip Claude scratchpad / markdown fences from streamed HTML.
 * Returns only the raw HTML starting from <!DOCTYPE or <html>.
 */
function stripHtmlPreamble(raw) {
    if (!raw || typeof raw !== 'string') return raw;
    // Remove leading/trailing markdown code fences like ```html ... ```
    let cleaned = raw.replace(/^\s*```(?:html)?\s*\n?/i, '');
    cleaned = cleaned.replace(/\n?```\s*$/i, '');

    // Check if the AI incorrectly put markdown fences inside
    if (cleaned.includes('```html')) {
        cleaned = cleaned.replace(/```html\n?/gi, '');
        cleaned = cleaned.replace(/```\n?/g, '');
    }

    // Strip any text before <!DOCTYPE or <html
    const match = cleaned.match(/<!doctype\s+html[^>]*>|<html[\s>]/i);
    if (match) {
        cleaned = cleaned.slice(match.index);
    }

    // --- SAFETY NETS FOR BABEL & JSX ---

    const hasJsxSyntax = cleaned.includes('/>') || cleaned.includes('</') && cleaned.includes('const App');
    const hasReactCode = cleaned.includes('ReactDOM.createRoot') || cleaned.includes('React.createElement') || hasJsxSyntax;

    // 1. Inject Babel Standalone if missing but needed
    if ((cleaned.includes('text/babel') || hasReactCode) && !cleaned.includes('babel.min.js')) {
        cleaned = cleaned.replace(
            '</head>',
            '<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>\n</head>'
        );
    }

    // 2. Rewrite <script> to <script type="text/babel"> if it contains React code
    if (hasReactCode && !cleaned.includes('text/babel')) {
        // We find the <script> tag that is most likely the app code (usually large, or at the end of body)
        // A simple heuristic: replace <script> with <script type="text/babel"> if it's the one that contains ReactDOM
        // Let's just aggressively rewrite all <script> tags that don't have src attributes to text/babel as a fallback
        cleaned = cleaned.replace(/<script(?!\s+src)[\s>]/gi, match => {
            if (match.endsWith('>')) return '<script type="text/babel">';
            return '<script type="text/babel" '; // if it has other attributes
        });
    }

    // 3. Fix Groq hallucinating Tailwind CDN as a <link> tag instead of <script>
    if (cleaned.includes('cdn.tailwindcss.com')) {
        cleaned = cleaned.replace(/<link[^>]*href=["']https:\/\/cdn\.tailwindcss\.com["'][^>]*>/i,
            '<script src="https://cdn.tailwindcss.com"></script>'
        );
    }

    // 4. Fix Groq hallucinating API port 8001 instead of 8000 in fetch calls
    if (cleaned.includes('localhost:8001')) {
        cleaned = cleaned.replace(/localhost:8001/g, 'localhost:8000');
    }

    // 5. Fix generic network error display that hides mock data fallback
    // If the model generates a generic fetch catch without actually falling back to mock data
    // Or if the model sets error state but doesn't handle it gracefully
    // We already passed the backend so we just fix the port. The app should now fetch properly.

    // 6. Trim ANY trailing garbage code after </html> that causes preview to break on link clicks
    const closingHtmlIndex = cleaned.toLowerCase().lastIndexOf('</html>');
    if (closingHtmlIndex !== -1) {
        cleaned = cleaned.substring(0, closingHtmlIndex + 7);
    }

    // 7. Detect incomplete generation and inject warning
    const isComplete = cleaned.toLowerCase().includes('</html>') || cleaned.toLowerCase().includes('</body>');
    const hasStyle = cleaned.toLowerCase().includes('<style');
    const isStyleComplete = !hasStyle || cleaned.toLowerCase().includes('</style>');
    
    // If it's a very short string that isn't HTML, don't treat it as a document
    if (cleaned.length > 100 && (!isComplete || !isStyleComplete)) {
        const warning = `
            <div style="position:fixed; bottom:0; left:0; width:100%; background:#ef4444; color:white; padding:12px; z-index:99999; text-align:center; font-family:sans-serif; font-size:14px; font-weight:bold; box-shadow:0 -4px 10px rgba(0,0,0,0.3);">
                ⚠️ Warning: AI generation stopped prematurely. Output was truncated.
            </div>
        `;
        
        // Auto-close tags to prevent blank screens (e.g. if cut off inside <style>)
        if (hasStyle && !isStyleComplete) {
            cleaned += '\\n</style>';
        }
        if (!cleaned.toLowerCase().includes('</body>')) cleaned += '\\n</body>';
        if (!cleaned.toLowerCase().includes('</html>')) cleaned += '\\n</html>';

        if (cleaned.toLowerCase().includes('<body')) {
            cleaned = cleaned.replace(/(<body[^>]*>)/i, '$1' + warning);
        } else {
            cleaned = warning + cleaned;
        }
    }

    return cleaned;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function CopyButton({ text, size = 14 }) {
    const [copied, setCopied] = useState(false);
    const copy = () => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };
    return (
        <button type="button" onClick={copy} title="Copy to clipboard" style={{
            background: 'none', border: '1px solid var(--glass-border)',
            borderRadius: '6px', padding: '4px 8px',
            display: 'flex', alignItems: 'center', gap: '4px',
            color: copied ? '#56d364' : 'var(--text-muted)', fontSize: '0.75rem',
            transition: 'var(--transition)'
        }}>
            {copied ? <Check size={size} /> : <Copy size={size} />}
            {copied ? 'Copied' : 'Copy'}
        </button>
    );
}

const MIME_MAP = {
    html: 'text/html',
    htm: 'text/html',
    css: 'text/css',
    js: 'text/javascript',
    jsx: 'text/javascript',
    ts: 'text/typescript',
    tsx: 'text/typescript',
    py: 'text/x-python',
    json: 'application/json',
    md: 'text/markdown',
    txt: 'text/plain',
    sh: 'text/x-sh',
    yaml: 'text/yaml',
    yml: 'text/yaml',
};

function getMime(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    return MIME_MAP[ext] || 'text/plain';
}

function DownloadButton({ text, filename }) {
    const download = () => {
        if (!text) return;
        const mime = getMime(filename);
        const blob = new Blob([text], { type: mime });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };
    return (
        <button type="button" onClick={download} title={`Download as ${filename}`} style={{
            background: 'none', border: '1px solid var(--glass-border)',
            borderRadius: '6px', padding: '4px 8px',
            display: 'flex', alignItems: 'center', gap: '4px',
            color: 'var(--text-muted)', fontSize: '0.75rem',
            transition: 'var(--transition)'
        }}
            onMouseEnter={e => { e.currentTarget.style.color = '#a5b4fc'; e.currentTarget.style.borderColor = 'rgba(99,102,241,0.4)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.borderColor = 'var(--glass-border)'; }}
        >
            ⬇ {filename}
        </button>
    );
}

function FileTree({ files, selected, onSelect }) {
    if (!files) return null;
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {Object.keys(files).map(path => (
                <button type="button" key={path} onClick={() => onSelect(path)} style={{
                    textAlign: 'left', background: selected === path ? 'rgba(99,102,241,0.15)' : 'none',
                    border: 'none', borderRadius: '6px', padding: '6px 10px',
                    color: selected === path ? '#a5b4fc' : 'var(--text-secondary)',
                    fontSize: '0.78rem', fontFamily: 'monospace', transition: 'var(--transition)',
                    display: 'flex', alignItems: 'center', gap: '6px'
                }}>
                    <FileCode size={12} /> {path}
                </button>
            ))}
        </div>
    );
}

// ─── Live streaming code display ──────────────────────────────────────────────

function StreamingView({ buffer, isStreaming, type }) {
    const codeRef = useRef(null);
    useEffect(() => {
        if (codeRef.current) {
            codeRef.current.scrollTop = codeRef.current.scrollHeight;
        }
    }, [buffer]);

    const lines = buffer.split('\n').length;
    const chars = buffer.length;

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Status bar */}
            <div style={{
                display: 'flex', alignItems: 'center', gap: '12px', padding: '8px 14px',
                background: 'rgba(0,0,0,0.3)', borderBottom: '1px solid var(--glass-border)',
                flexShrink: 0
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div className={isStreaming ? 'animate-pulse' : ''} style={{
                        width: '7px', height: '7px', borderRadius: '50%',
                        background: isStreaming ? '#56d364' : '#a5b4fc'
                    }} />
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {isStreaming ? 'Claude is writing...' : 'Generation complete'}
                    </span>
                </div>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '14px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    <span>{lines.toLocaleString()} lines</span>
                    <span>{chars.toLocaleString()} chars</span>
                </div>
                {!isStreaming && buffer && <CopyButton text={buffer} />}
            </div>

            {/* Code area */}
            <div ref={codeRef} style={{
                flex: 1, overflowY: 'auto', padding: '16px',
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: '0.78rem', lineHeight: 1.7, color: '#e2e8f0',
                background: '#0d1117', position: 'relative'
            }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {buffer}
                    {isStreaming && (
                        <span style={{
                            display: 'inline-block', width: '2px', height: '1em',
                            background: '#a5b4fc', marginLeft: '1px',
                            animation: 'pulse-glow 0.8s ease-in-out infinite'
                        }} />
                    )}
                </pre>
            </div>
        </div>
    );
}

// ─── Preview Iframe ─────────────────────────────────────────────────────────

function PreviewIframe({ html, previewKey }) {
    const iframeRef = useRef(null);

    useEffect(() => {
        const iframe = iframeRef.current;
        if (!iframe || !html) return;

        // Add error logging script
        const errorScript = `
            <script>
                window.onerror = function(msg, url, line) {
                    console.error("Preview Error:", msg, url, line);
                    const errDiv = document.createElement('div');
                    errDiv.style.cssText = 'position:fixed;top:0;left:0;width:100%;background:rgba(220,38,38,0.9);color:white;padding:12px;z-index:99999;font-family:sans-serif;font-size:14px;box-shadow:0 4px 6px rgba(0,0,0,0.3);';
                    errDiv.innerHTML = '<strong>Preview Error:</strong> ' + msg + ' (Line: ' + line + ')<br/><span style="font-size:11px;opacity:0.8;">Check browser console for more details.</span>';
                    
                    const closeBtn = document.createElement('button');
                    closeBtn.innerHTML = '✕';
                    closeBtn.style.cssText = 'position:absolute;top:8px;right:12px;background:none;border:none;color:white;cursor:pointer;font-size:16px;';
                    closeBtn.onclick = () => errDiv.remove();
                    
                    errDiv.appendChild(closeBtn);
                    document.body.appendChild(errDiv);
                };
                
                // Polyfill for React/Babel errors that are logged but don't trigger window.onerror
                const originalConsoleError = console.error;
                console.error = function() {
                    const args = Array.from(arguments);
                    originalConsoleError.apply(console, args);
                    if (args[0] && typeof args[0] === 'string' && (args[0].includes('React') || args[0].includes('Babel') || args[0].includes('SyntaxError'))) {
                        window.onerror(args.join(' '), window.location.href, 'Unknown');
                    }
                };
            </script>
        `;

        let finalHtml = html;
        // Inject error script right after <head> or at the beginning
        if (finalHtml.includes('<head>')) {
            finalHtml = finalHtml.replace('<head>', '<head>' + errorScript);
        } else if (finalHtml.includes('<html>')) {
            finalHtml = finalHtml.replace('<html>', '<html>' + errorScript);
        } else {
            finalHtml = errorScript + finalHtml;
        }

        const doc = iframe.contentWindow?.document || iframe.contentDocument;
        if (doc) {
            doc.open();
            doc.write(finalHtml);
            doc.close();
        }
    }, [html, previewKey]);

    return (
        <iframe
            ref={iframeRef}
            title="Live Preview"
            style={{ width: '100%', height: '100%', border: 'none', background: '#0d1117' }}
            sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"
        />
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────

const Generate = () => {
    const [prompt, setPrompt] = useState('');
    const [type, setType] = useState('website');
    const [loading, setLoading] = useState(false);
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamBuffer, setStreamBuffer] = useState('');
    const [output, setOutput] = useState(null);
    const [previewHtml, setPreviewHtml] = useState(null); // explicit preview HTML for fullstack
    const [backendFiles, setBackendFiles] = useState(null); // Groq backend code for fullstack
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState('preview');
    const [selectedFile, setSelectedFile] = useState(null);
    const [refineMessages, setRefineMessages] = useState([]);
    const [refineInput, setRefineInput] = useState('');
    const [refining, setRefining] = useState(false);
    const [refineStreaming, setRefineStreaming] = useState(false);
    const [liveEdit, setLiveEdit] = useState(false);
    const [fullscreen, setFullscreen] = useState(false);
    const [previewKey, setPreviewKey] = useState(0); // stable key for iframe remounting

    const abortRef = useRef(null);
    const textareaRef = useRef(null);
    const chatEndRef = useRef(null);
    const iframeRef = useRef(null);

    // ── engine: 'claude' | 'groq-fallback' | 'groq' | null (loading)
    const [engine, setEngine] = useState(null);



    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) return;
        fetch(`${API_BASE}/generate/status`, { headers: { Authorization: `Bearer ${token}` } })
            .then(r => r.json())
            .then(d => setEngine(d.engine ?? (d.claude_available ? 'claude' : 'groq')))
            .catch(() => setEngine('groq'));
    }, []);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [refineMessages]);

    // Escape exits fullscreen
    useEffect(() => {
        const onKey = (e) => { if (e.key === 'Escape') setFullscreen(false); };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, []);

    // Lock body scroll when fullscreen is active
    useEffect(() => {
        if (fullscreen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => { document.body.style.overflow = ''; };
    }, [fullscreen]);

    // Resize state for output panel
    const [panelHeight, setPanelHeight] = useState(500);
    const resizingRef = useRef(false);

    const handleResizeMouseDown = useCallback((e) => {
        e.preventDefault();
        resizingRef.current = true;
        const startY = e.clientY;
        const startH = panelHeight;
        const onMove = (ev) => {
            if (!resizingRef.current) return;
            const delta = ev.clientY - startY;
            setPanelHeight(Math.max(300, startH + delta));
        };
        const onUp = () => {
            resizingRef.current = false;
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    }, [panelHeight]);

    const parsed = output ? parseOutput(output, type) : null;
    const hasOutput = !!output;

    // ─── Streaming generation ────────────────────────────────────────────────

    const handleGenerate = async (e) => {
        e?.preventDefault();
        if (!prompt.trim() || loading || isStreaming) return;

        const token = localStorage.getItem('token');
        if (!token) return;

        setError('');
        setOutput(null);
        setPreviewHtml(null);
        setBackendFiles(null);
        setStreamBuffer('');
        setRefineMessages([]);
        setActiveTab('stream');
        setIsStreaming(true);
        setLoading(true);
        setPreviewKey(k => k + 1); // bump key so preview iframe is fresh

        const controller = new AbortController();
        abortRef.current = controller;

        try {
            const res = await fetch(`${API_BASE}/generate/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({ prompt, type }),
                signal: controller.signal,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
                throw new Error(err.detail || 'Generation failed');
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let accumulated = '';
            let sseBuffer = ''; // buffer across network chunks

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                sseBuffer += decoder.decode(value, { stream: true });
                const lines = sseBuffer.split('\n');
                // Keep the last (potentially incomplete) line in the buffer
                sseBuffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') break;
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.error) { setError(parsed.error); break; }

                        // Website / fullstack-frontend: token-by-token streaming
                        if (parsed.chunk) {
                            accumulated += parsed.chunk;
                            setStreamBuffer(accumulated);
                        }

                        // Backend-only: full payload delivered at once
                        if (parsed.payload) {
                            accumulated = parsed.payload;
                            setStreamBuffer(accumulated);
                            setOutput(parsed.payload);
                            setActiveTab('code');
                        }

                        // Fullstack: Claude preview HTML for iframe
                        if (parsed.preview) {
                            const cleanHtml = stripHtmlPreamble(parsed.preview);
                            setPreviewHtml(cleanHtml);
                            setOutput(cleanHtml); // so hasOutput becomes true
                            setActiveTab('preview');
                        }

                        // Fullstack: Groq backend code arriving after frontend stream
                        if (parsed.backend_payload) {
                            try {
                                const bf = JSON.parse(parsed.backend_payload);
                                setBackendFiles(bf);
                            } catch {
                                setBackendFiles({ 'backend.txt': parsed.backend_payload });
                            }
                        }
                    } catch { /* skip malformed SSE */ }
                }
            }

            // Stream done — switch to preview for website/fullstack
            if (accumulated && (type === 'website')) {
                setOutput(stripHtmlPreamble(accumulated));
                setActiveTab('preview');
            }

        } catch (err) {
            if (err.name !== 'AbortError') {
                setError(err.message || 'Unexpected error during generation');
                setActiveTab('stream');
            }
        } finally {
            setIsStreaming(false);
            setLoading(false);
            abortRef.current = null;
        }
    };

    const handleCancel = () => {
        abortRef.current?.abort();
        setIsStreaming(false);
        setLoading(false);
    };

    // ─── Streaming refine ────────────────────────────────────────────────────

    const handleRefine = async () => {
        if (!refineInput.trim() || refining || !output) return;

        const token = localStorage.getItem('token');
        if (!token) return;

        const userMsg = refineInput.trim();
        setRefineInput('');
        setRefineMessages(prev => [...prev, { role: 'user', text: userMsg }]);
        setRefining(true);
        setRefineStreaming(true);

        // Add bot placeholder
        setRefineMessages(prev => [...prev, { role: 'assistant', text: '', streaming: true }]);

        const controller = new AbortController();

        try {
            const currentCode = parsed?.html || output;
            const res = await fetch(`${API_BASE}/generate/refine-stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ prompt: userMsg, current_code: currentCode }),
                signal: controller.signal,
            });

            if (!res.ok) throw new Error('Refine failed');

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let accumulated = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const raw = decoder.decode(value, { stream: true });
                for (const line of raw.split('\n')) {
                    if (!line.startsWith('data: ')) continue;
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') break;
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.chunk) {
                            accumulated += parsed.chunk;
                            setRefineMessages(prev => {
                                const msgs = [...prev];
                                msgs[msgs.length - 1] = { role: 'assistant', text: accumulated, streaming: true };
                                return msgs;
                            });
                        }
                    } catch { }
                }
            }

            // Finalise
            setRefineMessages(prev => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = { role: 'assistant', text: `✅ Done! Applied "${userMsg}"`, streaming: false };
                return msgs;
            });
            setOutput(stripHtmlPreamble(accumulated));
            setPreviewKey(k => k + 1);
            setActiveTab('preview');

        } catch (err) {
            setRefineMessages(prev => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = { role: 'assistant', text: '❌ Refine failed. Try again.', streaming: false };
                return msgs;
            });
        } finally {
            setRefining(false);
            setRefineStreaming(false);
        }
    };

    const TABS = [
        { id: 'stream', label: 'Live Output', icon: Terminal, show: true },
        { id: 'preview', label: 'Preview', icon: Eye, show: hasOutput && (type === 'website' || type === 'fullstack') },
        { id: 'code', label: type === 'fullstack' ? 'Frontend HTML' : 'Code', icon: Code2, show: hasOutput },
        { id: 'backend-code', label: 'Backend Code', icon: Server, show: type === 'fullstack' && !!backendFiles },
        { id: 'refine', label: 'Refine', icon: MessageSquare, show: hasOutput },
    ].filter(t => t.show);

    const activeTabFiles = parsed?.files;

    // ─── Keyboard shortcuts ──────────────────────────────────────────────────

    const handleKeyDown = (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            e.preventDefault();
            handleGenerate();
        }
    };

    return (
        <div className="generate-page animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>

            {/* ── TOP BAR ── */}
            <div className="topbar">
                <div className="topbar-pill"><Sparkles className="pill-icon" /> AI Code Generator</div>
                <div className="topbar-divider"></div>
                {engine === 'claude' && <div className="topbar-pill featured"><Activity className="pill-icon" /> Claude Opus Streaming</div>}
                {(engine === 'groq-fallback' || engine === 'groq') && <div className="topbar-pill"><Zap className="pill-icon" /> Groq Fast Streaming</div>}
            </div>

            {/* ── CONTENT AREA ── */}
            <div className="content" style={{ display: 'flex', flexDirection: 'column' }}>

                {/* Hero */}
                <h1 className="hero-headline">Build anything with a <span className="accent">single prompt</span></h1>
                <p className="hero-sub">Describe what you want — AI generates real code in real time.</p>

                {/* Mode Tabs */}
                <div className="mode-tabs">
                    {TYPES.map(t => {
                        const Icon = t.icon;
                        const active = type === t.id;
                        return (
                            <div key={t.id} className={`mode-tab ${active ? 'active' : ''}`} onClick={() => setType(t.id)}>
                                <Icon className="tab-icon" color={active ? 'var(--p2)' : 'var(--muted)'} />
                                <div className="tab-main">
                                    <span className="tab-name">{t.label}</span>
                                    <span className="tab-desc" style={{ display: window.innerWidth < 600 ? 'none' : 'inline' }}>{t.desc}</span>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Prompt Box */}
                <form onSubmit={handleGenerate} className="prompt-wrapper">
                    <textarea
                        ref={textareaRef}
                        className="prompt-box"
                        value={prompt}
                        onChange={e => setPrompt(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={`Describe your ${TYPES.find(t => t.id === type)?.label.toLowerCase()}...`}
                        disabled={isStreaming}
                    />
                    <div className="prompt-footer">
                        <div className="prompt-hint">
                            <span className="kbd">⌘</span> <span className="kbd">Enter</span>
                            <span>to generate</span>
                        </div>
                        {error && <div style={{ color: '#f87171', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}><X size={14} /> {error}</div>}
                        <div style={{ display: 'flex', gap: '8px' }}>
                            {isStreaming ? (
                                <button type="button" onClick={handleCancel} className="generate-btn" style={{ background: 'rgba(248,113,113,0.1)', color: '#f87171', boxShadow: 'none' }}>
                                    <StopCircle size={15} /> Stop
                                </button>
                            ) : (
                                <button type="submit" className="generate-btn" disabled={!prompt.trim()}>
                                    <Sparkles size={15} /> Generate
                                </button>
                            )}
                        </div>
                    </div>
                </form>

                {/* Example Chips & Recent (Shown only when not generating/outputting) */}
                {!hasOutput && !isStreaming && (
                    <>
                        <div className="chips-label">Inspirations</div>
                        <div className="chips-grid">
                            {EXAMPLES.map(ex => (
                                <div key={ex.text} className="builder-chip" onClick={() => { setPrompt(ex.text); textareaRef.current?.focus(); }}>
                                    <span className="chip-icon">{ex.emoji}</span> {ex.text}
                                </div>
                            ))}
                        </div>

                        <div className="section-divider"><span>Recent Builds</span></div>
                        <div className="recent-grid">
                            {[
                                { e: '⚡', n: 'SaaS Dashboard', t: 'Full Stack', d: '2 hrs ago' },
                                { e: '🛍️', n: 'E-commerce API', t: 'Backend', d: '5 hrs ago' },
                                { e: '🎨', n: 'Portfolio Site', t: 'Website', d: '1 day ago' }
                            ].map((p, i) => (
                                <div key={i} className="project-card">
                                    <div className="project-emoji">{p.e}</div>
                                    <div className="project-name">{p.n}</div>
                                    <div className="project-type">{p.t}</div>
                                    <div className="project-time">{p.d}</div>
                                </div>
                            ))}
                        </div>
                    </>
                )}

                {/* ── Bottom: Output panel ──────────────────────────────────────────── */}
                {(isStreaming || hasOutput) && (() => {
                    const panelContent = (
                    <div style={{
                        display: 'flex', flexDirection: 'column',
                        ...(fullscreen ? {
                            position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: 9999,
                            background: 'var(--bg)', borderRadius: 0, margin: 0,
                        } : {
                            flex: 1, minHeight: `${panelHeight}px`, height: `${panelHeight}px`,
                            marginTop: '20px', borderRadius: '16px',
                            background: 'var(--bg2)', border: '1px solid var(--border)',
                            boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
                        }),
                        overflow: 'hidden',
                    }}>
                        {/* Resize handle (top edge, non-fullscreen only) */}
                        {!fullscreen && (
                            <div onMouseDown={handleResizeMouseDown} style={{
                                height: '6px', cursor: 'ns-resize', flexShrink: 0,
                                background: 'transparent', position: 'relative', zIndex: 5,
                            }}>
                                <div style={{
                                    position: 'absolute', left: '50%', top: '2px', transform: 'translateX(-50%)',
                                    width: '40px', height: '3px', borderRadius: '2px',
                                    background: 'rgba(255,255,255,0.12)',
                                }} />
                            </div>
                        )}
                        {/* Tab bar */}
                        <div style={{
                            display: 'flex', alignItems: 'center', gap: '2px',
                            borderBottom: '1px solid var(--glass-border)', padding: '6px 10px 0',
                            flexShrink: 0, overflowX: 'auto',
                            background: fullscreen ? 'var(--bg)' : 'var(--bg2)',
                            zIndex: 10,
                        }}>
                            {TABS.map(tab => {
                                const Icon = tab.icon;
                                const active = activeTab === tab.id;
                                return (
                                    <button type="button" key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                                        display: 'flex', alignItems: 'center', gap: '6px',
                                        padding: '7px 14px', borderRadius: '8px 8px 0 0', border: 'none',
                                        background: active ? 'rgba(99,102,241,0.12)' : 'none',
                                        borderBottom: active ? '2px solid #6366f1' : '2px solid transparent',
                                        color: active ? '#a5b4fc' : 'var(--text-muted)',
                                        fontSize: '0.8rem', fontWeight: active ? 600 : 400,
                                        fontFamily: 'var(--font-main)', transition: 'var(--transition)',
                                        whiteSpace: 'nowrap', cursor: 'pointer'
                                    }}>
                                        <Icon size={13} />
                                        {tab.label}
                                        {tab.id === 'stream' && isStreaming && (
                                            <span style={{
                                                width: '6px', height: '6px', borderRadius: '50%',
                                                background: '#56d364', animation: 'pulse-glow 1s infinite'
                                            }} />
                                        )}
                                    </button>
                                );
                            })}

                            <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px', paddingBottom: '6px', alignItems: 'center' }}>
                                {hasOutput && (
                                    <button type="button" onClick={handleGenerate} disabled={isStreaming} className="btn-secondary"
                                        style={{ padding: '5px 12px', fontSize: '0.75rem', gap: '5px', cursor: 'pointer' }}>
                                        <RefreshCw size={12} /> Regenerate
                                    </button>
                                )}
                                <button
                                    type="button"
                                    onClick={() => setFullscreen(f => !f)}
                                    title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
                                    style={{
                                        background: 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)',
                                        borderRadius: '7px', padding: '5px 7px',
                                        color: 'var(--text-muted)', display: 'flex', alignItems: 'center',
                                        transition: 'all 0.2s', cursor: 'pointer'
                                    }}
                                    onMouseEnter={e => { e.currentTarget.style.color = '#a5b4fc'; e.currentTarget.style.borderColor = 'rgba(99,102,241,0.4)'; }}
                                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.borderColor = 'var(--glass-border)'; }}
                                >
                                    {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                                </button>
                            </div>
                        </div>

                        {/* Tab content */}
                        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>

                            {/* ── LIVE STREAM TAB ──────────────────────────────────────── */}
                            {activeTab === 'stream' && (
                                <StreamingView buffer={streamBuffer} isStreaming={isStreaming} type={type} />
                            )}

                            {/* ── PREVIEW TAB ──────────────────────────────────────────── */}
                            {activeTab === 'preview' && (previewHtml || parsed?.html) && (
                                <div style={{ height: '100%', position: 'relative' }}>
                                    {isStreaming ? (
                                        <div style={{
                                            height: '100%', display: 'flex', flexDirection: 'column',
                                            alignItems: 'center', justifyContent: 'center', gap: '16px',
                                            color: 'var(--text-muted)', background: '#0d1117'
                                        }}>
                                            <Loader2 size={32} className="animate-spin" style={{ color: '#6366f1' }} />
                                            <p style={{ fontSize: '0.9rem' }}>Generating preview...</p>
                                            <p style={{ fontSize: '0.75rem', opacity: 0.6 }}>Preview will appear when streaming is complete</p>
                                        </div>
                                    ) : (
                                        <PreviewIframe html={stripHtmlPreamble(previewHtml || parsed.html)} previewKey={previewKey} />
                                    )}
                                </div>
                            )}
                            {activeTab === 'preview' && !previewHtml && !parsed?.html && hasOutput && (
                                <div style={{
                                    height: '100%', display: 'flex', flexDirection: 'column',
                                    alignItems: 'center', justifyContent: 'center', gap: '12px',
                                    color: 'var(--text-muted)'
                                }}>
                                    <Eye size={32} style={{ opacity: 0.3 }} />
                                    <p style={{ fontSize: '0.85rem' }}>No preview available for this output type.</p>
                                    <button type="button" onClick={() => setActiveTab('code')} className="btn-secondary"
                                        style={{ padding: '7px 16px', fontSize: '0.8rem', gap: '6px' }}>
                                        <Code2 size={13} /> View Code
                                    </button>
                                </div>
                            )}

                            {/* ── CODE TAB ──────────────────────────────────────────────────── */}
                            {activeTab === 'code' && (
                                <div style={{ height: '100%', display: 'flex', overflow: 'hidden' }}>
                                    {activeTabFiles && (
                                        <div style={{
                                            width: '200px', flexShrink: 0, borderRight: '1px solid var(--glass-border)',
                                            padding: '12px 8px', overflowY: 'auto', background: 'rgba(0,0,0,0.2)'
                                        }}>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '8px', padding: '0 4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                                                Files
                                            </div>
                                            <FileTree
                                                files={activeTabFiles}
                                                selected={selectedFile}
                                                onSelect={setSelectedFile}
                                            />
                                        </div>
                                    )}
                                    <div style={{ flex: 1, overflow: 'auto', position: 'relative' }}>
                                        <div style={{ position: 'absolute', top: '10px', right: '12px', zIndex: 2, display: 'flex', gap: '6px' }}>
                                            <CopyButton text={
                                                type === 'fullstack'
                                                    ? (previewHtml || output || '')
                                                    : (selectedFile ? activeTabFiles?.[selectedFile] : (parsed?.html || output))
                                            } />
                                            {type === 'fullstack' && (previewHtml || output) && (
                                                <DownloadButton
                                                    text={previewHtml || output}
                                                    filename="app.html"
                                                />
                                            )}
                                            {type === 'website' && parsed?.html && (
                                                <DownloadButton
                                                    text={parsed.html}
                                                    filename="index.html"
                                                />
                                            )}
                                        </div>
                                        <pre style={{
                                            margin: 0, padding: '16px', height: '100%', overflow: 'auto',
                                            fontFamily: 'monospace', fontSize: '0.78rem', lineHeight: 1.7,
                                            color: '#e2e8f0', background: '#0d1117',
                                            whiteSpace: 'pre-wrap', wordBreak: 'break-word'
                                        }}>
                                            {type === 'fullstack'
                                                ? (previewHtml || output || '// Generating...')
                                                : selectedFile
                                                    ? activeTabFiles?.[selectedFile]
                                                    : (parsed?.html || JSON.stringify(output, null, 2))}
                                        </pre>
                                    </div>
                                </div>
                            )}

                            {/* ── BACKEND CODE TAB ───────────────────────────────────────── */}
                            {activeTab === 'backend-code' && backendFiles && (
                                <div style={{ height: '100%', display: 'flex', overflow: 'hidden' }}>
                                    <div style={{
                                        width: '220px', flexShrink: 0, borderRight: '1px solid var(--glass-border)',
                                        padding: '12px 8px', overflowY: 'auto', background: 'rgba(0,0,0,0.2)'
                                    }}>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '8px', padding: '0 4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                                            Backend Files (Groq)
                                        </div>
                                        <FileTree files={backendFiles} selected={selectedFile} onSelect={setSelectedFile} />
                                    </div>
                                    <div style={{ flex: 1, overflow: 'auto', position: 'relative' }}>
                                        <div style={{ position: 'absolute', top: '10px', right: '12px', zIndex: 2, display: 'flex', gap: '6px' }}>
                                            <CopyButton text={selectedFile ? backendFiles[selectedFile] : ''} />
                                            {selectedFile && backendFiles[selectedFile] && (
                                                <DownloadButton
                                                    text={backendFiles[selectedFile]}
                                                    filename={selectedFile.split('/').pop()}
                                                />
                                            )}
                                        </div>
                                        <pre style={{
                                            flex: 1, margin: 0, padding: '16px', height: '100%',
                                            fontFamily: 'monospace', fontSize: '0.78rem', lineHeight: 1.7,
                                            color: '#e2e8f0', background: '#0d1117', overflow: 'auto',
                                            whiteSpace: 'pre-wrap', wordBreak: 'break-word'
                                        }}>
                                            {selectedFile ? backendFiles[selectedFile] : '← Select a file to view'}
                                        </pre>
                                    </div>
                                </div>
                            )}

                            {/* ── REFINE TAB ───────────────────────────────────────────── */}
                            {activeTab === 'refine' && (
                                <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                                    {/* Messages */}
                                    <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                        {refineMessages.length === 0 && (
                                            <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                                                <MessageSquare size={28} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
                                                <p style={{ fontSize: '0.85rem' }}>Ask Claude to refine your {type}.</p>
                                                <p style={{ fontSize: '0.78rem', marginTop: '4px', opacity: 0.6 }}>
                                                    "Add a dark mode toggle" · "Make the hero bigger" · "Add animations"
                                                </p>
                                            </div>
                                        )}
                                        {refineMessages.map((msg, i) => (
                                            <div key={i} style={{
                                                display: 'flex', gap: '10px', alignItems: 'flex-start',
                                                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
                                            }}>
                                                <div style={{
                                                    width: '28px', height: '28px', borderRadius: '8px', flexShrink: 0,
                                                    background: msg.role === 'user' ? 'rgba(99,102,241,0.2)' : 'rgba(139,92,246,0.2)',
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                                                }}>
                                                    {msg.role === 'user' ? <UserIcon size={14} color="#a5b4fc" /> : <Bot size={14} color="#a78bfa" />}
                                                </div>
                                                <div style={{
                                                    maxWidth: '75%', padding: '10px 14px', borderRadius: '12px',
                                                    background: msg.role === 'user' ? 'rgba(99,102,241,0.12)' : 'rgba(255,255,255,0.04)',
                                                    border: '1px solid var(--glass-border)', fontSize: '0.85rem', lineHeight: 1.6
                                                }}>
                                                    {msg.streaming && msg.text.length > 100
                                                        ? msg.text.slice(-300) + '…'
                                                        : msg.text || <Loader2 size={14} className="animate-spin" />}
                                                    {msg.streaming && (
                                                        <span style={{ display: 'inline-block', width: '2px', height: '0.9em', background: '#a5b4fc', marginLeft: '2px', animation: 'pulse-glow 0.7s infinite' }} />
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                        <div ref={chatEndRef} />
                                    </div>

                                    {/* Refine input */}
                                    <div style={{ padding: '12px', borderTop: '1px solid var(--glass-border)', display: 'flex', gap: '8px' }}>
                                        <input
                                            id="refine-input"
                                            type="text"
                                            className="input-field"
                                            placeholder='e.g. "Add a dark mode toggle" or "Make the CTA bigger"'
                                            value={refineInput}
                                            onChange={e => setRefineInput(e.target.value)}
                                            onKeyDown={e => e.key === 'Enter' && handleRefine()}
                                            disabled={refining}
                                            style={{ flex: 1, fontSize: '0.85rem', padding: '9px 14px' }}
                                        />
                                        <button
                                            onClick={handleRefine}
                                            disabled={refining || !refineInput.trim()}
                                            className="btn-primary"
                                            style={{ padding: '9px 16px', gap: '6px', fontSize: '0.85rem' }}
                                        >
                                            {refining ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                    );
                    return fullscreen ? createPortal(panelContent, document.body) : panelContent;
                })()}
            </div>
        </div>
    );
};

export default Generate;
