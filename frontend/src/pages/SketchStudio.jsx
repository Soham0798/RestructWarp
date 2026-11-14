import { useCallback, useEffect, useRef, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import {
    PenTool, Upload, Camera, Eye, Code2, Braces, GitBranch, ShieldCheck, Smartphone,
    Download, Monitor, Tablet, Plus, Loader2, Save, Layers, Link2, LayoutGrid, Check, X, RefreshCw
} from 'lucide-react';
import { API_BASE } from '../config';
import { CopyButton } from '../components/GenerationUtils';

// Sketch Studio (merged from Sketch2UI): a photo of a hand-drawn UI becomes pages you can
// preview, edit as JSON, export as HTML / React / full stack, and open on a phone.

const TABS = [
    { id: 'preview', label: 'Preview', icon: Eye },
    { id: 'code', label: 'Code', icon: Code2 },
    { id: 'json', label: 'JSON', icon: Braces },
    { id: 'flow', label: 'Flow map', icon: GitBranch },
    { id: 'a11y', label: 'Accessibility', icon: ShieldCheck },
    { id: 'phone', label: 'Phone', icon: Smartphone },
];
const DEVICES = [
    { id: 'desktop', width: '100%', label: 'Desktop', icon: Monitor },
    { id: 'tablet', width: '768px', label: 'Tablet', icon: Tablet },
    { id: 'phone', width: '390px', label: 'Phone', icon: Smartphone },
];
const EXPORTS = [['html', 'HTML'], ['react', 'React'], ['fullstack', 'Full stack']];
const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
const MAX_BYTES = 10 * 1024 * 1024;
const ANALYZING = 'Reading your sketch…';

const panel = {
    background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: '16px',
};
const label = {
    fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase',
    color: 'var(--text-secondary)',
};

async function request(path, { method = 'GET', json, form, raw } = {}) {
    const headers = { Authorization: `Bearer ${localStorage.getItem('token')}` };
    let body;
    if (json !== undefined) {
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify(json);
    } else if (form) {
        body = form;
    }
    let res;
    try {
        res = await fetch(API_BASE + path, { method, headers, body });
    } catch {
        throw new Error("Can't reach the server. Is the backend running?");
    }
    if (!res.ok) {
        const detail = (await res.json().catch(() => ({}))).detail;
        const msg = Array.isArray(detail) ? detail.map(d => d.msg).join('; ') : detail;
        throw new Error(msg || `Request failed (${res.status})`);
    }
    if (raw) return res;
    return res.status === 204 ? null : res.json();
}

// A srcDoc page has no URL of its own, so href="about.html" goes nowhere. This script hands
// page links to the Studio (which swaps the page) and stops form posts.
const PREVIEW_NAV = `<script>
window.__sketch2uiGo = (href) => parent.postMessage({ sketch2uiNav: href }, "*");
document.addEventListener("click", (e) => {
  const a = e.target.closest("a[href]");
  if (!a) return;
  e.preventDefault();
  parent.postMessage({ sketch2uiNav: a.getAttribute("href") }, "*");
});
document.addEventListener("submit", (e) => e.preventDefault());
</script>`;
const withNav = (html) => (html || '').replace('</body>', `${PREVIEW_NAV}\n</body>`);

const countComponents = (doc) => {
    let n = 0;
    const walk = (c) => { n += 1; (c.children || []).forEach(walk); };
    doc.screens.forEach(s => (s.root.children || []).forEach(walk));
    return n;
};

// Draws each screen as a card and each drawn arrow as a link between them
function FlowMap({ doc }) {
    const W = 150, H = 96, GAP = 70;
    const screens = doc.screens;
    const x = (i) => 20 + i * (W + GAP);
    const index = Object.fromEntries(screens.map((s, i) => [s.id, i]));
    const width = x(screens.length - 1) + W + 20;
    const textOf = (screen, compId) => {
        const stack = [screen.root];
        while (stack.length) {
            const c = stack.pop();
            if (c.id === compId) return c.props?.text || c.type;
            stack.push(...(c.children || []));
        }
        return compId;
    };
    return (
        <div style={{ ...panel, padding: '16px', overflowX: 'auto' }}>
            <svg viewBox={`0 0 ${width} ${H + 80}`} width={Math.max(width, 320)} role="img"
                aria-label={`Flow of ${screens.length} screens and ${doc.links.length} links`}>
                <defs>
                    <marker id="flow-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
                        <path d="M0,0 L10,5 L0,10 z" fill="#c084fc" />
                    </marker>
                </defs>
                {doc.links.map((l, k) => {
                    const a = index[l.fromScreen], b = index[l.toScreen];
                    const forward = b > a;
                    const y = forward ? 40 + (k % 3) * 18 : H + 40;
                    const x1 = forward ? x(a) + W : x(a) + W / 2, x2 = forward ? x(b) : x(b) + W / 2;
                    const d = forward ? `M${x1},${y} C${x1 + 30},${y} ${x2 - 30},${y} ${x2},${y}`
                        : `M${x1},${H + 20} C${x1},${H + 70} ${x2},${H + 70} ${x2},${H + 22}`;
                    return (
                        <g key={k}>
                            <path d={d} fill="none" stroke="#c084fc" strokeWidth="2" markerEnd="url(#flow-head)" />
                            <text x={(x1 + x2) / 2} y={forward ? y - 6 : H + 66} textAnchor="middle" fontSize="11" fill="rgba(240,238,255,0.6)">
                                {textOf(screens[a], l.fromComponent)}
                            </text>
                        </g>
                    );
                })}
                {screens.map((s, i) => (
                    <g key={s.id}>
                        <rect x={x(i)} y="20" width={W} height={H} rx="12" fill="#13111f" stroke="rgba(240,238,255,0.5)" strokeWidth="1.5" />
                        <text x={x(i) + W / 2} y={20 + H / 2 + 5} textAnchor="middle" fontSize="14" fill="#f0eeff">{s.name}</text>
                    </g>
                ))}
            </svg>
            {doc.links.length === 0 && (
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '8px 4px 0' }}>
                    No arrows found. Draw an arrow from a button to another screen to link them.
                </p>
            )}
        </div>
    );
}

function UploadBox({ onFile, busy }) {
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [error, setError] = useState('');
    const [dragging, setDragging] = useState(false);
    const inputRef = useRef(null);

    const choose = (f) => {
        if (!f) return;
        if (!ALLOWED_TYPES.includes(f.type)) return setError('Use a PNG, JPG or WEBP image.');
        if (f.size > MAX_BYTES) return setError('That image is over 10 MB.');
        setError('');
        setFile(f);
        setPreview(URL.createObjectURL(f));
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div
                role="button" tabIndex={0}
                onClick={() => inputRef.current?.click()}
                onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
                onDragOver={e => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={e => { e.preventDefault(); setDragging(false); choose(e.dataTransfer.files[0]); }}
                style={{
                    minHeight: '190px', display: 'grid', placeItems: 'center', textAlign: 'center',
                    padding: '14px', borderRadius: '14px', cursor: 'pointer', transition: 'var(--transition)',
                    border: `2px dashed ${dragging ? 'var(--p2)' : 'var(--border-hi)'}`,
                    background: dragging ? 'rgba(149,76,255,0.1)' : 'rgba(255,255,255,0.02)',
                }}
            >
                <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" hidden
                    aria-label="Choose a sketch image" onChange={e => choose(e.target.files[0])} />
                {preview ? (
                    <img src={preview} alt="Your sketch" style={{ maxHeight: '220px', maxWidth: '100%', borderRadius: '10px' }} />
                ) : (
                    <div>
                        <Upload size={26} color="var(--p2)" style={{ marginBottom: '8px' }} />
                        <p style={{ fontWeight: 600, marginBottom: '4px' }}>Drop your sketch here</p>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>or click to choose a photo (PNG, JPG, WEBP, up to 10 MB)</p>
                    </div>
                )}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
                <label className="btn-secondary" style={{ padding: '9px 12px', fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Camera size={14} /> Take photo
                    <input type="file" accept="image/*" capture="environment" hidden onChange={e => choose(e.target.files[0])} />
                </label>
                <button type="button" className="generate-btn" style={{ flex: 1, justifyContent: 'center', whiteSpace: 'nowrap', padding: '9px 10px' }}
                    disabled={!file || busy} onClick={() => onFile(file)}>
                    <PenTool size={14} /> {busy ? 'Working…' : 'Turn into UI'}
                </button>
            </div>
            {error && <p role="alert" style={{ color: '#f87171', fontSize: '0.8rem' }}>{error}</p>}
        </div>
    );
}

const SketchStudio = () => {
    const [projects, setProjects] = useState([]);
    const [projectId, setProjectId] = useState(null);
    const [newName, setNewName] = useState('');
    const [sketchId, setSketchId] = useState(null);
    const [doc, setDoc] = useState(null);
    const [result, setResult] = useState(null); // generate response
    const [tab, setTab] = useState('preview');
    const [page, setPage] = useState('index.html');
    const [device, setDevice] = useState('desktop');
    const [jsonText, setJsonText] = useState('');
    const [busy, setBusy] = useState('');
    const [error, setError] = useState('');
    const [saved, setSaved] = useState(null); // history generation id

    const project = projects.find(p => p.id === projectId) || null;

    const loadProjects = useCallback(async () => {
        const list = await request('/projects');
        setProjects(list);
        setProjectId(id => (list.some(p => p.id === id) ? id : list[0]?.id ?? null));
        return list;
    }, []);

    useEffect(() => { loadProjects().catch(e => setError(e.message)); }, [loadProjects]);

    // links inside the preview iframe switch pages
    useEffect(() => {
        const onNav = (e) => {
            const href = e.data?.sketch2uiNav;
            if (href && result?.pages?.[href]) setPage(href);
        };
        window.addEventListener('message', onNav);
        return () => window.removeEventListener('message', onNav);
    }, [result]);

    const run = async (what, fn) => {
        setBusy(what);
        setError('');
        try { await fn(); } catch (e) { setError(e.message); } finally { setBusy(''); }
    };

    const show = (sid, document, generated) => {
        setSketchId(sid);
        setSaved(null);
        setDoc(document);
        setJsonText(JSON.stringify(document, null, 2));
        setResult(generated);
        setPage('index.html');
    };

    const createProject = (e) => {
        e.preventDefault();
        if (!newName.trim()) return;
        run('Creating project…', async () => {
            const created = await request('/projects', { method: 'POST', json: { name: newName.trim() } });
            setNewName('');
            await loadProjects();
            setProjectId(created.id);
            setDoc(null);
            setResult(null);
        });
    };

    const analyze = (file) => run(ANALYZING, async () => {
        let pid = projectId;
        if (!pid) { // first sketch: make a project for it
            pid = (await request('/projects', { method: 'POST', json: { name: 'My sketches' } })).id;
            setProjectId(pid);
        }
        const form = new FormData();
        form.append('project_id', pid);
        form.append('file', file);
        try {
            const out = await request('/sketch/analyze', { method: 'POST', form });
            show(out.sketch_id, out.document, await request(`/sketch/${out.sketch_id}/generate`, { method: 'POST' }));
            setTab('preview');
        } finally {
            await loadProjects(); // the list shows the new sketch, or that it failed
        }
    });

    const open = (sid) => run('Opening…', async () => {
        const document = await request(`/sketch/${sid}`);
        show(sid, document, await request(`/sketch/${sid}/generate`, { method: 'POST' }));
        await loadProjects(); // status is now "generated"
    });

    const saveJson = () => run('Saving…', async () => {
        let parsed;
        try { parsed = JSON.parse(jsonText); } catch { throw new Error('That JSON has a syntax error.'); }
        setDoc(await request(`/sketch/${sketchId}/json`, { method: 'PUT', json: parsed }));
        setResult(await request(`/sketch/${sketchId}/generate`, { method: 'POST' }));
    });

    const download = (target) => run('Preparing download…', async () => {
        const res = await request(`/sketch/${sketchId}/export?target=${target}`, { raw: true });
        const url = URL.createObjectURL(await res.blob());
        const a = Object.assign(document.createElement('a'), { href: url, download: `sketch-${sketchId}-${target}.zip` });
        a.click();
        URL.revokeObjectURL(url);
    });

    const redesign = () => run('Designing the pages again…', async () => {
        setResult(await request(`/sketch/${sketchId}/generate?fresh=true`, { method: 'POST' }));
        setSaved(null);
    });

    const saveToHistory = () => run('Saving to history…', async () => {
        const out = await request('/generate/import', {
            method: 'POST', json: { name: doc.name, html: result.pages['index.html'], document: doc },
        });
        setSaved(out.generation_id);
    });

    const pages = result ? Object.keys(result.pages) : [];
    // the backend builds the preview link from the address it sees; use the one this page talks to
    const phoneUrl = result?.preview_url.replace(/^https?:\/\/[^/]+/, API_BASE);
    const stats = doc ? [
        ['Screens', doc.screens.length, Layers],
        ['Components', countComponents(doc), LayoutGrid],
        ['Links', doc.links.length, Link2],
        ['Accessibility', result?.a11y_after != null ? `${result.a11y_after}/100` : '–', ShieldCheck],
    ] : [];

    return (
        <div className="animate-fade-in" style={{ padding: '48px 32px 40px', maxWidth: '1280px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
            <h1 className="hero-headline">Turn a <span className="accent">paper sketch</span> into working UI</h1>
            <p className="hero-sub">
                Photograph a hand-drawn screen. Draw arrows between screens to link them, and write notes like “blue” or “big” beside elements.
            </p>

            <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                {/* ── Left: project, upload, earlier sketches ── */}
                <aside style={{ flex: '0 0 300px', maxWidth: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <section style={{ ...panel, padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <h2 style={label}>Project</h2>
                        {projects.length > 0 && (
                            <select className="input-field" value={projectId ?? ''} aria-label="Project"
                                onChange={e => { setProjectId(Number(e.target.value)); setDoc(null); setResult(null); setSketchId(null); }}
                                style={{ padding: '9px 12px', fontSize: '0.85rem' }}>
                                {projects.map(p => <option key={p.id} value={p.id} style={{ background: '#13111f' }}>{p.name}</option>)}
                            </select>
                        )}
                        <form onSubmit={createProject} style={{ display: 'flex', gap: '8px' }}>
                            <input className="input-field" value={newName} onChange={e => setNewName(e.target.value)}
                                placeholder="New project name" aria-label="New project name" maxLength={120}
                                style={{ padding: '9px 12px', fontSize: '0.85rem', flex: 1, minWidth: 0 }} />
                            <button type="submit" className="btn-secondary" disabled={!newName.trim() || !!busy}
                                title="Create project" aria-label="Create project" style={{ padding: '9px 12px' }}>
                                <Plus size={14} />
                            </button>
                        </form>
                    </section>

                    <section style={{ ...panel, padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <h2 style={label}>New sketch</h2>
                        <UploadBox onFile={analyze} busy={!!busy} />
                    </section>

                    {project?.sketches.length > 0 && (
                        <section style={{ ...panel, padding: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <h2 style={label}>Earlier sketches</h2>
                            {project.sketches.map(s => {
                                const active = s.id === sketchId;
                                const unusable = s.status === 'failed' || s.status === 'uploaded';
                                return (
                                    <button type="button" key={s.id} disabled={unusable || !!busy} onClick={() => open(s.id)}
                                        style={{
                                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                            padding: '8px 12px', borderRadius: '10px', fontSize: '0.84rem', textAlign: 'left',
                                            border: '1px solid', borderColor: active ? 'var(--border-hi)' : 'transparent',
                                            background: active ? 'rgba(149,76,255,0.12)' : 'rgba(255,255,255,0.03)',
                                            color: 'var(--text)', opacity: unusable ? 0.5 : 1, cursor: unusable ? 'default' : 'pointer',
                                        }}>
                                        <span>Sketch #{s.id}</span>
                                        <span style={{
                                            fontSize: '0.7rem', padding: '2px 8px', borderRadius: '999px',
                                            color: s.status === 'generated' ? '#56d364' : s.status === 'failed' ? '#f87171' : '#c084fc',
                                            background: 'rgba(255,255,255,0.05)',
                                        }}>{s.status}</span>
                                    </button>
                                );
                            })}
                        </section>
                    )}
                </aside>

                {/* ── Right: result ── */}
                <section style={{ flex: '1 1 520px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {busy && (
                        <p role="status" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.88rem', color: '#c084fc' }}>
                            <Loader2 size={16} className="animate-spin" />
                            {busy === ANALYZING ? 'Reading your sketch and designing the pages… this can take a minute or two.' : busy}
                        </p>
                    )}
                    {saved && (
                        <p role="status" style={{ ...panel, padding: '10px 14px', fontSize: '0.85rem', borderColor: 'rgba(86,211,100,0.3)', color: '#56d364', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Check size={14} /> Saved to your History as generation #{saved}.
                        </p>
                    )}
                    {error && (
                        <p role="alert" style={{ ...panel, padding: '10px 14px', fontSize: '0.85rem', borderColor: 'rgba(248,113,113,0.35)', color: '#f87171', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <X size={14} /> {error}
                        </p>
                    )}

                    {!doc ? (
                        <div style={{ ...panel, minHeight: '460px', display: 'grid', placeItems: 'center', textAlign: 'center', padding: '32px' }}>
                            <div style={{ maxWidth: '420px' }}>
                                <PenTool size={36} color="var(--p2)" style={{ marginBottom: '14px', opacity: 0.8 }} />
                                <p style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '8px' }}>Your UI appears here</p>
                                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                                    Upload a photo of a hand-drawn screen. Several screens on one page become several linked pages.
                                </p>
                            </div>
                        </div>
                    ) : (
                        <>
                            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }}>
                                <div role="tablist" style={{ ...panel, borderRadius: '12px', padding: '4px', display: 'flex', flexWrap: 'wrap', gap: '2px' }}>
                                    {TABS.map(({ id, label: text, icon: Icon }) => {
                                        const active = tab === id;
                                        return (
                                            <button type="button" key={id} role="tab" aria-selected={active} onClick={() => setTab(id)}
                                                style={{
                                                    display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 12px',
                                                    borderRadius: '9px', border: 'none', fontSize: '0.8rem', cursor: 'pointer',
                                                    fontFamily: 'var(--font-main)', fontWeight: active ? 600 : 400,
                                                    background: active ? 'var(--accent-gradient)' : 'none',
                                                    color: active ? 'white' : 'var(--text-secondary)',
                                                }}>
                                                <Icon size={13} /> {text}
                                            </button>
                                        );
                                    })}
                                </div>
                                <div style={{ marginLeft: 'auto', display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                                    {result && (
                                        <button type="button" className="btn-secondary" disabled={!!busy} onClick={redesign}
                                            title="Ask Claude for a new design of these pages"
                                            style={{ padding: '7px 12px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer' }}>
                                            <RefreshCw size={12} /> Redesign
                                        </button>
                                    )}
                                    {EXPORTS.map(([target, text]) => (
                                        <button type="button" key={target} className="btn-secondary" disabled={!!busy} onClick={() => download(target)}
                                            style={{ padding: '7px 12px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer' }}>
                                            <Download size={12} /> {text}
                                        </button>
                                    ))}
                                    {result && (
                                        <button type="button" className="generate-btn" disabled={!!busy || !!saved} onClick={saveToHistory}
                                            style={{ padding: '7px 14px', fontSize: '0.78rem' }}>
                                            <Save size={12} /> {saved ? 'Saved' : 'Save to History'}
                                        </button>
                                    )}
                                </div>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px' }}>
                                {stats.map(([name, value, Icon]) => (
                                    <div key={name} style={{ ...panel, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <span style={{ width: '32px', height: '32px', borderRadius: '9px', display: 'grid', placeItems: 'center', background: 'rgba(149,76,255,0.14)', color: '#c084fc' }}>
                                            <Icon size={15} />
                                        </span>
                                        <div>
                                            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{name}</div>
                                            <div style={{ fontWeight: 700 }}>{value}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {pages.length > 1 && (tab === 'preview' || tab === 'code') && (
                                <div role="group" aria-label="Page" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '6px' }}>
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginRight: '2px' }}>Pages</span>
                                    {pages.map(p => (
                                        <button type="button" key={p} aria-pressed={page === p} onClick={() => setPage(p)}
                                            style={{
                                                padding: '4px 12px', borderRadius: '999px', fontSize: '0.74rem', cursor: 'pointer',
                                                fontFamily: "'JetBrains Mono', monospace", border: '1px solid var(--border)',
                                                background: page === p ? 'var(--text)' : 'rgba(255,255,255,0.03)',
                                                color: page === p ? 'var(--bg)' : 'var(--text-secondary)',
                                            }}>{p}</button>
                                    ))}
                                </div>
                            )}

                            {tab === 'preview' && result && (
                                <div style={{ ...panel, overflow: 'hidden' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '9px 14px', borderBottom: '1px solid var(--border)' }}>
                                        <span style={{ flex: 1, minWidth: 0, fontFamily: "'JetBrains Mono', monospace", fontSize: '0.75rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis' }}>{page}</span>
                                        <div role="group" aria-label="Preview size" style={{ display: 'flex', gap: '2px' }}>
                                            {DEVICES.map(({ id, label: text, icon: Icon }) => (
                                                <button type="button" key={id} title={text} aria-label={text} aria-pressed={device === id} onClick={() => setDevice(id)}
                                                    style={{
                                                        width: '32px', height: '28px', display: 'grid', placeItems: 'center', borderRadius: '7px',
                                                        border: 'none', cursor: 'pointer',
                                                        background: device === id ? 'rgba(149,76,255,0.18)' : 'none',
                                                        color: device === id ? '#c084fc' : 'var(--text-secondary)',
                                                    }}>
                                                    <Icon size={14} />
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'center', background: '#0d1117', padding: device === 'desktop' ? 0 : '20px' }}>
                                        <iframe title="Generated page preview" srcDoc={withNav(result.pages[page])} sandbox="allow-scripts"
                                            style={{
                                                width: DEVICES.find(d => d.id === device).width, maxWidth: '100%', height: '640px',
                                                border: 'none', background: '#fff', borderRadius: device === 'desktop' ? 0 : '14px',
                                            }} />
                                    </div>
                                </div>
                            )}

                            {tab === 'code' && result && (
                                <div style={{ ...panel, overflow: 'hidden' }}>
                                    <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
                                        <CopyButton text={result.pages[page]} />
                                    </div>
                                    <pre style={{
                                        margin: 0, padding: '16px', height: '600px', overflow: 'auto', background: '#0d1117', color: '#e2e8f0',
                                        fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: '0.76rem', lineHeight: 1.65,
                                        whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                                    }}>{result.pages[page]}</pre>
                                </div>
                            )}

                            {tab === 'json' && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                    <textarea value={jsonText} onChange={e => setJsonText(e.target.value)} spellCheck={false}
                                        aria-label="Component JSON"
                                        style={{
                                            ...panel, height: '560px', padding: '16px', resize: 'vertical', background: '#0d1117', color: '#e2e8f0',
                                            fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: '0.76rem', lineHeight: 1.6, outline: 'none',
                                        }} />
                                    <button type="button" className="generate-btn" disabled={!!busy} onClick={saveJson} style={{ alignSelf: 'flex-start' }}>
                                        <Save size={14} /> Save and regenerate
                                    </button>
                                </div>
                            )}

                            {tab === 'flow' && <FlowMap doc={doc} />}

                            {tab === 'a11y' && result && (
                                <div style={{ ...panel, padding: '24px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '18px' }}>
                                    {[['Before fixes', result.a11y_before], ['After fixes', result.a11y_after]].map(([name, value], i) => (
                                        <div key={name}>
                                            <p style={label}>{name}</p>
                                            <p style={{ fontSize: '3rem', fontWeight: 800, lineHeight: 1.1 }}>
                                                <span className={i ? 'text-gradient' : undefined}>{value ?? '–'}</span>
                                                <span style={{ fontSize: '1.2rem', color: 'var(--text-secondary)' }}>/100</span>
                                            </p>
                                        </div>
                                    ))}
                                    <p style={{ gridColumn: '1 / -1', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                        {result.a11y_fixed_by === 'unavailable' ? "The accessibility checker isn't installed on the server (run npm install in the a11y folder)."
                                            : result.a11y_fixed_by === 'none' ? 'No accessibility problems found, so nothing needed fixing.'
                                                : `Problems were fixed automatically (${result.a11y_fixed_by === 'llm' ? 'by the AI' : 'by built-in rules'}). Scored with axe-core.`}
                                    </p>
                                </div>
                            )}

                            {tab === 'phone' && result && (
                                <div style={{ ...panel, padding: '24px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '24px' }}>
                                    <div style={{ background: '#fff', padding: '12px', borderRadius: '14px' }}>
                                        <QRCodeSVG value={phoneUrl} size={180} level="M" />
                                    </div>
                                    <div style={{ minWidth: 0, flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        <p style={{ fontSize: '1.2rem', fontWeight: 700 }}>Scan to open on your phone</p>
                                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                            When running locally, your phone must be on the same Wi-Fi and this site opened by the computer&apos;s network address (not localhost).
                                        </p>
                                        <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.74rem', wordBreak: 'break-all' }}>{phoneUrl}</p>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </section>
            </div>
        </div>
    );
};

export default SketchStudio;
