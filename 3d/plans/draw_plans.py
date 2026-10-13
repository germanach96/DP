"""Orthographic plans of the proposed flacon shape (front, side, top, base) for user sign-off.

Shape model: every outline is built from superellipse halves joined to gently convex sides, so
there are no straight runs and no corners. Units are relative (body width = 1).
Run: python3 draw_plans.py  ->  planos-forma.svg
"""
import math
from pathlib import Path

S = 260                      # px per unit
H, D, N = 1.62, 0.40, 2.6    # body height, depth, plan superellipse exponent
SPLIT = 1.075                # green/black boundary height
GREEN, BLACK, INK, DIM = '#0c7a5a', '#1a1a1a', '#111', '#666'


def silhouette(hw0, top_b, top_n, bot_b, bot_n, bulge, cx, cy, k=120):
    """Closed outline: superellipse dome on top, superellipse floor, convex sides that blend to 0."""
    yc = H - top_b
    side_hw = lambda y: hw0 + bulge * math.sin(math.pi * (y - bot_b) / (yc - bot_b))
    pts = []
    for i in range(k + 1):                       # dome, right -> left
        t = i / k * math.pi
        c, s = math.cos(t), math.sin(t)
        pts.append((hw0 * math.copysign(abs(c) ** (2 / top_n), c), yc + top_b * abs(s) ** (2 / top_n)))
    for i in range(1, k):                        # left side, down
        y = yc - (yc - bot_b) * i / k
        pts.append((-side_hw(y), y))
    for i in range(k + 1):                       # floor, left -> right
        t = math.pi + i / k * math.pi
        c, s = math.cos(t), math.sin(t)
        pts.append((hw0 * math.copysign(abs(c) ** (2 / bot_n), c), bot_b - bot_b * abs(s) ** (2 / bot_n)))
    for i in range(1, k):                        # right side, up
        y = bot_b + (yc - bot_b) * i / k
        pts.append((side_hw(y), y))
    return 'M' + ' L'.join(f'{cx + x * S:.1f},{cy - y * S:.1f}' for x, y in pts) + ' Z'


def superellipse(a, b, n, cx, cy, k=200):
    pts = []
    for i in range(k):
        t = 2 * math.pi * i / k
        c, s = math.cos(t), math.sin(t)
        pts.append((cx + a * math.copysign(abs(c) ** (2 / n), c) * S, cy + b * math.copysign(abs(s) ** (2 / n), s) * S))
    return 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts) + ' Z'


def body(d, cx, cy, cid):
    return [f'<defs><clipPath id="{cid}"><path d="{d}"/></clipPath></defs>',
            f'<g clip-path="url(#{cid})"><rect x="{cx-400}" y="{cy-H*S-60}" width="800" height="{(H-SPLIT)*S+60}" fill="{GREEN}"/>',
            f'<rect x="{cx-400}" y="{cy-SPLIT*S}" width="800" height="{SPLIT*S+40}" fill="{BLACK}"/></g>',
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="2"/>']


def cap(cx, cy, w):
    top = cy - H * S
    return [f'<rect x="{cx-0.12*S:.1f}" y="{top-0.075*S:.1f}" width="{0.24*S:.1f}" height="{0.09*S:.1f}" rx="6" fill="#222" stroke="{INK}" stroke-width="1.5"/>',
            f'<rect x="{cx-w/2*S:.1f}" y="{top-0.34*S:.1f}" width="{w*S:.1f}" height="{0.27*S:.1f}" rx="{0.07*S:.1f}" fill="#111" stroke="{INK}" stroke-width="1.5"/>']


def dim_h(x1, x2, y, label):
    return [f'<path d="M{x1},{y}H{x2}M{x1},{y-6}v12M{x2},{y-6}v12" stroke="{DIM}" fill="none"/>',
            f'<text x="{(x1+x2)/2}" y="{y+20}" text-anchor="middle" font-size="15" fill="{DIM}">{label}</text>']


def dim_v(x, y1, y2, label):
    return [f'<path d="M{x},{y1}V{y2}M{x-6},{y1}h12M{x-6},{y2}h12" stroke="{DIM}" fill="none"/>',
            f'<text x="{x-10}" y="{(y1+y2)/2}" text-anchor="end" font-size="15" fill="{DIM}">{label}</text>']


def title(x, y, t, sub):
    return [f'<text x="{x}" y="{y}" text-anchor="middle" font-size="24" font-weight="600" fill="{INK}">{t}</text>',
            f'<text x="{x}" y="{y+24}" text-anchor="middle" font-size="15" fill="{DIM}">{sub}</text>']


W_PX, H_PX = 1700, 1080
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_PX}" height="{H_PX}" viewBox="0 0 {W_PX} {H_PX}" font-family="Inter, Arial, sans-serif">',
     f'<rect width="{W_PX}" height="{H_PX}" fill="#f4f4f2"/>']

fx, fy = 330, 900
pf = silhouette(0.5, 0.30, 2.8, 0.17, 3.2, 0.012, fx, fy)
o += body(pf, fx, fy, 'cf') + cap(fx, fy, 0.35)
o.append(f'<circle cx="{fx}" cy="{fy-0.864*S}" r="{0.23*S}" fill="none" stroke="#3a3a3a" stroke-width="5"/><circle cx="{fx}" cy="{fy-0.864*S}" r="{0.2*S}" fill="{GREEN}"/>')
o += dim_h(fx - 0.5 * S, fx + 0.5 * S, fy + 30, 'ancho 1,00') + dim_v(fx - 0.5 * S - 30, fy, fy - H * S, 'alto cuerpo 1,62')
o += title(fx, 60, 'Alzado (frente)', 'sin rectas: lados algo abombados, hombros en cúpula continua hasta el cuello')

sx, sy = 860, 900
ps = silhouette(D / 2, 0.20, 2.4, 0.13, 2.8, 0.008, sx, sy)
o += body(ps, sx, sy, 'cs') + cap(sx, sy, 0.30)
o += dim_h(sx - D / 2 * S, sx + D / 2 * S, sy + 30, 'fondo 0,40')
o += title(sx, 60, 'Perfil (lateral)', 'canto redondo arriba y abajo, sin aristas')

px, py = 1360, 330
o.append(f'<path d="{superellipse(0.5, D/2, N, px, py)}" fill="{BLACK}" stroke="{INK}" stroke-width="2"/>')
o.append(f'<path d="{superellipse(0.175, 0.15, 3.2, px, py)}" fill="#111" stroke="#888" stroke-width="1.5" stroke-dasharray="6 4"/>')
o.append(f'<text x="{px}" y="{py+5}" text-anchor="middle" font-size="13" fill="#bbb">tapón</text>')
o += dim_h(px - 0.5 * S, px + 0.5 * S, py + D / 2 * S + 30, 'ancho 1,00')
o += title(px, 60, 'Planta (desde arriba)', 'sección tipo «píldora» (superelipse n≈2,6), extremos redondos')

bx, by = 1360, 790
o.append(f'<path d="{superellipse(0.5, D/2, N, bx, by)}" fill="#1c1c1c" stroke="{INK}" stroke-width="2"/>')
o.append(f'<path d="{superellipse(0.42, D/2-0.07, 2.4, bx, by)}" fill="#2b2b2b" stroke="#8a8a8a" stroke-width="2"/>')
o += title(bx, 600, 'Base (desde abajo)', 'panel ovalado hundido a ~0,07 del borde, canto de cristal grueso')
o.append(f'<text x="{W_PX/2}" y="{H_PX-20}" text-anchor="middle" font-size="14" fill="{DIM}">Unidades relativas (ancho = 1). Alto y emblema se mantienen; el fondo 0,40 es estimado porque la foto está en perspectiva desde abajo.</text>')
o.append('</svg>')
Path(__file__).with_name('planos-forma.svg').write_text('\n'.join(o))
