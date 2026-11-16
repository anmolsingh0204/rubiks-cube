#!/usr/bin/env python3
"""Generate glassmorphism gallery index.html for GitHub Pages"""

gallery_html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>3D Rubik's Cube Gallery — Interactive N×N×N Cubes</title>
  <meta name="description" content="Interactive 3D Rubik's cubes (2×2×2 through 5×5×5) with shuffle/solve animation, exploded views, and 3D printing exports.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0a0a0f;
      --bg-elevated: #12121a;
      --fg: #f0f0f5;
      --fg-muted: #888899;
      --accent: #00d4aa;
      --accent-dim: #00d4aa33;
      --card-bg: rgba(255,255,255,0.04);
      --card-border: rgba(255,255,255,0.08);
      --glass-bg: rgba(255,255,255,0.03);
      --glass-border: rgba(255,255,255,0.1);
      --shadow: 0 20px 60px -10px rgba(0,0,0,0.5);
      --radius: 16px;
      --radius-sm: 10px;
    }
    @media (prefers-color-scheme: light) {
      :root {
        --bg: #f5f5f8;
        --bg-elevated: #ffffff;
        --fg: #1a1a2e;
        --fg-muted: #666677;
        --accent: #009977;
        --accent-dim: #00997722;
        --card-bg: rgba(255,255,255,0.8);
        --card-border: rgba(0,0,0,0.06);
        --glass-bg: rgba(255,255,255,0.7);
        --glass-border: rgba(0,0,0,0.08);
        --shadow: 0 20px 60px -10px rgba(0,0,0,0.1);
      }
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      font-family: 'Inter', system-ui, sans-serif;
      background: var(--bg);
      color: var(--fg);
      min-height: 100vh;
      overflow-x: hidden;
      line-height: 1.6;
    }
    /* Animated background */
    .bg-layer {
      position: fixed; inset: 0; z-index: -1; pointer-events: none;
      background: 
        radial-gradient(ellipse 80% 50% at 20% 10%, var(--accent-dim) 0%, transparent 50%),
        radial-gradient(ellipse 60% 40% at 80% 90%, #6366f133 0%, transparent 50%),
        radial-gradient(ellipse 40% 30% at 50% 50%, #ec489922 0%, transparent 60%);
      animation: bgShift 20s ease-in-out infinite alternate;
    }
    @keyframes bgShift {
      0% { transform: translate(0, 0) scale(1); opacity: 0.6; }
      50% { transform: translate(-2%, 2%) scale(1.02); opacity: 0.8; }
      100% { transform: translate(2%, -1%) scale(0.98); opacity: 0.6; }
    }
    .grid-overlay {
      position: fixed; inset: 0; z-index: -1; pointer-events: none; opacity: 0.03;
      background-image: 
        linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px);
      background-size: 60px 60px;
      animation: gridMove 30s linear infinite;
    }
    @keyframes gridMove { 0% { transform: translate(0,0); } 100% { transform: translate(60px,60px); } }
    .container { max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }
    /* Header */
    header { text-align: center; padding: 4rem 0 3rem; position: relative; }
    .badge {
      display: inline-flex; align-items: center; gap: 0.5rem;
      padding: 0.5rem 1rem; border-radius: 100px;
      background: var(--glass-bg); border: 1px solid var(--glass-border);
      backdrop-filter: blur(10px); font-size: 0.85rem; font-weight: 500;
      color: var(--accent); margin-bottom: 1.5rem;
      animation: fadeInUp 0.8s ease-out;
    }
    .badge::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: pulse 2s ease-in-out infinite; }
    @keyframes pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.2); } }
    h1 { font-family: 'Space Grotesk', sans-serif; font-size: clamp(2.5rem, 6vw, 4rem); font-weight: 700; letter-spacing: -0.03em; line-height: 1.1; margin-bottom: 1rem; background: linear-gradient(135deg, var(--fg) 0%, var(--accent) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; animation: fadeInUp 0.8s ease-out 0.1s both; }
    .subtitle { font-size: clamp(1.1rem, 2.5vw, 1.35rem); color: var(--fg-muted); max-width: 600px; margin: 0 auto; animation: fadeInUp 0.8s ease-out 0.2s both; }
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    /* Stats bar */
    .stats { display: flex; justify-content: center; gap: 2.5rem; margin-top: 3rem; flex-wrap: wrap; animation: fadeInUp 0.8s ease-out 0.3s both; }
    .stat { text-align: center; }
    .stat-value { font-family: 'Space Grotesk', sans-serif; font-size: 2.5rem; font-weight: 700; color: var(--accent); line-height: 1; }
    .stat-label { font-size: 0.85rem; color: var(--fg-muted); margin-top: 0.25rem; }
    /* Sections */
    section { margin-bottom: 4rem; }
    .section-header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem; }
    .section-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.75rem; font-weight: 600; }
    .section-link { color: var(--accent); text-decoration: none; font-weight: 500; font-size: 0.95rem; transition: opacity 0.2s; }
    .section-link:hover { opacity: 0.7; }
    /* Cube Grid */
    .cube-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem; }
    .cube-card {
      background: var(--card-bg); border: 1px solid var(--card-border);
      border-radius: var(--radius); overflow: hidden;
      backdrop-filter: blur(20px); transition: transform 0.3s cubic-bezier(0.2,0.8,0.2,1), box-shadow 0.3s, border-color 0.3s;
      animation: fadeInUp 0.6s ease-out both;
    }
    .cube-card:hover { transform: translateY(-8px); box-shadow: var(--shadow); border-color: var(--accent-dim); }
    .cube-preview {
      aspect-ratio: 1; background: linear-gradient(135deg, rgba(255,255,255,0.02) 0%, rgba(0,0,0,0.1) 100%);
      position: relative; overflow: hidden;
    }
    .cube-preview iframe { width: 100%; height: 100%; border: none; }
    .cube-info { padding: 1.25rem; }
    .cube-name { font-family: 'Space Grotesk', sans-serif; font-size: 1.15rem; font-weight: 600; margin-bottom: 0.25rem; }
    .cube-meta { display: flex; gap: 1rem; font-size: 0.8rem; color: var(--fg-muted); flex-wrap: wrap; margin-bottom: 1rem; }
    .cube-meta span { display: flex; align-items: center; gap: 0.35rem; }
    .cube-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .btn { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.55rem 1rem; border-radius: var(--radius-sm); font-size: 0.85rem; font-weight: 500; text-decoration: none; transition: all 0.2s; border: 1px solid transparent; cursor: pointer; }
    .btn-primary { background: var(--accent); color: var(--bg); }
    .btn-primary:hover { background: #00e8bb; transform: translateY(-2px); box-shadow: 0 8px 20px -5px var(--accent); }
    .btn-secondary { background: var(--glass-bg); border-color: var(--glass-border); color: var(--fg); backdrop-filter: blur(10px); }
    .btn-secondary:hover { background: var(--card-bg); border-color: var(--accent-dim); color: var(--accent); }
    .btn-sm { padding: 0.4rem 0.8rem; font-size: 0.8rem; }
    /* Feature cards */
    .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.5rem; }
    .feature-card { background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: var(--radius); padding: 2rem; backdrop-filter: blur(20px); transition: all 0.3s; }
    .feature-card:hover { border-color: var(--accent-dim); transform: translateY(-4px); }
    .feature-icon { width: 48px; height: 48px; border-radius: 12px; background: var(--accent-dim); display: flex; align-items: center; justify-content: center; margin-bottom: 1rem; color: var(--accent); }
    .feature-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; }
    .feature-desc { color: var(--fg-muted); font-size: 0.95rem; line-height: 1.7; }
    /* Footer */
    footer { text-align: center; padding: 3rem 0; border-top: 1px solid var(--card-border); color: var(--fg-muted); font-size: 0.9rem; }
    footer a { color: var(--accent); text-decoration: none; }
    footer a:hover { text-decoration: underline; }
    /* Scroll animations */
    .reveal { opacity: 0; transform: translateY(30px); transition: opacity 0.6s ease-out, transform 0.6s cubic-bezier(0.2,0.8,0.2,1); }
    .reveal.visible { opacity: 1; transform: translateY(0); }
    /* Reduced motion */
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
      .bg-layer, .grid-overlay { animation: none; }
    }
  </style>
</head>
<body>
  <div class="bg-layer"></div>
  <div class="grid-overlay"></div>
  <div class="container">
    <header>
      <div class="badge">Live Demo · GitHub Pages</div>
      <h1>3D Rubik's Cube Gallery</h1>
      <p class="subtitle">Interactive N×N×N cubes with shuffle/solve animation, exploded views, and 3D printing exports — built with Plotly.js and Python</p>
      <div class="stats">
        <div class="stat"><div class="stat-value">5</div><div class="stat-label">Cube Sizes (2–5)</div></div>
        <div class="stat"><div class="stat-value">4</div><div class="stat-label">View Modes</div></div>
        <div class="stat"><div class="stat-value">3</div><div class="stat-label">Export Formats</div></div>
        <div class="stat"><div class="stat-value">60fps</div><div class="stat-label">WebGL Rendering</div></div>
      </div>
    </header>

    <section class="reveal">
      <div class="section-header">
        <h2 class="section-title">Interactive Cubes</h2>
        <a href="#static" class="section-link">View Static →</a>
      </div>
      <div class="cube-grid" id="interactive-grid">
        <!-- Populated by JS -->
      </div>
    </section>

    <section id="static" class="reveal">
      <div class="section-header">
        <h2 class="section-title">Static Previews</h2>
        <a href="#exploded" class="section-link">Exploded Views →</a>
      </div>
      <div class="cube-grid" id="static-grid">
        <!-- Populated by JS -->
      </div>
    </section>

    <section id="exploded" class="reveal">
      <div class="section-header">
        <h2 class="section-title">Exploded Views</h2>
      </div>
      <div class="cube-grid" id="exploded-grid">
        <!-- Populated by JS -->
      </div>
    </section>

    <section class="reveal">
      <div class="section-header">
        <h2 class="section-title">Features</h2>
      </div>
      <div class="feature-grid">
        <div class="feature-card">
          <div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg></div>
          <h3 class="feature-title">N×N×N Cubes (2–5)</h3>
          <p class="feature-desc">Generate Pocket Cube (2×2×2) through Professor's Cube (5×5×5) with correct cubie geometry and color mapping.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg></div>
          <h3 class="feature-title">Shuffle & Animated Solve</h3>
          <p class="feature-desc">Scramble with configurable moves, then watch the automated solve animation with adjustable speed (0.5×–2.0×).</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg></div>
          <h3 class="feature-title">Exploded View</h3>
          <p class="feature-desc">Separate all cubies to see interior faces (dark gray) and understand the 3D structure of every piece.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg></div>
          <h3 class="feature-title">STL/OBJ Export</h3>
          <p class="feature-desc">Multi-color 3D printable files compatible with Bambu Lab AMS, Prusa MMU, and other multi-material systems.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 6v6l4 2"></path></svg></div>
          <h3 class="feature-title">Standard Notation</h3>
          <p class="feature-desc">Full move support: R, U, F, L, D, B with prime (') and double (2) modifiers. Scramble history preserved.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg></div>
          <h3 class="feature-title">Dark/Light Mode</h3>
          <p class="feature-desc">Automatic theme detection with glassmorphism UI that adapts to system preference — no flash, no toggle needed.</p>
        </div>
      </div>
    </section>

    <footer>
      <p>Generated with <a href="https://github.com/anmolsingh0204/rubiks-cube">rubiks-cube</a> · <a href="https://github.com/anmolsingh0204/rubiks-cube">Source on GitHub</a> · MIT License</p>
    </footer>
  </div>

  <script>
    // Cube data
    const cubes = [
      { size: 2, name: "2×2×2 Pocket Cube", cubies: 8, stickers: 24 },
      { size: 3, name: "3×3×3 Standard", cubies: 26, stickers: 54 },
      { size: 4, name: "4×4×4 Rubik's Revenge", cubies: 56, stickers: 96 },
      { size: 5, name: "5×5×5 Professor's Cube", cubies: 98, stickers: 150 }
    ];

    function createCard(cube, type) {
      const isInteractive = type === 'interactive';
      const isExploded = type === 'exploded';
      const suffix = isInteractive ? '_interactive' : (isExploded ? '_exploded' : '');
      const explodedLabel = isExploded ? 'exploded' : '';
      const href = `rubiks_${cube.size}x${cube.size}x${cube.size}${suffix}.html`;
      const stlHref = `rubiks_${cube.size}x${cube.size}x${cube.size}${suffix}.stl`;
      const objHref = `rubiks_${cube.size}x${cube.size}x${cube.size}${suffix}.obj`;
      const hasExports = !isInteractive; // Static and exploded have exports

      return `
        <article class="cube-card" style="animation-delay: ${cubes.indexOf(cube) * 80}ms">
          <div class="cube-preview">
            <iframe src="${href}" loading="lazy" title="${cube.name} ${explodedLabel}"></iframe>
          </div>
          <div class="cube-info">
            <h3 class="cube-name">${cube.name}${explodedLabel ? ' (Exploded)' : ''}</h3>
            <div class="cube-meta">
              <span>${cube.cubies} cubies</span>
              <span>${cube.stickers} stickers</span>
              <span>${cube.size}³</span>
            </div>
            <div class="cube-actions">
              <a href="${href}" class="btn btn-primary" target="_blank" rel="noopener">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                ${isInteractive ? 'Open Interactive' : 'View'}
              </a>
              ${hasExports ? `
                <a href="${stlHref}" class="btn btn-secondary btn-sm" download>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg> STL
                </a>
                <a href="${objHref}" class="btn btn-secondary btn-sm" download>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg> OBJ
                </a>
              ` : ''}
            </div>
          </div>
        </article>
      `;
    }

    // Populate grids
    document.getElementById('interactive-grid').innerHTML = cubes.map(c => createCard(c, 'interactive')).join('');
    document.getElementById('static-grid').innerHTML = cubes.map(c => createCard(c, 'static')).join('');
    document.getElementById('exploded-grid').innerHTML = cubes.map(c => createCard(c, 'exploded')).join('');

    // Scroll reveal
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

    // Stagger card animations
    document.querySelectorAll('.cube-card').forEach((card, i) => {
      card.style.animationDelay = `${(i % 4) * 80}ms`;
    });
  </script>
</body>
</html>'''

with open('docs/index.html', 'w') as f:
    f.write(gallery_html)

print("Generated docs/index.html")
