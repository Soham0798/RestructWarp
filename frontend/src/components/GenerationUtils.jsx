import React, { useState, useRef, useEffect } from 'react';
import { Copy, Check } from 'lucide-react';

/**
 * Strip Claude scratchpad / markdown fences from streamed HTML.
 * Returns only the raw HTML starting from <!DOCTYPE or <html>.
 */
export function stripHtmlPreamble(raw) {
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

    // 4b. Fix AI over-escaping backticks in JSX template literals
    if (cleaned.includes('\\`')) {
        cleaned = cleaned.replace(/\\`/g, '`');
    }

    // 5. Fix Lucide icons
    if (cleaned.includes('lucide') && !cleaned.includes('lucide-react')) {
        cleaned = cleaned.replace(
            /<script[^>]*src=["'][^"']*lucide[^"']*["'][^>]*>\s*<\/script>/gi,
            ''
        );

        const lucideReactShim = `
<script>
(function(){
  var iconPaths = {
    Home:[["path",{d:"M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"}],["path",{d:"M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"}]],
    TrendingUp:[["polyline",{points:"22 7 13.5 15.5 8.5 10.5 2 17"}],["polyline",{points:"16 7 22 7 22 13"}]],
    TrendingDown:[["polyline",{points:"22 17 13.5 8.5 8.5 13.5 2 7"}],["polyline",{points:"16 17 22 17 22 11"}]],
    Wallet:[["path",{d:"M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"}],["path",{d:"M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"}]],
    Settings:[["path",{d:"M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"}],["circle",{cx:"12",cy:"12",r:"3"}]],
    Menu:[["line",{x1:"4",x2:"20",y1:"12",y2:"12"}],["line",{x1:"4",x2:"20",y1:"6",y2:"6"}],["line",{x1:"4",x2:"20",y1:"18",y2:"18"}]],
    X:[["path",{d:"M18 6 6 18"}],["path",{d:"m6 6 12 12"}]],
    ChevronRight:[["path",{d:"m9 18 6-6-6-6"}]],
    ChevronDown:[["path",{d:"m6 9 6 6 6-6"}]],
    Plus:[["path",{d:"M5 12h14"}],["path",{d:"M12 5v14"}]],
    ArrowUpRight:[["path",{d:"M7 7h10v10"}],["path",{d:"M7 17 17 7"}]],
    ArrowDownRight:[["path",{d:"m7 7 10 10"}],["path",{d:"M17 7v10H7"}]],
    Loader2:[["path",{d:"M21 12a9 9 0 1 1-6.219-8.56"}]],
    CircleDollarSign:[["circle",{cx:"12",cy:"12",r:"10"}],["path",{d:"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"}],["path",{d:"M12 18V6"}]],
    Calendar:[["path",{d:"M8 2v4"}],["path",{d:"M16 2v4"}],["rect",{width:"18",height:"18",x:"3",y:"4",rx:"2"}],["path",{d:"M3 10h18"}]],
    Banknote:[["rect",{width:"20",height:"12",x:"2",y:"6",rx:"2"}],["circle",{cx:"12",cy:"12",r:"2"}],["path",{d:"M6 12h.01M18 12h.01"}]],
    Percent:[["line",{x1:"19",x2:"5",y1:"5",y2:"19"}],["circle",{cx:"6.5",cy:"6.5",r:"2.5"}],["circle",{cx:"17.5",cy:"17.5",r:"2.5"}]],
    ChartLine:[["path",{d:"M3 3v16a2 2 0 0 0 2 2h16"}],["path",{d:"m19 9-5 5-4-4-3 3"}]],
    Package:[["path",{d:"m7.5 4.27 9 5.15"}],["path",{d:"M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"}],["path",{d:"m3.3 7 8.7 5 8.7-5"}],["path",{d:"M12 22V12"}]],
    Gauge:[["path",{d:"m12 14 4-4"}],["path",{d:"M3.34 19a10 10 0 1 1 17.32 0"}]],
    PiggyBank:[["path",{d:"M19 5c-1.5 0-2.8 1.4-3 2-3.5-1.5-11-.3-11 5 0 1.8 0 3 2 4.5V20h4v-2h3v2h4v-4c1-.5 1.7-1 2-2h2v-4h-2c0-1-.5-1.5-1-2"}],["path",{d:"M2 9v1c0 1.1.9 2 2 2h1"}],["path",{d:"M16 11h.01"}]],
    Search:[["circle",{cx:"11",cy:"11",r:"8"}],["path",{d:"m21 21-4.3-4.3"}]],
    Bell:[["path",{d:"M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"}],["path",{d:"M10.3 21a1.94 1.94 0 0 0 3.4 0"}]],
    Eye:[["path",{d:"M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"}],["circle",{cx:"12",cy:"12",r:"3"}]],
    EyeOff:[["path",{d:"M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"}],["path",{d:"M14.084 14.158a3 3 0 0 1-4.242-4.242"}],["path",{d:"M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"}],["path",{d:"m2 2 20 20"}]],
    Edit:[["path",{d:"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"}]],
    Trash2:[["path",{d:"M3 6h18"}],["path",{d:"M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"}],["path",{d:"M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"}],["line",{x1:"10",x2:"10",y1:"11",y2:"17"}],["line",{x1:"14",x2:"14",y1:"11",y2:"17"}]],
    DollarSign:[["line",{x1:"12",x2:"12",y1:"2",y2:"22"}],["path",{d:"M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"}]],
    BarChart3:[["path",{d:"M3 3v16a2 2 0 0 0 2 2h16"}],["path",{d:"M18 17V9"}],["path",{d:"M13 17V5"}],["path",{d:"M8 17v-3"}]],
    Activity:[["polyline",{points:"22 12 18 12 15 21 9 3 6 12 2 12"}]],
    Clock:[["circle",{cx:"12",cy:"12",r:"10"}],["polyline",{points:"12 6 12 12 16 14"}]],
    Check:[["path",{d:"M20 6 9 17l-5-5"}]],
    Filter:[["polygon",{points:"22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"}]],
    Download:[["path",{d:"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"}],["polyline",{points:"7 10 12 15 17 10"}],["line",{x1:"12",x2:"12",y1:"15",y2:"3"}]],
    RefreshCw:[["path",{d:"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"}],["path",{d:"M21 3v5h-5"}],["path",{d:"M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"}],["path",{d:"M3 21v-5h5"}]],
    Info:[["circle",{cx:"12",cy:"12",r:"10"}],["path",{d:"M12 16v-4"}],["path",{d:"M12 8h.01"}]],
    AlertTriangle:[["path",{d:"m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"}],["path",{d:"M12 9v4"}],["path",{d:"M12 17h.01"}]],
    Star:[["path",{d:"M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"}]],
    Users:[["path",{d:"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"}],["circle",{cx:"9",cy:"7",r:"4"}],["path",{d:"M22 21v-2a4 4 0 0 0-3-3.87"}],["path",{d:"M16 3.13a4 4 0 0 1 0 7.75"}]],
    CreditCard:[["rect",{width:"20",height:"14",x:"2",y:"5",rx:"2"}],["line",{x1:"2",x2:"22",y1:"10",y2:"10"}]],
    ArrowUp:[["path",{d:"m5 12 7-7 7 7"}],["path",{d:"M12 19V5"}]],
    ArrowDown:[["path",{d:"m19 12-7 7-7-7"}],["path",{d:"M12 5v14"}]],
    Briefcase:[["path",{d:"M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"}],["rect",{width:"20",height:"14",x:"2",y:"6",rx:"2"}]],
    Target:[["circle",{cx:"12",cy:"12",r:"10"}],["circle",{cx:"12",cy:"12",r:"6"}],["circle",{cx:"12",cy:"12",r:"2"}]],
    Zap:[["path",{d:"M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"}]],
    LineChart:[["path",{d:"M3 3v16a2 2 0 0 0 2 2h16"}],["path",{d:"m19 9-5 5-4-4-3 3"}]],
    PieChart:[["path",{d:"M21.21 15.89A10 10 0 1 1 8 2.83"}],["path",{d:"M22 12A10 10 0 0 0 12 2v10z"}]],
    Landmark:[["line",{x1:"3",x2:"21",y1:"22",y2:"22"}],["line",{x1:"6",x2:"6",y1:"18",y2:"11"}],["line",{x1:"10",x2:"10",y1:"18",y2:"11"}],["line",{x1:"14",x2:"14",y1:"18",y2:"11"}],["line",{x1:"18",x2:"18",y1:"18",y2:"11"}],["polygon",{points:"12 2 20 7 4 7"}]],
    LogOut:[["path",{d:"M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"}],["polyline",{points:"16 17 21 12 16 7"}],["line",{x1:"21",x2:"9",y1:"12",y2:"12"}]],
    User:[["path",{d:"M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"}],["circle",{cx:"12",cy:"7",r:"4"}]],
    FileText:[["path",{d:"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"}],["path",{d:"M14 2v4a2 2 0 0 0 2 2h4"}],["path",{d:"M10 9H8"}],["path",{d:"M16 13H8"}],["path",{d:"M16 17H8"}]],
    MoreVertical:[["circle",{cx:"12",cy:"12",r:"1"}],["circle",{cx:"12",cy:"5",r:"1"}],["circle",{cx:"12",cy:"19",r:"1"}]],
    ExternalLink:[["path",{d:"M15 3h6v6"}],["path",{d:"M10 14 21 3"}],["path",{d:"M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"}]],
    Copy:[["rect",{width:"14",height:"14",x:"8",y:"8",rx:"2",ry:"2"}],["path",{d:"M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"}]],
    Inbox:[["polyline",{points:"22 12 16 12 14 15 10 15 8 12 2 12"}],["path",{d:"M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"}]],
    HelpCircle:[["circle",{cx:"12",cy:"12",r:"10"}],["path",{d:"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"}],["path",{d:"M12 17h.01"}]],
    Layers:[["path",{d:"m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.84Z"}],["path",{d:"m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"}],["path",{d:"m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"}]],
    Globe:[["circle",{cx:"12",cy:"12",r:"10"}],["path",{d:"M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"}],["path",{d:"M2 12h20"}]],
    MapPin:[["path",{d:"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"}],["circle",{cx:"12",cy:"10",r:"3"}]],
    Maximize2:[["polyline",{points:"15 3 21 3 21 9"}],["polyline",{points:"9 21 3 21 3 15"}],["line",{x1:"21",x2:"14",y1:"3",y2:"10"}],["line",{x1:"3",x2:"10",y1:"21",y2:"14"}]],
    Minimize2:[["polyline",{points:"4 14 10 14 10 20"}],["polyline",{points:"20 10 14 10 14 4"}],["line",{x1:"14",x2:"21",y1:"10",y2:"3"}],["line",{x1:"3",x2:"10",y1:"21",y2:"14"}]],
    Moon:[["path",{d:"M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"}]],
    Sun:[["circle",{cx:"12",cy:"12",r:"4"}],["path",{d:"M12 2v2"}],["path",{d:"M12 20v2"}],["path",{d:"m4.93 4.93 1.41 1.41"}],["path",{d:"m17.66 17.66 1.41 1.41"}],["path",{d:"M2 12h2"}],["path",{d:"M20 12h2"}],["path",{d:"m6.34 17.66-1.41 1.41"}],["path",{d:"m19.07 4.93-1.41 1.41"}]],
    Shield:[["path",{d:"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"}]],
    Lock:[["rect",{width:"18",height:"11",x:"3",y:"11",rx:"2",ry:"2"}],["path",{d:"M7 11V7a5 5 0 0 1 10 0v4"}]],
  };
  var h=React.createElement;
  window.lucide={icons:{}};
  Object.keys(iconPaths).forEach(function(name){
    var paths=iconPaths[name];
    window.lucide.icons[name]=function LucideIcon(props){
      props=props||{};
      var size=props.size||24;
      var color=props.color||'currentColor';
      var sw=props.strokeWidth||2;
      var cn=props.className||'';
      var children=paths.map(function(p,i){
        return h(p[0],Object.assign({key:i},p[1]));
      });
      return h('svg',{
        xmlns:'http://www.w3.org/2000/svg',
        width:size,height:size,viewBox:'0 0 24 24',
        fill:'none',stroke:color,strokeWidth:sw,
        strokeLinecap:'round',strokeLinejoin:'round',
        className:cn,style:props.style
      },children);
    };
  });
})();
</script>`;
        if (cleaned.includes('</head>')) {
            cleaned = cleaned.replace('</head>', lucideReactShim + '\n</head>');
        }
    }

    const closingHtmlIndex = cleaned.toLowerCase().lastIndexOf('</html>');
    if (closingHtmlIndex !== -1) {
        cleaned = cleaned.substring(0, closingHtmlIndex + 7);
    }

    const isComplete = cleaned.toLowerCase().includes('</html>') || cleaned.toLowerCase().includes('</body>');
    const hasStyle = cleaned.toLowerCase().includes('<style');
    const isStyleComplete = !hasStyle || cleaned.toLowerCase().includes('</style>');
    
    if (cleaned.length > 100 && (!isComplete || !isStyleComplete)) {
        const warning = `
            <div style="position:fixed; bottom:0; left:0; width:100%; background:#ef4444; color:white; padding:12px; z-index:99999; text-align:center; font-family:sans-serif; font-size:14px; font-weight:bold; box-shadow:0 -4px 10px rgba(0,0,0,0.3);">
                ⚠️ Warning: AI generation stopped prematurely. Output was truncated.
            </div>
        `;
        if (hasStyle && !isStyleComplete) cleaned += '\\n</style>';
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

export function CopyButton({ text, size = 14 }) {
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

export function StreamingView({ buffer, isStreaming, type }) {
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

export function PreviewIframe({ html, previewKey }) {
    const [blobUrl, setBlobUrl] = useState(null);
    const containerRef = useRef(null);
    const [scale, setScale] = useState(1);

    useEffect(() => {
        if (!containerRef.current) return;
        const observer = new ResizeObserver(entries => {
            for (let entry of entries) {
                const { width } = entry.contentRect;
                if (width > 0 && width < 1280) {
                    setScale(width / 1280);
                } else {
                    setScale(1);
                }
            }
        });
        observer.observe(containerRef.current);
        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        if (!html) { setBlobUrl(null); return; }

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
                
                const originalConsoleError = console.error;
                console.error = function() {
                    const args = Array.from(arguments);
                    originalConsoleError.apply(console, args);
                    if (args[0] && typeof args[0] === 'string' && (args[0].includes('React') || args[0].includes('Babel') || args[0].includes('SyntaxError'))) {
                        window.onerror(args.join(' '), window.location.href, 'Unknown');
                    }
                };
            <\/script>
        `;

        let finalHtml = html;
        if (finalHtml.includes('<head>')) {
            finalHtml = finalHtml.replace('<head>', '<head>' + errorScript);
        } else if (finalHtml.includes('<html>')) {
            finalHtml = finalHtml.replace('<html>', '<html>' + errorScript);
        } else {
            finalHtml = errorScript + finalHtml;
        }

        const blob = new Blob([finalHtml], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        setBlobUrl(url);

        return () => URL.revokeObjectURL(url);
    }, [html, previewKey]);

    return (
        <div ref={containerRef} style={{ width: '100%', height: '100%', overflow: 'hidden', position: 'relative', background: '#0d1117' }}>
            <div style={{
                width: '1280px',
                height: `${scale > 0 ? 100 / scale : 100}%`,
                transform: `scale(${scale})`,
                transformOrigin: 'top left',
                position: 'absolute',
                top: 0,
                left: 0
            }}>
                <iframe
                    key={previewKey}
                    src={blobUrl}
                    title="Live Preview"
                    style={{ width: '100%', height: '100%', border: 'none', background: '#fff' }}
                    sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"
                />
            </div>
        </div>
    );
}
