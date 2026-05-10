import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import './Landing.css';

const Landing = () => {
    const canvasRef = useRef(null);
    const dotRef = useRef(null);
    const ringRef = useRef(null);
    const roRef = useRef(null);
    const blobRef = useRef(null);
    const titleRef = useRef(null);

    useEffect(() => {
        // ── Cursor ──
        const dot = dotRef.current;
        const ring = ringRef.current;
        const ro = roRef.current;
        const blob = blobRef.current;

        let mx = window.innerWidth / 2, my = window.innerHeight / 2;
        let r1x = mx, r1y = my, r2x = mx, r2y = my, bx = mx, by = my;

        const handleMouseMove = (e) => {
            mx = e.clientX;
            my = e.clientY;
        };
        document.addEventListener('mousemove', handleMouseMove);

        let animationFrameId;
        const tick = () => {
            if (dot && ring && ro && blob) {
                dot.style.left = mx + 'px'; dot.style.top = my + 'px';
                r1x += (mx - r1x) * 0.15; r1y += (my - r1y) * 0.15;
                r2x += (mx - r2x) * 0.07; r2y += (my - r2y) * 0.07;
                bx += (mx - bx) * 0.04; by += (my - by) * 0.04;
                ring.style.left = r1x + 'px'; ring.style.top = r1y + 'px';
                ro.style.left = r2x + 'px'; ro.style.top = r2y + 'px';
                blob.style.left = bx + 'px'; blob.style.top = by + 'px';
            }
            animationFrameId = requestAnimationFrame(tick);
        };
        tick();

        // ── Particles ──
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let W, H;
        let parts = [];

        const resize = () => {
            W = canvas.width = window.innerWidth;
            H = canvas.height = window.innerHeight;
        };
        resize();
        window.addEventListener('resize', resize);

        const COLS = ['rgba(155,93,229,', 'rgba(199,125,255,', 'rgba(90,24,154,', 'rgba(224,64,251,', 'rgba(130,50,210,'];

        class P {
            constructor() { this.init(); }
            init() {
                this.x = Math.random() * W; this.y = Math.random() * H;
                this.r = Math.random() * 1.5 + 0.2;
                this.vx = (Math.random() - .5) * .28; this.vy = (Math.random() - .5) * .28;
                this.a = Math.random() * .5 + .08;
                this.c = COLS[Math.floor(Math.random() * COLS.length)];
                this.ph = Math.random() * Math.PI * 2;
                this.ps = .006 + Math.random() * .01;
            }
            step() {
                this.ph += this.ps;
                const dx = mx - this.x, dy = my - this.y, d = Math.hypot(dx, dy);
                if (d < 190) { this.vx -= dx / d * .02; this.vy -= dy / d * .02; }
                this.vx *= .983; this.vy *= .983;
                this.x += this.vx; this.y += this.vy;
                if (this.x < -10 || this.x > W + 10 || this.y < -10 || this.y > H + 10) this.init();
            }
            draw() {
                const a = this.a * (0.6 + 0.4 * Math.sin(this.ph));
                ctx.beginPath(); ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
                ctx.fillStyle = this.c + a + ')'; ctx.fill();
            }
        }

        for (let i = 0; i < 220; i++) parts.push(new P());

        const web = () => {
            for (let i = 0; i < parts.length; i++) {
                for (let j = i + 1; j < parts.length; j++) {
                    const d = Math.hypot(parts[i].x - parts[j].x, parts[i].y - parts[j].y);
                    if (d < 125) {
                        ctx.beginPath();
                        ctx.moveTo(parts[i].x, parts[i].y);
                        ctx.lineTo(parts[j].x, parts[j].y);
                        ctx.strokeStyle = `rgba(155,93,229,${(1 - d / 125) * .14})`;
                        ctx.lineWidth = .35; ctx.stroke();
                    }
                }
            }
        };

        let loopId;
        const loop = () => {
            if (ctx) {
                ctx.clearRect(0, 0, W, H);
                parts.forEach(p => { p.step(); p.draw(); });
                web();
            }
            loopId = requestAnimationFrame(loop);
        };
        loop();

        // ── Glitch bursts ──
        const title = titleRef.current;
        let burstTimeout;
        let scheduleTimeout;

        const burst = () => {
            if (title) {
                title.classList.add('burst');
                burstTimeout = setTimeout(() => {
                    if (title) title.classList.remove('burst');
                }, 300);
            }
        };

        const schedule = () => {
            scheduleTimeout = setTimeout(() => {
                burst();
                schedule();
            }, 2800 + Math.random() * 4200);
        };
        setTimeout(schedule, 1800);

        // ── Cleanup ──
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('resize', resize);
            cancelAnimationFrame(animationFrameId);
            cancelAnimationFrame(loopId);
            clearTimeout(burstTimeout);
            clearTimeout(scheduleTimeout);
        };
    }, []);

    return (
        <div className="landing-root">
            <canvas id="canvas" ref={canvasRef}></canvas>
            <div className="grain"></div>
            <div className="vignette"></div>
            <div className="glow-blob" id="blob" ref={blobRef}></div>

            <div className="cursor-dot" id="dot" ref={dotRef}></div>
            <div className="cursor-ring" id="ring" ref={ringRef}></div>
            <div className="cursor-ring-outer" id="ringOuter" ref={roRef}></div>

            <div className="stage">
                <h1 className="title" id="title" data-text="RESTRUCT WARP" ref={titleRef}>
                    RESTRUCT <span className="ai">WARP</span>
                </h1>
                <p className="tagline">Intelligence · Emerging · Now</p>
            </div>

            <Link to="/" className="enter">Enter</Link>
        </div>
    );
};

export default Landing;
