import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Mail, Shield, Zap, CreditCard, Clock, BarChart3, User as UserIcon, Key } from 'lucide-react';
import { useUser } from '../context/UserContext';

const ROLE_META = {
    developer: { label: 'Developer', color: '#56d364', bg: 'rgba(63,185,80,0.12)', border: 'rgba(63,185,80,0.3)' },
    admin: { label: 'Admin', color: '#e3b341', bg: 'rgba(227,179,65,0.12)', border: 'rgba(227,179,65,0.3)' },
    user: { label: 'Free Plan', color: '#8b949e', bg: 'rgba(139,148,158,0.1)', border: 'rgba(139,148,158,0.2)' },
};

const StatCard = ({ icon: Icon, label, value, color = '#6366f1', bg = 'rgba(99,102,241,0.1)' }) => (
    <div style={{
        padding: '18px 20px', borderRadius: '14px',
        background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)',
        display: 'flex', alignItems: 'center', gap: '14px',
        transition: 'border-color 0.2s ease'
    }}
        onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.25)'}
        onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--glass-border)'}
    >
        <div style={{
            width: '44px', height: '44px', borderRadius: '12px', flexShrink: 0,
            background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
            <Icon size={18} color={color} />
        </div>
        <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 500 }}>
                {label}
            </div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.03em', marginTop: '2px' }}>
                {value}
            </div>
        </div>
    </div>
);

const Profile = () => {
    const { user, loading } = useUser();

    const roleInfo = ROLE_META[user?.role] || ROLE_META.user;
    const initials = user?.email ? user.email.slice(0, 2).toUpperCase() : '??';
    const emailUser = user?.email?.split('@')[0] || '—';
    const emailDomain = user?.email?.split('@')[1] || '';
    const credits = user?.credits;
    const isUnlimited = credits >= 999_000_000;
    const joinDate = user?.created_at
        ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
        : '—';

    if (loading) {
        return (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: '70px', borderRadius: '14px' }} />)}
            </div>
        );
    }

    return (
        <div className="animate-fade-in content" style={{ maxWidth: '760px' }}>
            {/* Header */}
            <div style={{ marginBottom: '28px' }}>
                <h1 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.04em' }}>Account</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '3px' }}>
                    Manage your profile and subscription
                </p>
            </div>

            {/* Avatar card */}
            <div style={{
                padding: '28px', borderRadius: '18px', marginBottom: '16px',
                background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)',
                display: 'flex', gap: '20px', alignItems: 'center', flexWrap: 'wrap'
            }}>
                {/* Avatar */}
                <div style={{
                    width: '72px', height: '72px', borderRadius: '20px', flexShrink: 0,
                    background: 'var(--accent-gradient)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '1.4rem', fontWeight: 800, color: '#fff',
                    boxShadow: '0 4px 20px rgba(99,102,241,0.35)',
                    letterSpacing: '-0.02em'
                }}>
                    {initials}
                </div>

                {/* Info */}
                <div style={{ flex: 1, minWidth: '180px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '5px' }}>
                        <h2 style={{ fontSize: '1.15rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
                            {emailUser}
                        </h2>
                        <span style={{
                            display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '3px 10px',
                            borderRadius: '99px', background: roleInfo.bg, border: `1px solid ${roleInfo.border}`,
                            color: roleInfo.color, fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.03em'
                        }}>
                            <Shield size={9} /> {roleInfo.label}
                        </span>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        {user?.email}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                        Member since {joinDate}
                    </div>
                </div>

                {/* Credits badge */}
                <div style={{
                    padding: '14px 20px', borderRadius: '14px', textAlign: 'center',
                    background: isUnlimited ? 'rgba(63,185,80,0.08)' : 'rgba(99,102,241,0.08)',
                    border: `1px solid ${isUnlimited ? 'rgba(63,185,80,0.2)' : 'rgba(99,102,241,0.2)'}`
                }}>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, marginBottom: '4px' }}>
                        Credits
                    </div>
                    <div style={{
                        fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.04em',
                        color: isUnlimited ? '#56d364' : '#a5b4fc'
                    }}>
                        {isUnlimited ? '∞' : credits?.toLocaleString()}
                    </div>
                    <div style={{ fontSize: '0.65rem', color: isUnlimited ? '#56d364' : 'var(--text-muted)', marginTop: '2px', fontWeight: 500 }}>
                        {isUnlimited ? 'Unlimited' : 'remaining'}
                    </div>
                </div>
            </div>

            {/* Stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '10px', marginBottom: '16px' }}>
                <StatCard icon={CreditCard} label="Credits" value={isUnlimited ? '∞' : credits?.toLocaleString()} color="#6366f1" bg="rgba(99,102,241,0.1)" />
                <StatCard icon={Shield} label="Role" value={roleInfo.label} color={roleInfo.color} bg={roleInfo.bg} />
                <StatCard icon={Clock} label="Member Since" value={joinDate.split(' ')[1] || joinDate} color="#8b5cf6" bg="rgba(139,92,246,0.1)" />
                <StatCard icon={BarChart3} label="Status" value="Active" color="#56d364" bg="rgba(63,185,80,0.1)" />
            </div>

            {/* Details section */}
            <div style={{
                borderRadius: '16px', overflow: 'hidden',
                background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)'
            }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--glass-border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <UserIcon size={14} color="var(--text-muted)" />
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '-0.01em' }}>
                        Account Details
                    </span>
                </div>
                {[
                    { icon: Mail, label: 'Email', value: user?.email },
                    { icon: Shield, label: 'Role', value: user?.role },
                    { icon: Key, label: 'Account ID', value: `#${user?.id ?? '—'}` },
                    { icon: Zap, label: 'Credits Remaining', value: isUnlimited ? 'Unlimited' : `${credits?.toLocaleString()} credits` },
                ].map(({ icon: Icon, label, value }, i, arr) => (
                    <div
                        key={label}
                        style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            padding: '14px 20px',
                            borderBottom: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none'
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <Icon size={14} color="var(--text-muted)" />
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{label}</span>
                        </div>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 500 }}>{value}</span>
                    </div>
                ))}
            </div>

            {/* Upgrade CTA if free user */}
            {user?.role === 'user' && (
                <div style={{
                    marginTop: '16px', padding: '20px 24px', borderRadius: '16px',
                    background: 'linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(139,92,246,0.08) 100%)',
                    border: '1px solid rgba(99,102,241,0.2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap'
                }}>
                    <div>
                        <div style={{ fontWeight: 700, marginBottom: '3px' }}>Unlock unlimited generations</div>
                        <div style={{ fontSize: '0.83rem', color: 'var(--text-secondary)' }}>
                            Upgrade to Pro for unlimited credits, priority AI, and team features.
                        </div>
                    </div>
                    <Link to="/pricing" style={{
                        display: 'inline-flex', alignItems: 'center', gap: '7px',
                        background: 'var(--accent-gradient)', color: '#fff',
                        padding: '10px 20px', borderRadius: '10px', textDecoration: 'none',
                        fontWeight: 600, fontSize: '0.85rem', whiteSpace: 'nowrap',
                        boxShadow: '0 4px 16px rgba(99,102,241,0.35)'
                    }}>
                        <Zap size={14} /> Upgrade to Pro
                    </Link>
                </div>
            )}
        </div>
    );
};

export default Profile;
