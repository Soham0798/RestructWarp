import { useState } from 'react';
import { Check, Zap, Building2, Sparkles } from 'lucide-react';

const PLANS = [
    {
        id: 'starter',
        name: 'Starter',
        desc: 'For indie builders and hobbyists',
        monthlyPrice: 0,
        yearlyPrice: 0,
        color: '#8b949e',
        accent: 'rgba(139,148,158,0.15)',
        border: 'rgba(139,148,158,0.2)',
        cta: 'Current Plan',
        ctaDisabled: true,
        features: [
            '50 AI generations / month',
            'Website generation (Groq)',
            'Live preview',
            'Generation history',
            'Community support',
        ],
        missing: ['Claude streaming', 'Backend / Full-stack', 'Priority queue', 'API access'],
    },
    {
        id: 'pro',
        name: 'Pro',
        desc: 'For serious builders shipping products',
        monthlyPrice: 29,
        yearlyPrice: 19,
        color: '#6366f1',
        accent: 'rgba(99,102,241,0.12)',
        border: 'rgba(99,102,241,0.35)',
        cta: 'Upgrade to Pro',
        featured: true,
        features: [
            'Unlimited AI generations',
            'Claude Opus streaming',
            'Website + Backend + Full-stack',
            'Priority generation queue',
            'Streaming real-time refiner',
            'API access (100k req/mo)',
            'Email support',
        ],
        missing: ['Dedicated infrastructure', 'SSO / SAML', 'Custom AI models'],
    },
    {
        id: 'enterprise',
        name: 'Enterprise',
        desc: 'For teams and scaling companies',
        monthlyPrice: null,
        yearlyPrice: null,
        color: '#8b5cf6',
        accent: 'rgba(139,92,246,0.1)',
        border: 'rgba(139,92,246,0.25)',
        cta: 'Contact Sales',
        features: [
            'Everything in Pro',
            'Dedicated AI infrastructure',
            'Custom AI model fine-tuning',
            'SSO / SAML authentication',
            'Unlimited API requests',
            'SLA & uptime guarantee',
            'Dedicated account manager',
        ],
        missing: [],
    },
];

const FAQS = [
    { q: 'Can I cancel anytime?', a: 'Yes — monthly subscriptions can be cancelled at any time with no penalty. Yearly plans are refunded on a prorated basis.' },
    { q: 'What counts as a "generation"?', a: 'Each successful AI output (website, backend project, or full-stack app) counts as one generation.' },
    { q: 'Which AI models are used?', a: 'Starter uses Groq (Llama 3). Pro and Enterprise unlock Claude Opus for higher-quality streaming generation.' },
    { q: 'Do you offer a free trial?', a: 'The Starter plan is permanently free with 50 generations/month — no credit card required.' },
    { q: 'Is there an API?', a: 'Pro and Enterprise plans include REST API access so you can integrate EmergentAI into your own workflows.' },
];

const Pricing = () => {
    const [yearly, setYearly] = useState(false);
    const [openFaq, setOpenFaq] = useState(null);

    return (
        <div className="animate-fade-in content">
            {/* Header */}
            <div style={{ textAlign: 'center', marginBottom: '36px' }}>
                <div className="badge badge-accent" style={{ margin: '0 auto 14px', width: 'fit-content' }}>
                    <Sparkles size={11} /> Simple, transparent pricing
                </div>
                <h1 className="hero-headline" style={{ fontSize: 'clamp(1.8rem, 4vw, 2.6rem)', marginBottom: '10px' }}>
                    Choose your <span className="accent">build speed</span>
                </h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', maxWidth: '480px', margin: '0 auto 24px' }}>
                    Start free. Upgrade when you need faster AI, more generations, or advanced features.
                </p>

                {/* Billing toggle */}
                <div style={{
                    display: 'inline-flex', alignItems: 'center', gap: '12px',
                    background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)',
                    padding: '5px', borderRadius: '12px'
                }}>
                    <button
                        type="button"
                        onClick={() => setYearly(false)}
                        style={{
                            padding: '7px 18px', borderRadius: '8px', border: 'none',
                            background: !yearly ? 'rgba(99,102,241,0.15)' : 'transparent',
                            color: !yearly ? '#a5b4fc' : 'var(--text-secondary)',
                            fontWeight: !yearly ? 600 : 400, fontSize: '0.85rem',
                            fontFamily: 'var(--font-main)', transition: 'all 0.2s ease'
                        }}
                    >
                        Monthly
                    </button>
                    <button
                        type="button"
                        onClick={() => setYearly(true)}
                        style={{
                            padding: '7px 18px', borderRadius: '8px', border: 'none',
                            background: yearly ? 'rgba(99,102,241,0.15)' : 'transparent',
                            color: yearly ? '#a5b4fc' : 'var(--text-secondary)',
                            fontWeight: yearly ? 600 : 400, fontSize: '0.85rem',
                            fontFamily: 'var(--font-main)', transition: 'all 0.2s ease',
                            display: 'flex', alignItems: 'center', gap: '7px'
                        }}
                    >
                        Yearly
                        <span style={{
                            fontSize: '0.65rem', fontWeight: 700, background: 'linear-gradient(135deg, #56d364, #3fb950)',
                            padding: '2px 7px', borderRadius: '99px', color: '#fff', letterSpacing: '0.02em'
                        }}>
                            −35%
                        </span>
                    </button>
                </div>
            </div>

            {/* Plan cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px', marginBottom: '50px', alignItems: 'start' }}>
                {PLANS.map((plan) => (
                    <div
                        key={plan.id}
                        style={{
                            borderRadius: '18px', overflow: 'hidden',
                            background: plan.featured ? 'linear-gradient(180deg, rgba(99,102,241,0.08) 0%, var(--bg-secondary) 100%)' : 'var(--bg-secondary)',
                            border: `1px solid ${plan.featured ? 'rgba(99,102,241,0.4)' : plan.border}`,
                            boxShadow: plan.featured ? '0 0 40px rgba(99,102,241,0.12)' : 'none',
                            position: 'relative',
                            transition: 'transform 0.2s ease, box-shadow 0.2s ease'
                        }}
                        onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = plan.featured ? '0 8px 50px rgba(99,102,241,0.2)' : '0 4px 20px rgba(0,0,0,0.3)'; }}
                        onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = plan.featured ? '0 0 40px rgba(99,102,241,0.12)' : 'none'; }}
                    >
                        {/* Popular badge */}
                        {plan.featured && (
                            <div style={{
                                background: 'var(--accent-gradient)',
                                padding: '6px 16px', textAlign: 'center',
                                fontSize: '0.72rem', fontWeight: 700, color: '#fff', letterSpacing: '0.05em',
                                textTransform: 'uppercase'
                            }}>
                                ✦ Most Popular
                            </div>
                        )}

                        <div style={{ padding: '24px' }}>
                            {/* Plan header */}
                            <div style={{ marginBottom: '20px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                    <div style={{
                                        width: '28px', height: '28px', borderRadius: '8px',
                                        background: plan.accent, display: 'flex', alignItems: 'center', justifyContent: 'center'
                                    }}>
                                        {plan.id === 'starter' ? <Zap size={13} color={plan.color} /> :
                                            plan.id === 'pro' ? <Sparkles size={13} color={plan.color} /> :
                                                <Building2 size={13} color={plan.color} />}
                                    </div>
                                    <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)' }}>{plan.name}</span>
                                </div>
                                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>{plan.desc}</p>
                            </div>

                            {/* Price */}
                            <div style={{ marginBottom: '22px' }}>
                                {plan.monthlyPrice === null ? (
                                    <div style={{ fontSize: '1.8rem', fontWeight: 800, letterSpacing: '-0.05em', color: 'var(--text-primary)' }}>
                                        Custom
                                    </div>
                                ) : plan.monthlyPrice === 0 ? (
                                    <div>
                                        <span style={{ fontSize: '2rem', fontWeight: 800, letterSpacing: '-0.05em', color: 'var(--text-primary)' }}>Free</span>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>forever</div>
                                    </div>
                                ) : (
                                    <div>
                                        <div style={{ display: 'flex', alignItems: 'baseline', gap: '2px' }}>
                                            <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 500 }}>$</span>
                                            <span style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.05em', color: 'var(--text-primary)' }}>
                                                {yearly ? plan.yearlyPrice : plan.monthlyPrice}
                                            </span>
                                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>/mo</span>
                                        </div>
                                        {yearly && (
                                            <div style={{ fontSize: '0.72rem', color: '#56d364', fontWeight: 500, marginTop: '2px' }}>
                                                Billed ${plan.yearlyPrice * 12}/yr
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* CTA */}
                            <button
                                type="button"
                                onClick={() => {
                                    if (!plan.ctaDisabled) {
                                        alert("Checkout flow coming soon!");
                                    }
                                }}
                                style={{
                                    width: '100%', padding: '11px', borderRadius: '11px',
                                    background: plan.featured ? 'var(--accent-gradient)' : plan.ctaDisabled ? 'rgba(255,255,255,0.04)' : plan.accent,
                                    border: plan.featured ? 'none' : `1px solid ${plan.border}`,
                                    color: plan.featured ? '#fff' : plan.ctaDisabled ? 'var(--text-muted)' : plan.color,
                                    fontWeight: 600, fontSize: '0.875rem',
                                    fontFamily: 'var(--font-main)', letterSpacing: '-0.01em',
                                    boxShadow: plan.featured ? '0 4px 16px rgba(99,102,241,0.35)' : 'none',
                                    marginBottom: '20px', transition: 'opacity 0.2s'
                                }}
                                onMouseEnter={e => !plan.ctaDisabled && (e.currentTarget.style.opacity = '0.88')}
                                onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
                            >
                                {plan.cta}
                            </button>

                            {/* Features */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>
                                {plan.features.map(f => (
                                    <div key={f} style={{ display: 'flex', alignItems: 'flex-start', gap: '9px', fontSize: '0.82rem' }}>
                                        <div style={{
                                            width: '16px', height: '16px', borderRadius: '5px', flexShrink: 0, marginTop: '1px',
                                            background: 'rgba(63,185,80,0.15)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                                        }}>
                                            <Check size={10} color="#56d364" strokeWidth={2.5} />
                                        </div>
                                        <span style={{ color: 'var(--text-secondary)', lineHeight: 1.4 }}>{f}</span>
                                    </div>
                                ))}
                                {plan.missing.map(f => (
                                    <div key={f} style={{ display: 'flex', alignItems: 'flex-start', gap: '9px', fontSize: '0.82rem', opacity: 0.35 }}>
                                        <div style={{
                                            width: '16px', height: '16px', borderRadius: '5px', flexShrink: 0, marginTop: '1px',
                                            background: 'rgba(255,255,255,0.05)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                                        }}>
                                            <div style={{ width: '8px', height: '1px', background: 'var(--text-muted)' }} />
                                        </div>
                                        <span style={{ color: 'var(--text-muted)', lineHeight: 1.4 }}>{f}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* FAQ */}
            <div style={{ maxWidth: '640px', margin: '0 auto' }}>
                <h2 style={{ fontSize: '1.2rem', fontWeight: 700, letterSpacing: '-0.03em', marginBottom: '16px', textAlign: 'center' }}>
                    Frequently asked questions
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {FAQS.map((faq, i) => (
                        <details
                            key={i}
                            style={{
                                background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)',
                                borderRadius: '12px', overflow: 'hidden'
                            }}
                            onToggle={e => setOpenFaq(e.target.open ? i : null)}
                        >
                            <summary style={{
                                padding: '15px 18px', fontSize: '0.875rem', fontWeight: 600,
                                color: 'var(--text-primary)',
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                listStyle: 'none', userSelect: 'none'
                            }}>
                                {faq.q}
                                <span style={{
                                    fontSize: '1rem', color: 'var(--text-muted)',
                                    transform: openFaq === i ? 'rotate(45deg)' : 'none',
                                    transition: 'transform 0.2s ease', display: 'inline-block', flexShrink: 0
                                }}>+</span>
                            </summary>
                            <div style={{
                                padding: '0 18px 15px', fontSize: '0.85rem',
                                color: 'var(--text-secondary)', lineHeight: 1.7,
                                borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '12px', marginTop: '-2px'
                            }}>
                                {faq.a}
                            </div>
                        </details>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default Pricing;
