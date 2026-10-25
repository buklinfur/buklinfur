"""Generate the profile banner: a terminal that runs a route planner over a contour map.

Run from the repo root. Produces assets/banner-dark.svg and assets/banner-light.svg.
Pass --static to also write *-static.svg previews with all animations in their final state.
"""
import math
import sys

W, H = 880, 300
WIN_X, WIN_Y, WIN_W, WIN_H = 8, 8, W - 16, H - 16
BAR_H = 34
MAP_X, MAP_Y, MAP_W, MAP_H = 520, 58, 334, 216

THEMES = {
    "dark": dict(
        win="#0d1117", bar="#161b22", border="#30363d", text="#e6edf3", dim="#8b949e",
        prompt="#3fb950", accent="#f0883e", contour="#2d4a3a", contour_hi="#3f6b52",
        grid="#21262d", ok="#3fb950", dots=("#ff5f57", "#febc2e", "#28c840"),
    ),
    "light": dict(
        win="#ffffff", bar="#f6f8fa", border="#d0d7de", text="#1f2328", dim="#656d76",
        prompt="#1a7f37", accent="#bc4c00", contour="#cfe0d4", contour_hi="#9fc2aa",
        grid="#eaeef2", ok="#1a7f37", dots=("#ff5f57", "#febc2e", "#28c840"),
    ),
}

# Terminal lines: (kind, text, start_time_s, duration_s)
LINES = [
    ("cmd", "whoami", 0.3, 0.5),
    ("name", "Valeriy Zaichikov", 1.0, 0.6),
    ("out", "robotics & AI student · NSU, 2023–2027", 1.6, 0.7),
    ("cmd", "cat focus.txt", 2.6, 0.6),
    ("out", "computer vision · CUDA · ROS2 · python backend", 3.3, 0.9),
    ("cmd", "./plan_route --terrain aerial --to internship", 4.5, 1.1),
    ("out", "analyzing terrain ............ done", 5.8, 0.8),
]
ROUTE_START, ROUTE_DUR = 6.7, 2.4
FOUND_T = ROUTE_START + ROUTE_DUR + 0.1

PEAKS = [  # (cx, cy, rx, ry, rings) in map-local coordinates
    (95, 70, 78, 52, 5),
    (250, 150, 70, 48, 5),
    (270, 40, 40, 26, 3),
]


def blob(cx, cy, rx, ry, seed, n=32):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 1 + 0.10 * math.sin(3 * a + seed) + 0.06 * math.sin(5 * a + 2 * seed) + 0.04 * math.cos(7 * a + seed)
        pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(n):  # Catmull-Rom -> cubic Bezier for a smooth closed curve
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.0f},{c1[1]:.0f} {c2[0]:.0f},{c2[1]:.0f} {p2[0]:.0f},{p2[1]:.0f}"
    return d + "Z"


def contours(t):
    out = []
    for k, (cx, cy, rx, ry, rings) in enumerate(PEAKS):
        for j in range(rings):
            s = 1 - j / rings
            col = t["contour_hi"] if j == rings - 1 else t["contour"]
            out.append(f'<path d="{blob(cx, cy, rx * s, ry * s, k * 1.7 + j * 0.6)}" fill="none" stroke="{col}" stroke-width="1.2"/>')
    return "\n".join(out)


# Route from bottom-left to top-right, threading the saddle between the peaks.
ROUTE = "M18,200 C60,196 120,150 160,118 S190,78 205,72 S240,92 285,96 S318,60 318,24"
START, END = (18, 200), (318, 24)


def build(theme_name, static=False):
    t = THEMES[theme_name]
    font = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
    css = f"""
    text{{font-family:{font};}}
    .t{{font-size:16.5px;fill:{t['text']};}}
    .d{{font-size:16.5px;fill:{t['dim']};}}
    .p{{font-size:16.5px;fill:{t['prompt']};font-weight:600;}}
    .n{{font-size:20px;fill:{t['text']};font-weight:700;}}
    .ttl{{font-size:13px;fill:{t['dim']};}}
    .lbl{{font-size:11px;fill:{t['dim']};stroke:{t['win']};stroke-width:4px;paint-order:stroke;stroke-linejoin:round;}}
    .ok{{font-size:16.5px;fill:{t['ok']};font-weight:600;}}
    """
    if not static:
        css += f"""
    .cover{{animation:wipe var(--dur) steps(var(--steps)) var(--t0) forwards;}}
    @keyframes wipe{{to{{transform:translateX(var(--w));}}}}
    .route{{stroke-dasharray:420;stroke-dashoffset:420;animation:draw {ROUTE_DUR}s ease-in-out {ROUTE_START}s forwards;}}
    @keyframes draw{{to{{stroke-dashoffset:0;}}}}
    .fade{{opacity:0;animation:fade .4s ease-out var(--t0) forwards;}}
    @keyframes fade{{to{{opacity:1;}}}}
    .cursor{{animation:blink 1s steps(1) infinite;}}
    @keyframes blink{{50%{{opacity:0;}}}}
    @media (prefers-reduced-motion:reduce){{
      .cover{{display:none;}} .route{{stroke-dashoffset:0;animation:none;}}
      .fade{{opacity:1;animation:none;}} .cursor{{animation:none;}} .drone{{display:none;}}
    }}
    """
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Valeriy Zaichikov — robotics and AI student at NSU: computer vision, CUDA, ROS2, Python backend">',
             f"<style>{css}</style>"]
    # window
    parts.append(f'<rect x="{WIN_X}" y="{WIN_Y}" width="{WIN_W}" height="{WIN_H}" rx="10" fill="{t["win"]}" stroke="{t["border"]}"/>')
    parts.append(f'<path d="M{WIN_X},{WIN_Y + BAR_H} V{WIN_Y + 10} a10,10 0 0 1 10,-10 H{WIN_X + WIN_W - 10} a10,10 0 0 1 10,10 V{WIN_Y + BAR_H} Z" fill="{t["bar"]}"/>')
    parts.append(f'<line x1="{WIN_X}" y1="{WIN_Y + BAR_H}" x2="{WIN_X + WIN_W}" y2="{WIN_Y + BAR_H}" stroke="{t["border"]}"/>')
    for i, c in enumerate(t["dots"]):
        parts.append(f'<circle cx="{WIN_X + 20 + i * 20}" cy="{WIN_Y + BAR_H / 2}" r="6" fill="{c}"/>')
    parts.append(f'<text x="{W / 2}" y="{WIN_Y + 22}" text-anchor="middle" class="ttl">buklinfur@nsu: ~</text>')

    # terminal text with typing wipes
    parts.append(f'<clipPath id="term"><rect x="{WIN_X}" y="{WIN_Y + BAR_H}" width="{MAP_X - 14 - WIN_X}" height="{WIN_H - BAR_H}"/></clipPath><g clip-path="url(#term)">')
    x0, y, lh = 30, 72, 26
    char_w = 10.3  # generous monospace advance at 16.5px (covers are clipped anyway)
    for kind, txt, t0, dur in LINES:
        if kind == "cmd":
            parts.append(f'<text x="{x0}" y="{y}" class="p">$</text>')
            tx, cls = x0 + 18, "t"
        else:
            tx, cls = x0, {"name": "n", "out": "d"}[kind]
        safe = txt.replace("&", "&amp;")
        parts.append(f'<text x="{tx}" y="{y}" class="{cls}" xml:space="preserve">{safe}</text>')
        if not static:
            w = len(txt) * (char_w * (20 / 16.5 if kind == "name" else 1)) + 12
            steps = max(len(txt), 1)
            parts.append(f'<rect class="cover" x="{tx - 2}" y="{y - 19}" width="{w:.0f}" height="26" fill="{t["win"]}" '
                         f'style="--t0:{t0}s;--dur:{dur}s;--steps:{steps};--w:{w + 4:.0f}px"/>')
        y += lh
    # final line: route found + cursor
    fade = "" if static else f' class="fade" style="--t0:{FOUND_T}s"'
    parts.append(f'<g{fade}><text x="{x0}" y="{y}" class="ok" xml:space="preserve">✓ route found <tspan class="d" font-weight="400">· open to internships</tspan></text></g>')
    cur = f'<rect class="cursor" x="{x0}" y="{y + 10}" width="9" height="17" fill="{t["text"]}"/>'
    parts.append(cur if static else f'<g class="fade" style="--t0:{FOUND_T + 0.3}s">{cur}</g>')
    parts.append("</g>")

    # map panel
    parts.append(f'<g transform="translate({MAP_X},{MAP_Y})">')
    parts.append(f'<rect x="0" y="0" width="{MAP_W}" height="{MAP_H}" rx="6" fill="none" stroke="{t["border"]}" stroke-dasharray="3 4"/>')
    for gx in range(40, MAP_W, 40):
        parts.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{MAP_H}" stroke="{t["grid"]}"/>')
    for gy in range(40, MAP_H, 40):
        parts.append(f'<line x1="0" y1="{gy}" x2="{MAP_W}" y2="{gy}" stroke="{t["grid"]}"/>')
    parts.append(f'<clipPath id="m"><rect x="0" y="0" width="{MAP_W}" height="{MAP_H}" rx="6"/></clipPath><g clip-path="url(#m)">')
    parts.append(contours(t))
    parts.append("</g>")
    route_cls = "" if static else ' class="route"'
    parts.append(f'<path id="r"{route_cls} d="{ROUTE}" fill="none" stroke="{t["accent"]}" stroke-width="2.4" stroke-linecap="round" {"" if static else " stroke-dasharray=\"420\""}/>')
    if static:
        pass
    # start marker
    parts.append(f'<circle cx="{START[0]}" cy="{START[1]}" r="5" fill="{t["accent"]}"/>')
    parts.append(f'<text x="{START[0] + 10}" y="{START[1] + 4}" class="lbl">NSU</text>')
    # target crosshair
    ex, ey = END
    parts.append(f'<g stroke="{t["accent"]}" stroke-width="1.6" fill="none"><circle cx="{ex}" cy="{ey}" r="7"/>'
                 f'<line x1="{ex - 11}" y1="{ey}" x2="{ex + 11}" y2="{ey}"/><line x1="{ex}" y1="{ey - 11}" x2="{ex}" y2="{ey + 11}"/></g>')
    parts.append(f'<text x="{ex - 12}" y="{ey + 4}" text-anchor="end" class="lbl">next role</text>')
    # drone marker follows the route while it is drawn, then stays at the target
    if not static:
        parts.append(f'<g class="drone"><circle r="4.5" fill="{t["text"]}" opacity="0">'
                     f'<set attributeName="opacity" to="1" begin="{ROUTE_START}s"/>'
                     f'<animateMotion dur="{ROUTE_DUR}s" begin="{ROUTE_START}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".42 0 .58 1">'
                     f'<mpath href="#r"/></animateMotion></circle></g>')
    parts.append(f'<text x="{MAP_W - 8}" y="{MAP_H - 8}" text-anchor="end" class="lbl">terrain map · lines = elevation</text>')
    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    for name in THEMES:
        with open(f"assets/banner-{name}.svg", "w", encoding="utf-8") as f:
            f.write(build(name))
        if "--static" in sys.argv:
            with open(f"assets/banner-{name}-static.svg", "w", encoding="utf-8") as f:
                f.write(build(name, static=True))
    print("ok")
