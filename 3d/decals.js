// Runtime decals for the flacon front print. The spec marks these as generated canvas
// textures (material 'print-green' -> runtimeDecal): the extracted photo crop bakes the
// studio lighting and the checker background, so the print is redrawn flat instead.
// Typography is an approximation of the reference, not the brand typeface.
import * as THREE from 'three';

const INK = '#0f8a5f';

function canvasTexture(w, h, draw) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const g = c.getContext('2d');
  draw(g, w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

// Interlocking double-G mark, measured on material-evidence/emblem-crop.png: each G has radius
// ~0.12u and sits 0.073u either side of centre; the openings face each other, with the G
// spurs meeting below the centre line. Black raised strokes ~0.04u wide with a lifted edge.
function drawGlyph(g, w, h) {
  const px = w / 0.46; // canvas px per body unit (decal plane is 0.46u wide)
  const cy = h / 2, R = 0.12 * px, off = 0.073 * px, sw = 0.04 * px;
  const G = (x0, flip) => {
    g.save();
    g.translate(x0, cy);
    if (flip) g.scale(-1, 1);
    const path = () => {
      g.beginPath();
      g.arc(0, 0, R, -Math.PI * 0.27, 0, true);
      g.moveTo(R, sw * 0.15);
      g.lineTo(R * 0.32, sw * 0.15);
    };
    g.lineJoin = 'miter'; g.lineCap = 'butt';
    g.strokeStyle = '#020202'; g.lineWidth = sw * 1.25; path(); g.stroke();
    g.strokeStyle = '#2b2b2b'; g.lineWidth = sw * 0.75; path(); g.stroke();
    g.strokeStyle = '#0a0a0a'; g.lineWidth = sw * 0.45; path(); g.stroke();
    g.restore();
  };
  G(w / 2 - off, false);
  G(w / 2 + off, true);
}

function drawText(g, w, h) {
  g.fillStyle = INK;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  // Plane spans y 0.1..0.7 of the body; wordmark at y 0.606, subline at y 0.187.
  const wordY = h * ((0.7 - 0.606) / 0.6);
  const subY = h * ((0.7 - 0.187) / 0.6);
  g.font = `400 ${Math.round(h * 0.075)}px "Times New Roman", Georgia, serif`;
  if ('letterSpacing' in g) g.letterSpacing = `${Math.round(w * 0.006)}px`;
  g.fillText('GUCCI GUILTY', w / 2, wordY);
  g.font = `600 ${Math.round(h * 0.04)}px Arial, Helvetica, sans-serif`;
  if ('letterSpacing' in g) g.letterSpacing = `${Math.round(w * 0.03)}px`;
  g.fillText('ESSENCE', w / 2 + w * 0.015, subY);
}

export function applyFrontDecals(model) {
  const glyphTex = canvasTexture(1024, 1024, drawGlyph);
  const textTex = canvasTexture(1024, 768, drawText);
  model.traverse((o) => {
    if (!o.isMesh) return;
    const decal = (map) => new THREE.MeshPhysicalMaterial({
      map, transparent: true, roughness: 0.35, clearcoat: 0.6, depthWrite: false,
      polygonOffset: true, polygonOffsetFactor: -2,
    });
    if (o.name === 'Double-G glyph print') o.material = decal(glyphTex);
    else if (o.name === 'Wordmark and subline print') o.material = decal(textTex);
    else if (o.name === 'Emblem green disc') {
      o.material = new THREE.MeshPhysicalMaterial({ color: 0x007255, roughness: 0.25, clearcoat: 1, clearcoatRoughness: 0.1 });
    }
  });
}
