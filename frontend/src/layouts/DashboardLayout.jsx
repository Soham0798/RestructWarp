import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
    Sparkles, History, User, LogOut, Menu, X,
    Zap, Bot, CreditCard, ChevronRight, LayoutGrid, ChevronLeft
} from 'lucide-react';
import { useUser } from '../context/UserContext';

const NAV_ITEMS = [
    { to: '/', icon: Sparkles, label: 'Generate', end: true },
    { to: '/builder', icon: LayoutGrid, label: 'Builder' },
    { to: '/history', icon: History, label: 'History' },
    { to: '/profile', icon: User, label: 'Profile' },
    { to: '/pricing', icon: Zap, label: 'Upgrade' },
];

const DashboardLayout = () => {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const navigate = useNavigate();
    const { user } = useUser();

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/auth');
    };

    const initials = user?.email
        ? user.email.slice(0, 2).toUpperCase()
        : 'U';

    const displayName = user?.email
        ? user.email.split('@')[0]
        : 'My Account';

    const planLabel =
        user?.role === 'developer' ? 'Developer'
            : user?.role === 'admin' ? 'Admin'
                : 'Free Plan';

    const planColor =
        user?.role === 'developer' ? '#56d364'
            : user?.role === 'admin' ? '#e3b341'
                : 'var(--text-muted)';

    const creditDisplay = user?.credits >= 999_000_000 ? '∞' : (user?.credits ?? '—');

    const sidebarWidth = isSidebarCollapsed ? '60px' : '240px';

    return (
        <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)', position: 'relative' }}>
            <div className="main-mesh"></div>

            {/* Mobile overlay */}
            {isMobileMenuOpen && (
                <div
                    onClick={() => setIsMobileMenuOpen(false)}
                    style={{
                        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
                        zIndex: 40, backdropFilter: 'blur(4px)'
                    }}
                />
            )}

            {/* ── Sidebar ────────────────────────────────────────────────────── */}
            <aside className="sidebar" style={{
                width: sidebarWidth, background: 'var(--bg2)',
                borderRight: '1px solid var(--border)',
                display: 'flex', flexDirection: 'column',
                position: 'fixed', height: '100vh', zIndex: 50,
                transform: isMobileMenuOpen ? 'translateX(0)' : undefined,
                transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1), transform 0.3s cubic-bezier(0.4,0,0.2,1)',
                overflow: 'hidden',
            }}>
                <div className="sidebar-mesh" style={{
                    position: 'absolute', top: 0, left: 0, right: 0, height: '300px',
                    background: 'radial-gradient(circle at top left, rgba(149,76,255,0.06) 0%, transparent 70%)',
                    pointerEvents: 'none'
                }}></div>

                {/* Logo */}
                <div className="logo-area" style={{ padding: isSidebarCollapsed ? '24px 12px' : '24px 20px', position: 'relative', zIndex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div className="logo-icon" style={{
                            width: '28px', height: '28px', borderRadius: '8px',
                            background: 'linear-gradient(135deg, var(--p1), var(--p3))',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            boxShadow: '0 0 16px rgba(149,76,255,0.4)', flexShrink: 0
                        }}>
                            <Bot size={16} color="white" />
                        </div>
                        {!isSidebarCollapsed && (
                            <div>
                                <div className="logo-name" style={{
                                    fontSize: '15px', fontWeight: 800, letterSpacing: '-0.3px',
                                    background: 'linear-gradient(90deg, #fff, #bbb)',
                                    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
                                }}>
                                    Restruct Warp
                                </div>
                                <div className="logo-sub" style={{
                                    fontSize: '10px', fontWeight: 500, color: 'var(--p2)',
                                    letterSpacing: '0.5px', textTransform: 'uppercase'
                                }}>
                                    Builder Studio
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Credits pill */}
                {user && !isSidebarCollapsed && (
                    <div style={{ padding: '0 16px 16px', position: 'relative', zIndex: 1 }}>
                        <div style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            padding: '10px 14px', borderRadius: '10px',
                            background: 'rgba(149,76,255,0.05)', border: '1px solid var(--border-hi)',
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <CreditCard size={14} color="var(--p2)" />
                                <span style={{ fontSize: '12px', color: 'var(--muted)', fontWeight: 500 }}>Credits</span>
                            </div>
                            <span style={{
                                fontSize: '13px', fontWeight: 700,
                                color: user.credits >= 999_000_000 ? '#3fb950' : 'var(--text)'
                            }}>
                                {creditDisplay}
                            </span>
                        </div>
                    </div>
                )}

                {/* Nav */}
                <nav style={{ flex: 1, padding: '0 12px', display: 'flex', flexDirection: 'column', gap: '4px', position: 'relative', zIndex: 1 }}>
                    {!isSidebarCollapsed && (
                        <div className="nav-label" style={{
                            fontSize: '9px', fontWeight: 600, color: 'var(--muted2)',
                            letterSpacing: '1.5px', textTransform: 'uppercase',
                            padding: '12px 12px 8px'
                        }}>
                            Navigation
                        </div>
                    )}
                    {isSidebarCollapsed && <div style={{ height: 12 }} />}
                    {NAV_ITEMS.map(({ to, icon: Icon, label, end }) => (
                        <NavLink
                            key={to}
                            to={to}
                            end={end}
                            onClick={() => setIsMobileMenuOpen(false)}
                            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            style={({ isActive }) => ({
                                display: 'flex', alignItems: 'center', gap: isSidebarCollapsed ? '0' : '10px',
                                padding: isSidebarCollapsed ? '10px 0' : '10px 12px', borderRadius: '10px',
                                justifyContent: isSidebarCollapsed ? 'center' : 'flex-start',
                                color: isActive ? 'var(--text)' : 'var(--muted)',
                                background: isActive ? 'rgba(255,255,255,0.03)' : 'transparent',
                                border: '1px solid',
                                borderColor: isActive ? 'var(--border)' : 'transparent',
                                textDecoration: 'none', transition: 'all 0.2s ease',
                                fontSize: '13px', fontWeight: isActive ? 600 : 500,
                                position: 'relative'
                            })}
                        >
                            {({ isActive }) => (
                                <>
                                    {isActive && (
                                        <div style={{
                                            position: 'absolute', left: '-1px', top: '10%', bottom: '10%',
                                            width: '2px', background: 'linear-gradient(180deg, var(--p1), var(--p3))',
                                            borderRadius: '0 2px 2px 0'
                                        }} />
                                    )}
                                    <Icon size={16} color={isActive ? 'var(--p2)' : 'var(--muted)'} style={{ transition: 'color 0.2s', flexShrink: 0 }} />
                                    {!isSidebarCollapsed && <span style={{ flex: 1 }}>{label}</span>}
                                    {!isSidebarCollapsed && label === 'Upgrade' && (
                                        <span style={{
                                            fontSize: '9px', fontWeight: 700, letterSpacing: '0.5px',
                                            background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)',
                                            padding: '2px 6px', borderRadius: '4px', color: '#fbbf24'
                                        }}>PRO</span>
                                    )}
                                </>
                            )}
                        </NavLink>
                    ))}
                </nav>

                {/* Bottom — user card + logout */}
                <div className="account-area" style={{
                    padding: isSidebarCollapsed ? '12px 8px' : '16px 12px', borderTop: '1px solid var(--border)',
                    position: 'relative', zIndex: 1
                }}>
                    <div className="account-card" style={{
                        display: 'flex', alignItems: 'center', gap: isSidebarCollapsed ? '0' : '10px',
                        padding: isSidebarCollapsed ? '8px' : '12px', borderRadius: '12px',
                        background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)',
                        marginBottom: '8px', justifyContent: isSidebarCollapsed ? 'center' : 'flex-start'
                    }}>
                        <div style={{
                            width: '32px', height: '32px', borderRadius: '8px', flexShrink: 0,
                            background: 'linear-gradient(135deg, var(--p1), var(--p3))',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '12px', fontWeight: 700, color: '#fff'
                        }}>
                            {initials}
                        </div>
                        {!isSidebarCollapsed && (
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{
                                    fontSize: '13px', fontWeight: 600, color: 'var(--text)',
                                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                                }}>
                                    {displayName}
                                </div>
                                <div style={{ fontSize: '10px', color: planColor, fontFamily: "'DM Mono', monospace", marginTop: '2px' }}>
                                    {planLabel}
                                </div>
                            </div>
                        )}
                    </div>

                    <button
                        type="button"
                        onClick={handleLogout}
                        style={{
                            display: 'flex', alignItems: 'center', gap: isSidebarCollapsed ? '0' : '8px',
                            width: '100%', padding: isSidebarCollapsed ? '10px 0' : '10px 12px',
                            justifyContent: isSidebarCollapsed ? 'center' : 'flex-start',
                            background: 'transparent', border: '1px solid transparent',
                            borderRadius: '10px', color: 'var(--muted)',
                            fontSize: '13px', fontWeight: 500,
                            transition: 'all 0.2s ease', fontFamily: 'var(--font-main)',
                            textAlign: 'left', cursor: 'pointer'
                        }}
                        onMouseEnter={e => {
                            e.currentTarget.style.color = '#f85149';
                            e.currentTarget.style.background = 'rgba(248,81,73,0.06)';
                        }}
                        onMouseLeave={e => {
                            e.currentTarget.style.color = 'var(--muted)';
                            e.currentTarget.style.background = 'transparent';
                        }}
                    >
                        <LogOut size={14} style={{ flexShrink: 0 }} />
                        {!isSidebarCollapsed && 'Sign Out'}
                    </button>
                </div>

                {/* Collapse toggle */}
                <div style={{ padding: '8px 12px', borderTop: '1px solid var(--border)', position: 'relative', zIndex: 1 }}>
                    <button
                        type="button"
                        onClick={() => setIsSidebarCollapsed(c => !c)}
                        style={{
                            display: 'flex', alignItems: 'center', justifyContent: isSidebarCollapsed ? 'center' : 'flex-start',
                            gap: '8px', width: '100%', padding: '8px 12px',
                            background: 'transparent', border: '1px solid transparent',
                            borderRadius: '10px', color: 'var(--muted)',
                            fontSize: '12px', fontWeight: 500,
                            transition: 'all 0.2s ease', fontFamily: 'var(--font-main)',
                            textAlign: 'left', cursor: 'pointer'
                        }}
                        onMouseEnter={e => {
                            e.currentTarget.style.color = 'var(--p2)';
                            e.currentTarget.style.background = 'rgba(149,76,255,0.06)';
                        }}
                        onMouseLeave={e => {
                            e.currentTarget.style.color = 'var(--muted)';
                            e.currentTarget.style.background = 'transparent';
                        }}
                    >
                        {isSidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
                        {!isSidebarCollapsed && 'Collapse'}
                    </button>
                </div>
            </aside>

            {/* ── Main Content ────────────────────────────────────────────────── */}
            <main className="main" style={{
                flex: 1, marginLeft: sidebarWidth,
                minHeight: '100vh', position: 'relative', zIndex: 1,
                display: 'flex', flexDirection: 'column',
                transition: 'margin-left 0.25s cubic-bezier(0.4,0,0.2,1)'
            }}>
                <Outlet />
            </main>
        </div>
    );
};

export default DashboardLayout;
