import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, Loader2, Mail, Lock, ArrowRight, Sparkles } from 'lucide-react';
import { API_BASE } from '../config';
import { useUser } from '../context/UserContext';

const Auth = () => {
    const [isRegistering, setIsRegistering] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const navigate = useNavigate();
    const { refetch } = useUser();

    const loginAsDev = async () => {
        setError('');
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: 'dev@bobthebuilder.ai', password: 'dev123' })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Authentication failed');
            localStorage.setItem('token', data.access_token);
            await refetch();
            navigate('/landing');
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleAuth = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        const endpoint = isRegistering ? '/auth/register' : '/auth/login';

        try {
            const res = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Authentication failed');

            if (isRegistering) {
                const loginRes = await fetch(`${API_BASE}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const loginData = await loginRes.json();
                if (!loginRes.ok) throw new Error(loginData.detail || 'Login failed after registration');
                localStorage.setItem('token', loginData.access_token);
                await refetch();
                navigate('/landing');
            } else {
                localStorage.setItem('token', data.access_token);
                await refetch();
                navigate('/landing');
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            background: 'var(--bg-primary)',
            position: 'relative',
            overflow: 'hidden'
        }}>
            {/* Background elements */}
            <div className="mesh-bg" />

            {/* Glowing orbs */}
            <div style={{
                position: 'absolute', width: '600px', height: '600px',
                borderRadius: '50%', top: '-200px', left: '-200px',
                background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)',
                filter: 'blur(40px)', pointerEvents: 'none'
            }} />
            <div style={{
                position: 'absolute', width: '400px', height: '400px',
                borderRadius: '50%', bottom: '-100px', right: '-100px',
                background: 'radial-gradient(circle, rgba(236,72,153,0.08) 0%, transparent 70%)',
                filter: 'blur(40px)', pointerEvents: 'none'
            }} />

            {/* Left Hero Panel — hidden on mobile */}
            <div className="md-show" style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                padding: '60px',
                position: 'relative',
                borderRight: '1px solid var(--glass-border)'
            }}>
                {/* Logo */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '64px' }}>
                    <div style={{
                        background: 'var(--accent-gradient)', padding: '10px', borderRadius: '14px',
                        display: 'flex', boxShadow: '0 0 30px var(--accent-glow)'
                    }}>
                        <Bot size={24} color="white" />
                    </div>
                    <span style={{ fontSize: '1.1rem', fontWeight: 700 }} className="gradient-text">EmergentAI</span>
                </div>

                {/* Hero text */}
                <div style={{ maxWidth: '480px' }}>
                    <h1 style={{ fontSize: '3rem', fontWeight: 800, lineHeight: 1.1, marginBottom: '20px' }}>
                        Build full-stack apps{' '}
                        <span className="gradient-text">with a single prompt.</span>
                    </h1>
                    <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '40px' }}>
                        EmergentAI transforms your ideas into real, deployable websites and APIs in seconds using the power of AI.
                    </p>

                    {/* Features list */}
                    {['AI Website Generation', 'Full-Stack App Builder', 'Live Code Editor', 'Instant Preview'].map((feat, i) => (
                        <div key={feat} style={{
                            display: 'flex', alignItems: 'center', gap: '12px',
                            marginBottom: '12px',
                            animation: `fadeInUp 0.5s ease-out ${i * 0.1}s both`
                        }}>
                            <div style={{
                                width: '28px', height: '28px', borderRadius: '8px',
                                background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <Sparkles size={13} color="#a5b4fc" />
                            </div>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{feat}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Right Auth Panel */}
            <div style={{
                width: '100%',
                maxWidth: '480px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                padding: '40px',
                position: 'relative'
            }}>
                {/* Mobile logo */}
                <div className="md-hidden" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '40px', justifyContent: 'center' }}>
                    <div style={{ background: 'var(--accent-gradient)', padding: '8px', borderRadius: '12px', display: 'flex' }}>
                        <Bot size={20} color="white" />
                    </div>
                    <span className="gradient-text" style={{ fontSize: '1.1rem', fontWeight: 700 }}>EmergentAI</span>
                </div>

                <div className="animate-fade-in" style={{ width: '100%', maxWidth: '380px', margin: '0 auto' }}>
                    {/* Header */}
                    <div style={{ marginBottom: '32px' }}>
                        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '8px', letterSpacing: '-0.03em' }}>
                            {isRegistering ? 'Create account' : 'Welcome back'}
                        </h2>
                        <p style={{ color: 'var(--text-secondary)' }}>
                            {isRegistering
                                ? 'Start building AI-powered apps today.'
                                : 'Sign in to continue building.'}
                        </p>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        {error && (
                            <div style={{
                                color: 'var(--danger)', background: 'rgba(248,81,73,0.08)',
                                border: '1px solid rgba(248,81,73,0.25)',
                                padding: '12px 16px', borderRadius: 'var(--radius-sm)',
                                fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: '8px'
                            }}>
                                ⚠️ {error}
                            </div>
                        )}

                        <div>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
                                Email address
                            </label>
                            <div style={{ position: 'relative' }}>
                                <Mail size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                                <input
                                    id="auth-email"
                                    type="email"
                                    className="input-field"
                                    placeholder="you@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    style={{ paddingLeft: '42px' }}
                                />
                            </div>
                        </div>

                        <div>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
                                Password
                            </label>
                            <div style={{ position: 'relative' }}>
                                <Lock size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                                <input
                                    id="auth-password"
                                    type="password"
                                    className="input-field"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    style={{ paddingLeft: '42px' }}
                                />
                            </div>
                        </div>

                        <button
                            id="auth-submit"
                            type="submit"
                            className="btn-primary"
                            style={{ marginTop: '8px', height: '48px', fontSize: '0.95rem' }}
                            disabled={loading}
                        >
                            {loading
                                ? <Loader2 className="animate-spin" size={18} />
                                : (
                                    <>
                                        {isRegistering ? 'Create Account' : 'Sign In'}
                                        <ArrowRight size={16} />
                                    </>
                                )}
                        </button>
                    </form>

                    {/* Divider */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: '24px 0', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        <div style={{ flex: 1, height: '1px', background: 'var(--glass-border)' }} />
                        OR
                        <div style={{ flex: 1, height: '1px', background: 'var(--glass-border)' }} />
                    </div>

                    {/* Toggle */}
                    <div style={{
                        textAlign: 'center', fontSize: '0.9rem',
                        padding: '16px', borderRadius: 'var(--radius-md)',
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid var(--glass-border)',
                        display: 'flex', flexDirection: 'column', gap: '12px'
                    }}>
                        <div>
                            <span style={{ color: 'var(--text-secondary)' }}>
                                {isRegistering ? 'Already have an account? ' : "Don't have an account? "}
                            </span>
                            <button
                                type="button"
                                onClick={() => { setIsRegistering(!isRegistering); setError(''); }}
                                style={{
                                    background: 'none', border: 'none',
                                    fontWeight: 600,
                                    fontFamily: 'var(--font-main)', fontSize: '0.9rem'
                                }}
                                className="text-gradient"
                            >
                                {isRegistering ? 'Sign In' : 'Sign Up'}
                            </button>
                        </div>
                        <button
                            type="button"
                            onClick={loginAsDev}
                            className="btn-secondary"
                            style={{ padding: '8px', fontSize: '0.85rem' }}
                        >
                            <Bot size={14} style={{ marginRight: '6px' }} />
                            Use Developer Account
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Auth;
