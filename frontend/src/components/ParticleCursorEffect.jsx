import { useEffect } from 'react';

const ParticleCursorEffect = () => {
    // ── Particle canvas + cursor RAF — global dashboard effect
    useEffect(() => {
        // --- Create and inject all effect elements into body ---
        const make = (tag, cls, extra = {}) => {
            const el = document.createElement(tag);
            if (cls) el.className = cls;
            Object.assign(el.style, extra);
            document.body.appendChild(el);
            return el;
        };

        const canvas = make('canvas', '', { position: 'fixed', inset: '0', zIndex: '0', pointerEvents: 'none', width: '100%', height: '100%' });
        const grain = make('div', 'grain');
        const blob = make('div', 'glow-blob');
        const dot = make('div', 'gen-cursor-dot');
        const ring = make('div', 'gen-cursor-ring');
        const outer = make('div', 'gen-cursor-outer');

        const ctx = canvas.getContext('2d');
        let W, H;
        const resize = () => { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; };
        resize();
        window.addEventListener('resize', resize);

        let mx = W / 2, my = H / 2;
        let r1x = mx, r1y = my, r2x = mx, r2y = my, bx = mx, by = my;
        const onMove = e => { mx = e.clientX; my = e.clientY; };
        document.addEventListener('mousemove', onMove);

        // cursor RAF
        let cursorId;
        const tickCursor = () => {
            dot.style.left = mx + 'px'; dot.style.top = my + 'px';
            r1x += (mx - r1x) * 0.15; r1y += (my - r1y) * 0.15;
            ring.style.left = r1x + 'px'; ring.style.top = r1y + 'px';
            r2x += (mx - r2x) * 0.07; r2y += (my - r2y) * 0.07;
            outer.style.left = r2x + 'px'; outer.style.top = r2y + 'px';
            bx += (mx - bx) * 0.04; by += (my - by) * 0.04;
            blob.style.left = bx + 'px'; blob.style.top = by + 'px';
            cursorId = requestAnimationFrame(tickCursor);
        };
        tickCursor();

        document.body.classList.add('custom-cursor-active');

        // particles
        const COLS = ['rgba(155,93,229,', 'rgba(199,125,255,', 'rgba(90,24,154,', 'rgba(224,64,251,', 'rgba(130,50,210,'];
        class Particle {
            constructor() { this.init(); }
            init() {
                this.x = Math.random() * W; this.y = Math.random() * H;
                this.r = Math.random() * 1.5 + 0.2;
                this.vx = (Math.random() - 0.5) * 0.28; this.vy = (Math.random() - 0.5) * 0.28;
                this.a = Math.random() * 0.5 + 0.08;
                this.c = COLS[Math.floor(Math.random() * COLS.length)];
                this.ph = Math.random() * Math.PI * 2; this.ps = 0.006 + Math.random() * 0.01;
            }
            step() {
                this.ph += this.ps;
                const dx = mx - this.x, dy = my - this.y, d = Math.hypot(dx, dy);
                if (d < 190) { this.vx -= (dx / d) * 0.02; this.vy -= (dy / d) * 0.02; }
                this.vx *= 0.983; this.vy *= 0.983;
                this.x += this.vx; this.y += this.vy;
                if (this.x < -10 || this.x > W + 10 || this.y < -10 || this.y > H + 10) this.init();
            }
            draw() {
                const a = this.a * (0.6 + 0.4 * Math.sin(this.ph));
                ctx.beginPath(); ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
                ctx.fillStyle = this.c + a + ')'; ctx.fill();
            }
        }
        const parts = [];
        for (let i = 0; i < 220; i++) parts.push(new Particle());

        const drawWeb = () => {
            for (let i = 0; i < parts.length; i++) {
                for (let j = i + 1; j < parts.length; j++) {
                    const d = Math.hypot(parts[i].x - parts[j].x, parts[i].y - parts[j].y);
                    if (d < 125) {
                        ctx.beginPath(); ctx.moveTo(parts[i].x, parts[i].y); ctx.lineTo(parts[j].x, parts[j].y);
                        ctx.strokeStyle = `rgba(155,93,229,${(1 - d / 125) * 0.14})`;
                        ctx.lineWidth = 0.35; ctx.stroke();
                    }
                }
            }
        };

        let loopId;
        const loop = () => {
            ctx.clearRect(0, 0, W, H);
            parts.forEach(p => { p.step(); p.draw(); });
            drawWeb();
            loopId = requestAnimationFrame(loop);
        };
        loop();

        return () => {
            document.body.classList.remove('custom-cursor-active');
            cancelAnimationFrame(cursorId);
            cancelAnimationFrame(loopId);
            window.removeEventListener('resize', resize);
            document.removeEventListener('mousemove', onMove);
            [canvas, grain, blob, dot, ring, outer].forEach(el => el.remove());
        };
    }, []);

    return null;
};

export default ParticleCursorEffect;
