import { useState, useEffect } from 'react';
import { Search, Globe, Server, Layers, ExternalLink, Clock, Code2, ChevronRight, Inbox, Calendar, Zap } from 'lucide-react';
import { API_BASE } from '../config';

const TYPE_META = {
    website: { label: 'Website', color: '#6366f1', bg: 'rgba(99,102,241,0.12)', border: 'rgba(99,102,241,0.25)', icon: Globe },
    backend: { label: 'Backend', color: '#ec4899', bg: 'rgba(236,72,153,0.12)', border: 'rgba(236,72,153,0.25)', icon: Server },
    fullstack: { label: 'Full Stack', color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)', border: 'rgba(139,92,246,0.25)', icon: Layers },
};

function TypeBadge({ type }) {
    const m = TYPE_META[type] || TYPE_META.website;
    const Icon = m.icon;
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '5px',
            padding: '3px 9px', borderRadius: '99px',
            background: m.bg, border: `1px solid ${m.border}`,
            color: m.color, fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.02em',
            whiteSpace: 'nowrap'
        }}>
            <Icon size={10} /> {m.label}
        </span>
    );
}

function timeAgo(dateStr) {
    const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const History = () => {
    const [items, setItems] = useState([]);
    const [filtered, setFiltered] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [typeFilter, setTypeFilter] = useState('all');
    const [expanded, setExpanded] = useState(null);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) return;
        fetch(`${API_BASE}/dashboard/history`, { headers: { Authorization: `Bearer ${token}` } })
            .then(r => r.json())
            .then(data => { setItems(data); setFiltered(data); })
            .catch(() => { })
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        let f = items;
        if (typeFilter !== 'all') f = f.filter(i => i.type === typeFilter);
        if (search.trim()) f = f.filter(i => i.prompt.toLowerCase().includes(search.toLowerCase()));
        setFiltered(f);
    }, [search, typeFilter, items]);

    return (
        <div className="animate-fade-in content">
            {/* Header */}
            <div style={{ marginBottom: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                    <div>
                        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.04em' }}>
                            Generation History
                        </h1>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '3px' }}>
                            {items.length} project{items.length !== 1 ? 's' : ''} generated
                        </p>
                    </div>
                    {/* Stats strip */}
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                        {Object.entries(TYPE_META).map(([key, m]) => {
                            const count = items.filter(i => i.type === key).length;
                            const Icon = m.icon;
                            return (
                                <div key={key} style={{
                                    display: 'flex', alignItems: 'center', gap: '6px',
                                    padding: '6px 12px', borderRadius: '8px',
                                    background: m.bg, border: `1px solid ${m.border}`,
                                }}>
                                    <Icon size={12} color={m.color} />
                                    <span style={{ fontSize: '0.72rem', color: m.color, fontWeight: 600 }}>{count} {m.label}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Toolbar */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '18px', flexWrap: 'wrap' }}>
                {/* Search */}
                <div style={{ position: 'relative', flex: '1 1 260px' }}>
                    <Search size={14} style={{ position: 'absolute', left: '13px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input
                        type="text"
                        className="input-field"
                        placeholder="Search prompts…"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        style={{ paddingLeft: '38px', padding: '9px 14px 9px 38px', fontSize: '0.85rem' }}
                    />
                </div>

                {/* Type filter pills */}
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
                    {['all', 'website', 'fullstack', 'backend'].map(t => (
                        <button
                            type="button"
                            key={t}
                            onClick={() => setTypeFilter(t)}
                            style={{
                                padding: '7px 14px', borderRadius: '8px', border: '1px solid',
                                borderColor: typeFilter === t ? 'rgba(99,102,241,0.4)' : 'var(--glass-border)',
                                background: typeFilter === t ? 'rgba(99,102,241,0.12)' : 'rgba(255,255,255,0.03)',
                                color: typeFilter === t ? '#a5b4fc' : 'var(--text-secondary)',
                                fontSize: '0.78rem', fontWeight: typeFilter === t ? 600 : 400,
                                fontFamily: 'var(--font-main)', transition: 'all 0.2s ease',
                                textTransform: 'capitalize'
                            }}
                        >
                            {t === 'all' ? 'All Types' : t}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            {loading ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className="skeleton" style={{ height: '76px', borderRadius: '12px' }} />
                    ))}
                </div>
            ) : filtered.length === 0 ? (
                <div style={{
                    padding: '70px 40px', textAlign: 'center',
                    background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)',
                    borderRadius: '16px'
                }}>
                    <div style={{
                        width: '56px', height: '56px', borderRadius: '16px', margin: '0 auto 16px',
                        background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                        <Inbox size={24} color="#6366f1" />
                    </div>
                    <h3 style={{ fontWeight: 600, marginBottom: '6px', fontSize: '1rem' }}>
                        {search || typeFilter !== 'all' ? 'No results found' : 'No generations yet'}
                    </h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.83rem' }}>
                        {search || typeFilter !== 'all'
                            ? 'Try a different search or filter'
                            : 'Head to Generate to build your first project'}
                    </p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {filtered.map((item, idx) => {
                        const isOpen = expanded === item.id;
                        return (
                            <div
                                key={item.id}
                                style={{
                                    background: 'var(--bg-secondary)',
                                    border: '1px solid var(--glass-border)',
                                    borderRadius: '12px',
                                    overflow: 'hidden',
                                    transition: 'border-color 0.2s ease',
                                    animation: `fadeInUp 0.3s ease-out ${idx * 0.03}s both`,
                                }}
                                onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.25)'}
                                onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--glass-border)'}
                            >
                                {/* Row */}
                                <div
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: '14px',
                                        padding: '14px 16px'
                                    }}
                                    onClick={() => setExpanded(isOpen ? null : item.id)}
                                >
                                    {/* Icon */}
                                    <div style={{
                                        width: '36px', height: '36px', borderRadius: '10px', flexShrink: 0,
                                        background: TYPE_META[item.type]?.bg || 'rgba(99,102,241,0.1)',
                                        border: `1px solid ${TYPE_META[item.type]?.border || 'rgba(99,102,241,0.2)'}`,
                                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                                    }}>
                                        {(() => { const Icon = (TYPE_META[item.type] || TYPE_META.website).icon; return <Icon size={15} color={(TYPE_META[item.type] || TYPE_META.website).color} />; })()}
                                    </div>

                                    {/* Prompt */}
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{
                                            fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-primary)',
                                            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                                        }}>
                                            {item.prompt}
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '3px', flexWrap: 'wrap' }}>
                                            <TypeBadge type={item.type} />
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                                                <Calendar size={10} /> {formatDate(item.created_at)}
                                            </span>
                                            {item.response_time && (
                                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                                                    <Zap size={10} /> {(item.response_time / 1000).toFixed(1)}s
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Ago + expand */}
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
                                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{timeAgo(item.created_at)}</span>
                                        <ChevronRight
                                            size={15}
                                            color="var(--text-muted)"
                                            style={{ transform: isOpen ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s ease' }}
                                        />
                                    </div>
                                </div>

                                {/* Expanded code preview */}
                                {isOpen && (
                                    <div style={{ borderTop: '1px solid var(--glass-border)' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 16px', background: '#0d1117' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                                                <Code2 size={11} />
                                                Output preview
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => navigator.clipboard.writeText(item.output)}
                                                style={{
                                                    background: 'none', border: '1px solid var(--glass-border)',
                                                    padding: '3px 9px', borderRadius: '6px',
                                                    color: 'var(--text-muted)', fontSize: '0.7rem', fontFamily: 'var(--font-main)',
                                                    transition: 'all 0.2s'
                                                }}
                                                onMouseEnter={e => { e.currentTarget.style.color = '#a5b4fc'; e.currentTarget.style.borderColor = 'rgba(99,102,241,0.4)'; }}
                                                onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.borderColor = 'var(--glass-border)'; }}
                                            >
                                                Copy
                                            </button>
                                        </div>
                                        <pre style={{
                                            margin: 0, padding: '14px 16px', background: '#0d1117',
                                            fontFamily: 'monospace', fontSize: '0.75rem', lineHeight: 1.7,
                                            color: '#8b949e', overflow: 'auto', maxHeight: '200px',
                                            whiteSpace: 'pre-wrap', wordBreak: 'break-word'
                                        }}>
                                            {item.output.slice(0, 1200)}{item.output.length > 1200 ? '\n…' : ''}
                                        </pre>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default History;
