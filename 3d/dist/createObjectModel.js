import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { BokehPass } from 'three/examples/jsm/postprocessing/BokehPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
// bevelEnabled defaults to true on THREE.ExtrudeGeometry and rounds every
// corner — sharp/pointed profiles (blades, fork tines, spikes) need
// bevelEnabled: false plus lineTo()-only path segments near the tip, since a
// curve command cannot produce a true converging point.
function buildExtrudeShape(points, holes) {
    const shape = new THREE.Shape();
    if (points.length > 0) {
        shape.moveTo(points[0][0], points[0][1]);
        for (let i = 1; i < points.length; i += 1) {
            shape.lineTo(points[i][0], points[i][1]);
        }
    }
    // Cutouts (e.g. an oval wire-cutter hole) as THREE.Path added to shape.holes —
    // dep-free boolean subtraction via the tessellator, no CSG library needed.
    for (const loop of holes ?? []) {
        if (loop.length < 3)
            continue;
        const path = new THREE.Path();
        path.moveTo(loop[0][0], loop[0][1]);
        for (let i = 1; i < loop.length; i += 1)
            path.lineTo(loop[i][0], loop[i][1]);
        path.closePath();
        shape.holes.push(path);
    }
    return shape;
}
// Build an N-gon oval loop (for hole authoring from a compact {cx,cy,rx,ry} descriptor).
function ovalLoop(cx, cy, rx, ry, seg = 24) {
    const loop = [];
    for (let i = 0; i < seg; i += 1) {
        const a = (i / seg) * Math.PI * 2;
        loop.push([cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]);
    }
    return loop;
}
function buildExtrudeGeometry(profile) {
    const holes = [...(profile.holes ?? []), ...((profile.ovalHoles ?? []).map((o) => ovalLoop(o.cx, o.cy, o.rx, o.ry)))];
    const shape = buildExtrudeShape(profile.points, holes);
    return new THREE.ExtrudeGeometry(shape, {
        depth: profile.depth,
        bevelEnabled: false,
        steps: 1,
    });
}
function hashString(value) {
    let hash = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
        hash ^= value.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
}
function readLayerNumber(value, keys, fallback) {
    if (typeof value === 'number')
        return value;
    if (value && typeof value === 'object') {
        const record = value;
        for (const key of keys) {
            if (typeof record[key] === 'number')
                return record[key];
        }
    }
    return fallback;
}
function hexToRgb(hex) {
    const normalized = /^#[0-9a-f]{3}$/i.test(hex)
        ? '#' + hex.slice(1).split('').map((part) => part + part).join('')
        : hex;
    const value = /^#[0-9a-f]{6}$/i.test(normalized) ? Number.parseInt(normalized.slice(1), 16) : 0x8a7a5f;
    return [clampAlbedoChannel((value >> 16) & 255), clampAlbedoChannel((value >> 8) & 255), clampAlbedoChannel(value & 255)];
}
function materialPalette(spec) {
    const palette = spec.colorVariation?.palette;
    if (Array.isArray(palette) && palette.length > 0)
        return palette.filter((value) => typeof value === 'string');
    const secondary = spec.albedo?.secondary;
    const colors = [spec.baseColor ?? spec.color ?? spec.albedo?.dominant, ...(Array.isArray(secondary) ? secondary : [])];
    return colors.filter((value) => typeof value === 'string' && value.startsWith('#'));
}
function clamp01(value) {
    return Math.max(0, Math.min(1, value));
}
function clampAlbedoChannel(value) {
    return Math.max(30, Math.min(240, Math.round(value)));
}
function clampPbrF0(value) {
    return Math.max(0.02, Math.min(1, value));
}
function clampPbrIor(value) {
    return Math.max(1, Math.min(2.5, value));
}
function clampPbrMetalness(value) {
    return value >= 0.5 ? 1 : 0;
}
function clampedAlbedoColor(spec) {
    const source = typeof spec.baseColor === 'string' ? spec.baseColor : '#8A7A5F';
    // setStyle with an explicit SRGBColorSpace, NOT the numeric constructor.
    //
    // `new THREE.Color(r, g, b)` treats its arguments as LINEAR working-space components,
    // while an authored `baseColor` hex is sRGB. Feeding one to the other skipped the
    // transfer function and lifted every dark albedo: #2e2a28, authored as a near-black
    // vinyl, rendered at roughly sRGB 0.46 — a mid grey. The error is largest exactly where
    // it matters most, because the transfer curve is steepest near black.
    return new THREE.Color().setStyle(source, THREE.SRGBColorSpace);
}
function smoothCurve(value) {
    return value * value * (3 - 2 * value);
}
function periodicHash(x, y, seed, periodX, periodY) {
    const wrappedX = ((x % periodX) + periodX) % periodX;
    const wrappedY = ((y % periodY) + periodY) % periodY;
    let value = Math.imul(wrappedX + seed * 17, 374761393) ^ Math.imul(wrappedY + seed * 31, 668265263);
    value = Math.imul(value ^ (value >>> 13), 1274126177);
    return ((value ^ (value >>> 16)) >>> 0) / 4294967295;
}
function periodicValueNoise(u, v, seed, periodX, periodY) {
    const x = u * periodX;
    const y = v * periodY;
    const x0 = Math.floor(x);
    const y0 = Math.floor(y);
    const tx = smoothCurve(x - x0);
    const ty = smoothCurve(y - y0);
    const a = periodicHash(x0, y0, seed, periodX, periodY);
    const b = periodicHash(x0 + 1, y0, seed, periodX, periodY);
    const c = periodicHash(x0, y0 + 1, seed, periodX, periodY);
    const d = periodicHash(x0 + 1, y0 + 1, seed, periodX, periodY);
    return THREE.MathUtils.lerp(THREE.MathUtils.lerp(a, b, tx), THREE.MathUtils.lerp(c, d, tx), ty);
}
function surfaceBands(spec) {
    const source = Array.isArray(spec.surfaceFrequencyBands) ? spec.surfaceFrequencyBands : [];
    const parsed = source.flatMap((item) => {
        if (!item || typeof item !== 'object')
            return [];
        const band = item;
        const frequency = typeof band.frequency === 'number' ? band.frequency : 0;
        const amplitude = typeof band.amplitude === 'number' ? band.amplitude : 0;
        if (frequency <= 0 || amplitude <= 0)
            return [];
        const stretch = Array.isArray(band.stretch) ? band.stretch : [1, 1];
        const description = `${String(band.pattern ?? '')} ${String(band.role ?? '')}`.toLowerCase();
        return [{
                frequency,
                amplitude,
                stretchX: typeof stretch[0] === 'number' ? Math.max(0.1, stretch[0]) : 1,
                stretchY: typeof stretch[1] === 'number' ? Math.max(0.1, stretch[1]) : 1,
                ridge: /(ridge|groove|grain|fiber|striated|crack)/.test(description),
            }];
    });
    return parsed.length > 0 ? parsed : [
        { frequency: 2, amplitude: 0.42, stretchX: 1, stretchY: 1, ridge: false },
        { frequency: 12, amplitude: 0.22, stretchX: 1, stretchY: 1, ridge: false },
        { frequency: 56, amplitude: 0.08, stretchX: 1, stretchY: 1, ridge: false },
    ];
}
function sampleSurface(u, v, bands, seed) {
    let value = 0;
    let weight = 0;
    for (let index = 0; index < bands.length; index += 1) {
        const band = bands[index];
        const periodX = Math.max(1, Math.round(band.frequency * band.stretchX));
        const periodY = Math.max(1, Math.round(band.frequency * band.stretchY));
        let sample = periodicValueNoise(u, v, seed + index * 1013, periodX, periodY);
        if (band.ridge)
            sample = 1 - Math.abs(sample * 2 - 1);
        value += sample * band.amplitude;
        weight += band.amplitude;
    }
    return weight > 0 ? clamp01(value / weight) : 0.5;
}
function mixPalette(colors, value) {
    if (colors.length === 1)
        return colors[0];
    const scaled = clamp01(value) * (colors.length - 1);
    const index = Math.min(colors.length - 2, Math.floor(scaled));
    const mix = scaled - index;
    const a = colors[index];
    const b = colors[index + 1];
    return [
        Math.round(THREE.MathUtils.lerp(a[0], b[0], mix)),
        Math.round(THREE.MathUtils.lerp(a[1], b[1], mix)),
        Math.round(THREE.MathUtils.lerp(a[2], b[2], mix)),
    ];
}
function parseRgba(value) {
    const match = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/.exec(value);
    if (!match)
        return [138, 122, 95];
    return [clampAlbedoChannel(Number(match[1])), clampAlbedoChannel(Number(match[2])), clampAlbedoChannel(Number(match[3]))];
}
// Analytical per-pixel gradient sample. The extraction schema's colorGradient carries
// exact rgba(...) stop colors (see extract_part_color_recipe.py), so this samples the
// same trend directly in JS math rather than round-tripping through a Canvas 2D
// createLinearGradient/createRadialGradient object — same visual result, and it composes
// directly with the existing noise/height-correlated colorVariation blend below.
function sampleColorGradient(gradient, u, v) {
    const stops = gradient.stops.length >= 2 ? gradient.stops : [{ offset: 0, color: 'rgba(138,122,95,1)' }, { offset: 1, color: 'rgba(138,122,95,1)' }];
    let t;
    if (gradient.type === 'radial') {
        const [cx, cy] = gradient.axis;
        const dx = u - cx;
        const dy = v - cy;
        const maxRadius = Math.max(0.001, Math.hypot(Math.max(cx, 1 - cx), Math.max(cy, 1 - cy)));
        t = clamp01(Math.hypot(dx, dy) / maxRadius);
    }
    else {
        const [ax, ay] = gradient.axis;
        const projection = (u - 0.5) * ax + (v - 0.5) * ay;
        const maxProjection = 0.5 * (Math.abs(ax) + Math.abs(ay)) || 0.5;
        t = clamp01(projection / maxProjection + 0.5);
    }
    const scaled = t * (stops.length - 1);
    const index = Math.min(stops.length - 2, Math.max(0, Math.floor(scaled)));
    const mix = scaled - index;
    const a = parseRgba(stops[index].color);
    const b = parseRgba(stops[index + 1].color);
    return [
        THREE.MathUtils.lerp(a[0], b[0], mix),
        THREE.MathUtils.lerp(a[1], b[1], mix),
        THREE.MathUtils.lerp(a[2], b[2], mix),
    ];
}
function writePixel(data, offset, red, green, blue) {
    data[offset] = Math.max(0, Math.min(255, Math.round(red)));
    data[offset + 1] = Math.max(0, Math.min(255, Math.round(green)));
    data[offset + 2] = Math.max(0, Math.min(255, Math.round(blue)));
    data[offset + 3] = 255;
}
function makeCanvas(size) {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    return canvas;
}
function createMapTexture(canvas, colorSpace, spec, options) {
    const texture = new THREE.CanvasTexture(canvas);
    const projection = spec.textureProjection && typeof spec.textureProjection === 'object' ? spec.textureProjection : {};
    const repeat = Array.isArray(projection.repeat) ? projection.repeat : [2, 2];
    texture.colorSpace = colorSpace;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(typeof repeat[0] === 'number' ? repeat[0] : 2, typeof repeat[1] === 'number' ? repeat[1] : 2);
    texture.anisotropy = Math.max(1, Math.round(options.textureAnisotropy ?? projection.anisotropy ?? 8));
    texture.needsUpdate = true;
    return texture;
}
function referenceMapUrl(spec, channel) {
    const reference = spec.referencePbr;
    if (!reference || typeof reference !== 'object')
        return null;
    if (reference.usable === false)
        return null;
    const confidence = typeof reference.confidence === 'number'
        ? reference.confidence
        : (typeof reference.estimatedFidelity === 'number' ? reference.estimatedFidelity : 0);
    const threshold = typeof reference.targetThreshold === 'number' ? reference.targetThreshold : 0.7;
    if (confidence < threshold)
        return null;
    const maps = reference.maps;
    if (!maps || typeof maps !== 'object')
        return null;
    const map = maps[channel];
    if (!map || typeof map !== 'object')
        return null;
    const record = map;
    const url = typeof record.url === 'string' && record.url.trim() ? record.url : record.path;
    return typeof url === 'string' && url.trim() ? url : null;
}
function createLoadedMapTexture(url, colorSpace, spec, options) {
    const texture = new THREE.TextureLoader().load(url);
    const projection = spec.textureProjection && typeof spec.textureProjection === 'object' ? spec.textureProjection : {};
    const repeat = Array.isArray(projection.repeat) ? projection.repeat : [1, 1];
    texture.colorSpace = colorSpace;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(typeof repeat[0] === 'number' ? repeat[0] : 1, typeof repeat[1] === 'number' ? repeat[1] : 1);
    texture.anisotropy = Math.max(1, Math.round(options.textureAnisotropy ?? projection.anisotropy ?? 8));
    texture.needsUpdate = true;
    return texture;
}
function makeReferenceTextureSet(spec, options) {
    const albedo = referenceMapUrl(spec, 'albedo');
    const roughness = referenceMapUrl(spec, 'roughness');
    const height = referenceMapUrl(spec, 'height');
    const normal = referenceMapUrl(spec, 'normal');
    const ao = referenceMapUrl(spec, 'ao');
    if (!albedo || !roughness || !height || !normal || !ao)
        return null;
    return {
        albedo: createLoadedMapTexture(albedo, THREE.SRGBColorSpace, spec, options),
        roughness: createLoadedMapTexture(roughness, THREE.NoColorSpace, spec, options),
        height: createLoadedMapTexture(height, THREE.NoColorSpace, spec, options),
        normal: createLoadedMapTexture(normal, THREE.NoColorSpace, spec, options),
        ao: createLoadedMapTexture(ao, THREE.NoColorSpace, spec, options),
        source: 'reference-pixel-extraction',
    };
}
function makeProceduralTextureSet(id, spec, options) {
    if (typeof document === 'undefined')
        return null;
    const qualityFirst = (options.qualityPriority ?? 'reference-fidelity') === 'reference-fidelity';
    const requested = options.textureSize ?? spec.textureResolution;
    const requestedSize = typeof requested === 'number' && Number.isFinite(requested)
        ? requested
        : (qualityFirst ? 1024 : 512);
    const size = Math.max(256, Math.min(2048, 2 ** Math.round(Math.log2(requestedSize))));
    const canvases = {
        albedo: makeCanvas(size),
        roughness: makeCanvas(size),
        height: makeCanvas(size),
        normal: makeCanvas(size),
        ao: makeCanvas(size),
    };
    const contexts = {
        albedo: canvases.albedo.getContext('2d'),
        roughness: canvases.roughness.getContext('2d'),
        height: canvases.height.getContext('2d'),
        normal: canvases.normal.getContext('2d'),
        ao: canvases.ao.getContext('2d'),
    };
    if (!contexts.albedo || !contexts.roughness || !contexts.height || !contexts.normal || !contexts.ao)
        return null;
    const images = {
        albedo: contexts.albedo.createImageData(size, size),
        roughness: contexts.roughness.createImageData(size, size),
        height: contexts.height.createImageData(size, size),
        normal: contexts.normal.createImageData(size, size),
        ao: contexts.ao.createImageData(size, size),
    };
    const seed = hashString(id);
    const bands = surfaceBands(spec);
    const heightField = new Float32Array(size * size);
    const roughnessField = new Float32Array(size * size);
    const palette = materialPalette(spec);
    const fallback = typeof spec.baseColor === 'string' ? spec.baseColor : '#8A7A5F';
    const colors = (palette.length >= 2 ? palette : [fallback, '#6E614B', '#A08F70']).map(hexToRgb);
    const baseRoughness = clamp01(readLayerNumber(spec.roughness, ['base'], 0.76));
    const roughnessVariation = clamp01(readLayerNumber(spec.roughness, ['variation'], 0.18));
    const colorAmplitude = clamp01(readLayerNumber(spec.colorVariation, ['amplitude', 'variation'], 0.18));
    const heightCorrelation = clamp01(readLayerNumber(spec.colorVariation, ['heightCorrelation'], 0.3));
    const colorGradient = spec.colorGradient;
    for (let y = 0; y < size; y += 1) {
        const v = y / size;
        for (let x = 0; x < size; x += 1) {
            const u = x / size;
            const index = y * size + x;
            const height = sampleSurface(u, v, bands, seed + 101);
            const roughNoise = sampleSurface(u, v, bands, seed + 7001);
            const colorNoise = sampleSurface(u, v, bands, seed + 15013);
            heightField[index] = height;
            roughnessField[index] = clamp01(baseRoughness + (roughNoise - 0.5) * roughnessVariation * 2);
            let color;
            if (colorGradient) {
                // Evidence-derived spatial gradient (Plan 1.3 Workstream C) takes priority
                // over the noise-based palette blend below — it is a measured trend, not a guess.
                color = sampleColorGradient(colorGradient, u, v);
            }
            else {
                const paletteValue = clamp01(0.5 + (colorNoise - 0.5) * colorAmplitude * 2 + (height - 0.5) * heightCorrelation);
                color = mixPalette(colors, paletteValue);
            }
            writePixel(images.albedo.data, index * 4, color[0], color[1], color[2]);
        }
    }
    const normalStrength = Math.max(0.05, readLayerNumber(spec.normal, ['strength', 'amplitude'], 0.35));
    const aoStrength = clamp01(readLayerNumber(spec.ambientOcclusion, ['cavityStrength', 'strength'], 0.35));
    for (let y = 0; y < size; y += 1) {
        const up = ((y - 1 + size) % size) * size;
        const down = ((y + 1) % size) * size;
        for (let x = 0; x < size; x += 1) {
            const left = (x - 1 + size) % size;
            const right = (x + 1) % size;
            const index = y * size + x;
            const center = heightField[index];
            const dx = (heightField[y * size + right] - heightField[y * size + left]) * normalStrength * 6;
            const dy = (heightField[down + x] - heightField[up + x]) * normalStrength * 6;
            const inverseLength = 1 / Math.sqrt(dx * dx + dy * dy + 1);
            const normalX = -dx * inverseLength;
            const normalY = -dy * inverseLength;
            const normalZ = inverseLength;
            const neighborAverage = (heightField[y * size + left] + heightField[y * size + right]
                + heightField[up + x] + heightField[down + x]) * 0.25;
            const cavity = Math.max(0, neighborAverage - center);
            const ao = clamp01(1 - aoStrength * (cavity * 12 + (1 - center) * 0.16));
            const offset = index * 4;
            const heightByte = center * 255;
            const roughnessByte = roughnessField[index] * 255;
            writePixel(images.height.data, offset, heightByte, heightByte, heightByte);
            writePixel(images.roughness.data, offset, roughnessByte, roughnessByte, roughnessByte);
            writePixel(images.normal.data, offset, (normalX * 0.5 + 0.5) * 255, (normalY * 0.5 + 0.5) * 255, (normalZ * 0.5 + 0.5) * 255);
            writePixel(images.ao.data, offset, ao * 255, ao * 255, ao * 255);
        }
    }
    contexts.albedo.putImageData(images.albedo, 0, 0);
    contexts.roughness.putImageData(images.roughness, 0, 0);
    contexts.height.putImageData(images.height, 0, 0);
    contexts.normal.putImageData(images.normal, 0, 0);
    contexts.ao.putImageData(images.ao, 0, 0);
    return {
        albedo: createMapTexture(canvases.albedo, THREE.SRGBColorSpace, spec, options),
        roughness: createMapTexture(canvases.roughness, THREE.NoColorSpace, spec, options),
        height: createMapTexture(canvases.height, THREE.NoColorSpace, spec, options),
        normal: createMapTexture(canvases.normal, THREE.NoColorSpace, spec, options),
        ao: createMapTexture(canvases.ao, THREE.NoColorSpace, spec, options),
        source: 'procedural',
    };
}
function createSculptMaterial(id, spec, options, denseComponent = false) {
    // A material that declares -- with evidence -- that its subject carries no texture
    // detail gets NO texture set. Synthesising one anyway is not a harmless default: the
    // branch below then forces color to white and roughness to 1 and reads both from the
    // generated maps, so the authored albedo and the reference-derived roughness are both
    // discarded, and the model gains mottling the reference does not have. Measured on the
    // tuxedo cat, whose black fur rendered as speckled grey-and-white from a palette that
    // only ever described two flat regions.
    const textureless = spec.textureless?.declared === true;
    const textures = textureless
        ? null
        : makeReferenceTextureSet(spec, options) ?? makeProceduralTextureSet(id, spec, options);
    const material = new THREE.MeshPhysicalMaterial({
        color: textures ? 0xffffff : clampedAlbedoColor(spec),
        roughness: textures ? 1 : clamp01(readLayerNumber(spec.roughness, ['base'], 0.76)),
        metalness: clampPbrMetalness(readLayerNumber(spec.metalness, ['base'], 0.0)),
        clearcoat: clamp01(readLayerNumber(spec.clearcoat, ['base', 'amount'], 0)),
        clearcoatRoughness: clamp01(readLayerNumber(spec.clearcoatRoughness, ['base'], 0.25)),
        transmission: clamp01(readLayerNumber(spec.transmission, ['base', 'amount'], 0)),
        ior: clampPbrIor(readLayerNumber(spec.ior, ['base', 'value'], 1.5)),
        thickness: Math.max(0, readLayerNumber(spec.thickness, ['base', 'amount'], 0)),
        attenuationDistance: Math.max(0.001, readLayerNumber(spec.attenuationDistance, ['base', 'value'], Infinity)),
        attenuationColor: new THREE.Color(typeof spec.attenuationColor === 'string' ? spec.attenuationColor : '#ffffff'),
        sheen: clamp01(readLayerNumber(spec.sheen, ['base', 'amount'], 0)),
        sheenColor: new THREE.Color(typeof spec.sheenColor === 'string' ? spec.sheenColor : '#ffffff'),
        sheenRoughness: clamp01(readLayerNumber(spec.sheenRoughness, ['base'], 1.0)),
        iridescence: clamp01(readLayerNumber(spec.iridescence, ['base', 'amount'], 0)),
        iridescenceIOR: clampPbrIor(readLayerNumber(spec.iridescenceIOR, ['base', 'value'], 1.3)),
        anisotropy: clamp01(readLayerNumber(spec.anisotropy, ['base', 'amount'], 0)),
        anisotropyRotation: readLayerNumber(spec.anisotropy, ['rotation'], 0),
        specularIntensity: clampPbrF0(readLayerNumber(spec.specularF0 ?? spec.f0 ?? spec.specularIntensity, ['base', 'value'], 1.0)),
        specularColor: new THREE.Color(typeof spec.specularColor === 'string' ? spec.specularColor : '#ffffff'),
        emissive: new THREE.Color(typeof spec.emissive === 'string' ? spec.emissive : '#000000'),
        emissiveIntensity: Math.max(0, readLayerNumber(spec.emissiveIntensity, ['base'], 1.0)),
        opacity: clamp01(readLayerNumber(spec.opacity, ['base'], 1)),
        transparent: readLayerNumber(spec.transmission, ['base', 'amount'], 0) > 0 || readLayerNumber(spec.opacity, ['base'], 1) < 1,
        alphaTest: Math.max(0, readLayerNumber(spec.alpha, ['cutoff', 'alphaTest'], 0)),
        wireframe: options.wireframe ?? false,
        side: spec.doubleSided === true ? THREE.DoubleSide : THREE.FrontSide,
        flatShading: spec.flatShading === true,
    });
    if (textures) {
        material.map = textures.albedo;
        material.roughnessMap = textures.roughness;
        material.normalMap = textures.normal;
        material.normalScale.setScalar(Math.max(0.05, readLayerNumber(spec.normal, ['strength', 'amplitude'], 0.35)));
        material.aoMap = textures.ao;
        material.aoMap.channel = 0;
        material.aoMapIntensity = readLayerNumber(spec.ambientOcclusion, ['cavityStrength', 'strength'], 0.35);
        const denseMesh = denseComponent || spec.denseMesh === true || spec.geometryDensity === 'dense' || spec.topologyClass === 'dense';
        const bumpScale = Math.max(0, readLayerNumber(spec.bump, ['amplitude', 'strength'], 0));
        const effectiveBumpScale = denseMesh ? Math.max(0.05, bumpScale) : bumpScale;
        if (effectiveBumpScale > 0) {
            material.bumpMap = textures.height;
            material.bumpScale = effectiveBumpScale;
        }
        const displacementScale = Math.max(0, readLayerNumber(spec.displacement, ['amplitude', 'strength'], 0));
        const effectiveDisplacementScale = denseMesh ? Math.max(0.005, displacementScale) : displacementScale;
        if (effectiveDisplacementScale > 0) {
            material.displacementMap = textures.height;
            material.displacementScale = effectiveDisplacementScale;
            material.displacementBias = -effectiveDisplacementScale * 0.5;
        }
    }
    material.envMapIntensity = readLayerNumber(spec, ['envMapIntensity'], 0.8);
    material.userData.sculptMaterial = spec;
    material.userData.proceduralMapsIndependent = true;
    material.userData.pbrConstraints = { albedoRange: [30, 240], binaryMetalness: true, f0Range: [0.02, 1], iorRange: [1, 2.5] };
    material.userData.pbrTextureSource = textures?.source ?? 'flat-fallback';
    material.userData.referencePbr = spec.referencePbr ?? null;
    material.userData.referenceMaterialId = spec.referenceMaterialId ?? spec.materialReference?.profileId ?? null;
    material.userData.materialEvidence = spec.materialEvidence ?? null;
    material.userData.validationViews = spec.materialReference?.validationViews ?? [];
    material.needsUpdate = true;
    return material;
}
function readVector3(value, fallback) {
    if (Array.isArray(value) && value.length === 3 && value.every((item) => typeof item === 'number')) {
        return new THREE.Vector3(value[0], value[1], value[2]);
    }
    return new THREE.Vector3(fallback[0], fallback[1], fallback[2]);
}
function readNumber(value, fallback) {
    return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}
function makeAttachmentEndpoint(attachment) {
    if (!attachment || typeof attachment !== 'object')
        return null;
    const record = attachment;
    const start = readVector3(record.localStart, [0, 0, 0]);
    const end = readVector3(record.localEnd, [0, 1, 0]);
    const delta = end.clone().sub(start);
    const length = delta.length();
    if (length <= 0.0001)
        return null;
    const direction = delta.clone().normalize();
    const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
    const baseRadius = Math.max(0.005, readNumber(record.baseRadius, 0.06));
    const endRadius = Math.max(0.003, readNumber(record.endRadius, baseRadius * 0.55));
    return {
        start,
        midpoint: delta.multiplyScalar(0.5),
        quaternion,
        length,
        baseRadius,
        endRadius,
    };
}
// Generated from ObjectSculptSpec target: Fragrance Flacon Two-Zone
// Sculpt build pass: form-refinement
// This factory is intentionally pass-gated. Finish browser screenshot review before unlocking deeper passes.
export function createFragranceFlaconTwoZoneModel(options = {}) {
    const root = new THREE.Group();
    root.name = "Fragrance Flacon Two-Zone";
    root.userData.reconstructionEvidence = { "itemFamily": null, "subtype": null, "componentAdapter": null, "route": null, "exactnessTier": null, "referenceCamera": { "solved": false, "fovDegrees": 40.0, "aspect": 1.0, "orientation": { "yaw": 0.0, "pitch": 0.0, "roll": 0.0 }, "positionHint": [0.0, 0.0, 3.0], "note": "For likeness work, solve the reference camera (forge/stage1_intake/solve_camera_pose.py) so the review render aligns with the photo and the reference can be projected. Confirm by overlay review." }, "approximationNotes": [] };
    root.userData.materialPipeline = {};
    root.userData.materialReferenceRegistry = null;
    const materialMap = {};
    materialMap["glass-green"] = createSculptMaterial("glass-green", { "id": "glass-green", "name": "Green tinted glass", "type": "MeshPhysicalMaterial", "baseColor": "#01604a", "metalness": 0, "roughness": { "base": 0.08 }, "transmission": 0.85, "ior": 1.5, "thickness": 0.4, "opacity": 1, "layers": ["albedo", "transmission"], "localOverrides": [{ "id": "split-line", "region": "y>=1.075", "note": "hard boundary to lacquer" }], "evidence": "image-analysis.md L5/L6", "textureless": { "declared": true, "evidence": ["zone:upper-third lum std 3.81: uniform tint, no grain or print"] }, "ambientOcclusion": { "mode": "contact", "note": "screen-space contact darkening at joins; no baked map" }, "rejectedReferencePbr": "material-evidence/glass-report.json (extracted, rejected after material-pass render: bakes highlights into albedo)" }, options);
    materialMap["lacquer-black"] = createSculptMaterial("lacquer-black", { "id": "lacquer-black", "name": "Black gloss lacquer", "type": "MeshPhysicalMaterial", "baseColor": "#020202", "metalness": 0, "roughness": { "base": 0.22 }, "clearcoat": 1, "clearcoatRoughness": 0.08, "layers": ["albedo", "clearcoat"], "localOverrides": [{ "id": "emblem-ring-highlight", "note": "grey edge highlights from studio light, not albedo" }], "evidence": "image-analysis.md L5", "textureless": { "declared": true, "evidence": ["zone:lower-two-thirds lum std 9.7: flat black, variance is specular only"] }, "ambientOcclusion": { "mode": "contact", "note": "screen-space contact darkening at joins; no baked map" }, "rejectedReferencePbr": "material-evidence/lacquer-report.json (extracted, rejected after material-pass render: bakes highlights into albedo)" }, options);
    materialMap["glass-base"] = createSculptMaterial("glass-base", { "id": "glass-base", "name": "Glass under lacquer", "type": "MeshPhysicalMaterial", "baseColor": "#0a0a0a", "metalness": 0, "roughness": { "base": 0.1 }, "layers": ["albedo"], "evidence": "inferred", "textureless": { "declared": true, "evidence": ["hidden under opaque lacquer; never visible"] }, "ambientOcclusion": { "mode": "contact", "note": "screen-space contact darkening at joins; no baked map" } }, options);
    materialMap["cap-black"] = createSculptMaterial("cap-black", { "id": "cap-black", "name": "Black gloss plastic", "type": "MeshPhysicalMaterial", "baseColor": "#020202", "metalness": 0, "roughness": { "base": 0.3 }, "clearcoat": 0.6, "layers": ["albedo", "clearcoat"], "localOverrides": [{ "id": "cap-edge-highlights", "note": "vertical highlight bands from environment reflection" }], "evidence": "image-analysis.md L5", "textureless": { "declared": true, "evidence": ["zone:cap lum std 16.46 from vertical gloss bands only, no grain"] }, "ambientOcclusion": { "mode": "contact", "note": "screen-space contact darkening at joins; no baked map" }, "rejectedReferencePbr": "material-evidence/cap-report.json (extracted, rejected after material-pass render: bakes highlights into albedo)" }, options);
    materialMap["emblem-green"] = createSculptMaterial("emblem-green", { "id": "emblem-green", "name": "Emblem green inlay", "type": "MeshPhysicalMaterial", "baseColor": "#007255", "metalness": 0, "roughness": { "base": 0.3 }, "layers": ["albedo"], "evidence": "sample (0,114,85)", "textureless": { "declared": true, "evidence": ["zone:emblem disc is flat inlay colour; glyph lines belong to label-decal"] }, "ambientOcclusion": { "mode": "contact", "note": "screen-space contact darkening at joins; no baked map" }, "rejectedReferencePbr": "material-evidence/disc-report.json (extracted, rejected after material-pass render: bakes highlights into albedo)" }, options);
    materialMap["print-green"] = createSculptMaterial("print-green", { "id": "print-green", "name": "Green print ink", "type": "MeshStandardMaterial", "baseColor": "#0f8a5f", "metalness": { "base": 0.0, "variation": 0.0 }, "roughness": { "base": 0.68, "variation": 0.05, "map": { "path": "/home/user/DP/3d/material-evidence/print/print-green_roughness.png", "url": "material-evidence/print/print-green_roughness.png", "channel": "roughness", "source": "reference-pixel-extraction" }, "localResponse": "reference-derived roughness estimate; cavities and textured zones trend rougher, bright highlights trend smoother" }, "transparent": true, "layers": ["albedo", "alpha"], "localOverrides": [{ "id": "wordmark" }, { "id": "subline" }, { "id": "double-g-glyph" }, { "id": "reference-pbr-pixel-evidence", "type": "material-map-evidence", "evidenceRefs": ["full-object"], "channels": ["albedo", "roughness", "height", "normal", "ambient-occlusion"], "notes": "Use generated maps as material evidence, then refine after browser screenshot comparison." }], "evidence": "sample wordmark y752", "ambientOcclusion": { "cavityStrength": 0.38, "contactShadowBias": 0.35, "map": { "path": "/home/user/DP/3d/material-evidence/print/print-green_ao.png", "url": "material-evidence/print/print-green_ao.png", "channel": "ao", "source": "reference-pixel-extraction" }, "notes": "Reference-derived cavity estimate from local height minima; verify against grazing-light screenshot." }, "finishClass": "worn-composite", "texturePalette": ["#000000", "#000000", "#000000", "#000000", "#010000"], "proceduralTexture": "mottle", "clearcoat": { "base": 0.0, "variation": 0.0 }, "clearcoatRoughness": { "base": 0.0, "variation": 0.0 }, "transmission": { "base": 0.0, "variation": 0.0 }, "ior": { "base": 1.5, "value": 1.5 }, "envMapIntensity": 0.5, "referencePbr": { "version": "1.0", "sourceImage": "/home/user/DP/3d/material-evidence/print-crop.png", "extractor": "stage1_intake/extract_pbr_evidence.py", "method": "single-image pixel evidence with de-lighting estimate; not photogrammetry", "usable": true, "verdict": "pass", "confidence": 0.833, "estimatedFidelity": 0.833, "targetThreshold": 0.7, "hardLimit": "A single image cannot uniquely recover true albedo/roughness/normal/AO; maps are reference-derived estimates.", "maps": { "albedo": { "path": "/home/user/DP/3d/material-evidence/print/print-green_albedo.png", "url": "material-evidence/print/print-green_albedo.png", "channel": "albedo", "source": "reference-pixel-extraction" }, "roughness": { "path": "/home/user/DP/3d/material-evidence/print/print-green_roughness.png", "url": "material-evidence/print/print-green_roughness.png", "channel": "roughness", "source": "reference-pixel-extraction" }, "height": { "path": "/home/user/DP/3d/material-evidence/print/print-green_height.png", "url": "material-evidence/print/print-green_height.png", "channel": "height", "source": "reference-pixel-extraction" }, "normal": { "path": "/home/user/DP/3d/material-evidence/print/print-green_normal.png", "url": "material-evidence/print/print-green_normal.png", "channel": "normal", "source": "reference-pixel-extraction" }, "ao": { "path": "/home/user/DP/3d/material-evidence/print/print-green_ao.png", "url": "material-evidence/print/print-green_ao.png", "channel": "ao", "source": "reference-pixel-extraction" } }, "diagnostics": { "sourceWidth": 240, "sourceHeight": 200, "mapSize": 1024, "cropBBoxPixels": { "x": 2, "y": 0, "width": 236, "height": 200 }, "mask": { "backgroundColor": "#000000", "backgroundNoise": 0.0, "transparentPixelFraction": 0.0, "foregroundCoverage": 0.181 }, "mapStats": { "valueRange": 0.2238, "heightP90Gradient": 0.01779, "roughnessBase": 0.68, "roughnessVariation": 0.05, "normalStrength": 0.177, "blurRadius": 21 }, "palette": ["#010301", "#060202", "#030E09", "#0E241C", "#214337"] }, "warnings": ["single-image inverse rendering cannot prove true physical PBR; confidence is capped", "low value range weakens height/roughness inference"] }, "textureResolution": 1024, "albedo": { "dominant": "#010301", "secondary": ["#060202", "#030E09", "#0E241C"], "samplingNotes": "Reference-derived from foreground pixels; de-lit to reduce baked shadows/highlights.", "map": { "path": "/home/user/DP/3d/material-evidence/print/print-green_albedo.png", "url": "material-evidence/print/print-green_albedo.png", "channel": "albedo", "source": "reference-pixel-extraction" } }, "colorVariation": { "palette": ["#010301", "#060202", "#030E09", "#0E241C", "#214337"], "pattern": "reference-derived pixel palette", "amplitude": 0.094, "heightCorrelation": 0.42 }, "normal": { "pattern": "reference-derived height-gradient normal map", "strength": 0.177, "map": { "path": "/home/user/DP/3d/material-evidence/print/print-green_normal.png", "url": "material-evidence/print/print-green_normal.png", "channel": "normal", "source": "reference-pixel-extraction" }, "heightSource": { "path": "/home/user/DP/3d/material-evidence/print/print-green_height.png", "url": "material-evidence/print/print-green_height.png", "channel": "height", "source": "reference-pixel-extraction" }, "space": "tangent" }, "bump": { "pattern": "reference-derived height field", "amplitude": 0.01, "map": { "path": "/home/user/DP/3d/material-evidence/print/print-green_height.png", "url": "material-evidence/print/print-green_height.png", "channel": "height", "source": "reference-pixel-extraction" } }, "surfaceFrequencyBands": [{ "id": "macro", "frequency": 2.0, "amplitude": 0.358, "role": "reference-derived broad albedo and height breakup" }, { "id": "meso", "frequency": 14.0, "amplitude": 0.225, "role": "reference-derived cracks, ridges, pores, grain, or leaf clusters" }, { "id": "micro", "frequency": 72.0, "amplitude": 0.098, "role": "reference-derived micro highlight breakup under grazing light" }], "shaderNotes": ["Reference-derived maps are estimates from image pixels; verify with neutral, grazing, and reference-matched renders.", "Do not treat baked image shadows as final albedo; rerun extraction with a tighter material crop if highlights/shadows pollute the maps."], "textureProjection": { "mode": "planar-front-uv", "texelDensity": "1024 px across 0.9u decal width (~1138 px/u)", "repeat": [1, 1], "anisotropy": 4 }, "agentReview": "analyze_texture classified this crop as worn-composite/mottle because it is 95% black lacquer; visual inspection: flat green ink lettering on black, no mottle. The decal albedo is a generated canvas texture (glyph + wordmark + subline) drawn in green #0f8a5f on transparent.", "runtimeDecal": { "source": "generated canvas texture", "module": "3d/decals.js", "layers": ["double-g-glyph (emblem-glyph-decal)", "wordmark + subline (text-decal)"], "color": "#0f8a5f", "note": "Approximate typography; not the brand font." } }, options);
    const nodes = { root };
    const meshes = {};
    const sockets = {};
    const colliders = {};
    const destructionGroups = {};
    const endpoint_body_lower_0 = makeAttachmentEndpoint(null);
    const node_body_lower_0 = new THREE.Group();
    node_body_lower_0.name = "Body lower (black lacquer)__pivot";
    node_body_lower_0.scale.set(1, 1, 1);
    if (endpoint_body_lower_0) {
        node_body_lower_0.position.copy(endpoint_body_lower_0.start);
        node_body_lower_0.rotation.set(0.0, 0.0, 0.0);
    }
    else {
        node_body_lower_0.position.set(0.0, 0.0, -0.225);
        node_body_lower_0.rotation.set(0.0, 0.0, 0.0);
    }
    node_body_lower_0.userData.sculptComponent = { "id": "body-lower", "name": "Body lower (black lacquer)", "level": "macro", "role": "body", "importance": 1.0, "confidence": 0.8, "primitive": "extrude", "topologyClass": "assembled-solid", "topologyRationale": "Front silhouette is a filleted, slightly tapered rectangle with constant thickness: an extruded 2D profile.", "geometryDescriptor": { "topologyIntent": "extruded filleted profile, base fillet r0.12", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry", "profile2D": { "points": [[-0.49562654320987654, 1.075], [-0.487, 0.12], [-0.4847, 0.0966], [-0.4779, 0.0741], [-0.4668, 0.0533], [-0.4519, 0.0351], [-0.4337, 0.0202], [-0.4129, 0.0091], [-0.3904, 0.0023], [-0.367, 0.0], [0.367, 0.0], [0.3904, 0.0023], [0.4129, 0.0091], [0.4337, 0.0202], [0.4519, 0.0351], [0.4668, 0.0533], [0.4779, 0.0741], [0.4847, 0.0966], [0.487, 0.12], [0.49562654320987654, 1.075]], "depth": 0.45 } }, "parent": null, "attachment": null, "dimensions": { "width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.8 }, "transform": { "position": [0, 0, -0.225], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "root", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "body-lower", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "lacquer-black" } }, "material": "lacquer-black", "materialLayers": ["glass-base", "lacquer-black"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{ "id": "base-fillet", "type": "fillet", "radius": 0.12, "evidence": "reference rows y960-992" }, { "id": "split-line", "type": "material-boundary", "y": 1.075, "evidence": "colour change at y566" }], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:lower-two-thirds"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(3, 3, 3, 1.0)", "secondaryAlbedo": "rgba(55, 55, 55, 1.0)", "materialClass": "glass", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:lower-two-thirds"] } };
    node_body_lower_0.userData.actionProfile = { "animationRole": "root", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "body-lower", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "lacquer-black" } };
    (nodes["root"] ?? root).add(node_body_lower_0);
    nodes["body-lower"] = node_body_lower_0;
    const mesh_body_lower_0Geometry = endpoint_body_lower_0
        ? new THREE.CylinderGeometry(endpoint_body_lower_0.endRadius, endpoint_body_lower_0.baseRadius, endpoint_body_lower_0.length, 32, 12)
        : buildExtrudeGeometry({ "points": [[-0.49562654320987654, 1.075], [-0.487, 0.12], [-0.4847, 0.0966], [-0.4779, 0.0741], [-0.4668, 0.0533], [-0.4519, 0.0351], [-0.4337, 0.0202], [-0.4129, 0.0091], [-0.3904, 0.0023], [-0.367, 0.0], [0.367, 0.0], [0.3904, 0.0023], [0.4129, 0.0091], [0.4337, 0.0202], [0.4519, 0.0351], [0.4668, 0.0533], [0.4779, 0.0741], [0.4847, 0.0966], [0.487, 0.12], [0.49562654320987654, 1.075]], "depth": 0.45 });
    if (!endpoint_body_lower_0) {
        mesh_body_lower_0Geometry.scale(1.0, 1.0, 1.0);
    }
    const mesh_body_lower_0 = new THREE.Mesh(mesh_body_lower_0Geometry, materialMap["lacquer-black"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 }));
    mesh_body_lower_0.name = "Body lower (black lacquer)";
    if (endpoint_body_lower_0) {
        mesh_body_lower_0.position.copy(endpoint_body_lower_0.midpoint);
        mesh_body_lower_0.quaternion.copy(endpoint_body_lower_0.quaternion);
    }
    mesh_body_lower_0.castShadow = options.castShadow ?? true;
    mesh_body_lower_0.receiveShadow = options.receiveShadow ?? true;
    mesh_body_lower_0.userData.sculptComponent = { "id": "body-lower", "name": "Body lower (black lacquer)", "level": "macro", "role": "body", "importance": 1.0, "confidence": 0.8, "primitive": "extrude", "topologyClass": "assembled-solid", "topologyRationale": "Front silhouette is a filleted, slightly tapered rectangle with constant thickness: an extruded 2D profile.", "geometryDescriptor": { "topologyIntent": "extruded filleted profile, base fillet r0.12", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry", "profile2D": { "points": [[-0.49562654320987654, 1.075], [-0.487, 0.12], [-0.4847, 0.0966], [-0.4779, 0.0741], [-0.4668, 0.0533], [-0.4519, 0.0351], [-0.4337, 0.0202], [-0.4129, 0.0091], [-0.3904, 0.0023], [-0.367, 0.0], [0.367, 0.0], [0.3904, 0.0023], [0.4129, 0.0091], [0.4337, 0.0202], [0.4519, 0.0351], [0.4668, 0.0533], [0.4779, 0.0741], [0.4847, 0.0966], [0.487, 0.12], [0.49562654320987654, 1.075]], "depth": 0.45 } }, "parent": null, "attachment": null, "dimensions": { "width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.8 }, "transform": { "position": [0, 0, -0.225], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "root", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "body-lower", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "lacquer-black" } }, "material": "lacquer-black", "materialLayers": ["glass-base", "lacquer-black"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{ "id": "base-fillet", "type": "fillet", "radius": 0.12, "evidence": "reference rows y960-992" }, { "id": "split-line", "type": "material-boundary", "y": 1.075, "evidence": "colour change at y566" }], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:lower-two-thirds"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(3, 3, 3, 1.0)", "secondaryAlbedo": "rgba(55, 55, 55, 1.0)", "materialClass": "glass", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:lower-two-thirds"] } };
    node_body_lower_0.add(mesh_body_lower_0);
    meshes["body-lower"] = mesh_body_lower_0;
    colliders["body-lower"] = { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." };
    destructionGroups["body-lower"] ?? (destructionGroups["body-lower"] = []);
    destructionGroups["body-lower"].push(node_body_lower_0);
    const endpoint_body_upper_1 = makeAttachmentEndpoint(null);
    const node_body_upper_1 = new THREE.Group();
    node_body_upper_1.name = "Body upper (green glass)__pivot";
    node_body_upper_1.scale.set(1, 1, 1);
    if (endpoint_body_upper_1) {
        node_body_upper_1.position.copy(endpoint_body_upper_1.start);
        node_body_upper_1.rotation.set(0.0, 0.0, 0.0);
    }
    else {
        node_body_upper_1.position.set(0.0, 0.0, 0.0);
        node_body_upper_1.rotation.set(0.0, 0.0, 0.0);
    }
    node_body_upper_1.userData.sculptComponent = { "id": "body-upper", "name": "Body upper (green glass)", "level": "macro", "role": "body", "importance": 1.0, "confidence": 0.8, "primitive": "extrude", "topologyClass": "assembled-solid", "topologyRationale": "Same extruded outline as the lower zone, continuing to the rounded shoulders.", "geometryDescriptor": { "topologyIntent": "extruded filleted profile, shoulder fillet r0.08", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry", "profile2D": { "points": [[-0.49562654320987654, 1.075], [0.49562654320987654, 1.075], [0.5, 1.54], [0.4985, 1.5556], [0.4939, 1.5706], [0.4865, 1.5844], [0.4766, 1.5966], [0.4644, 1.6065], [0.4506, 1.6139], [0.4356, 1.6185], [0.42, 1.62], [-0.42, 1.62], [-0.4356, 1.6185], [-0.4506, 1.6139], [-0.4644, 1.6065], [-0.4766, 1.5966], [-0.4865, 1.5844], [-0.4939, 1.5706], [-0.4985, 1.5556], [-0.5, 1.54]], "depth": 0.45 } }, "parent": "body-lower", "attachment": { "parentId": "body-lower", "parentSocket": "split-line", "localStart": [0, 1.07, 0], "localEnd": [0, 1.62, 0], "contactType": "butt", "embedDepth": 0.005, "gapTolerance": 0.002, "evidenceRefs": ["zone:upper-third"] }, "dimensions": { "width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.8 }, "transform": { "position": [0, 0, 0], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "body-upper", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "glass-green" } }, "material": "glass-green", "materialLayers": ["glass-green"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{ "id": "shoulder-fillet", "type": "fillet", "radius": 0.08, "evidence": "reference rows y350-380" }], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:upper-third"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(1, 108, 83, 1.0)", "secondaryAlbedo": "rgba(1, 119, 92, 1.0)", "materialClass": "glass", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:upper-third"], "colorGradient": { "type": "linear", "stops": [{ "position": 0, "color": "rgba(1, 119, 92, 1.0)" }, { "position": 1, "color": "rgba(1, 105, 79, 1.0)" }] } } };
    node_body_upper_1.userData.actionProfile = { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "body-upper", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "glass-green" } };
    (nodes["body-lower"] ?? root).add(node_body_upper_1);
    nodes["body-upper"] = node_body_upper_1;
    const mesh_body_upper_1Geometry = endpoint_body_upper_1
        ? new THREE.CylinderGeometry(endpoint_body_upper_1.endRadius, endpoint_body_upper_1.baseRadius, endpoint_body_upper_1.length, 32, 12)
        : buildExtrudeGeometry({ "points": [[-0.49562654320987654, 1.075], [0.49562654320987654, 1.075], [0.5, 1.54], [0.4985, 1.5556], [0.4939, 1.5706], [0.4865, 1.5844], [0.4766, 1.5966], [0.4644, 1.6065], [0.4506, 1.6139], [0.4356, 1.6185], [0.42, 1.62], [-0.42, 1.62], [-0.4356, 1.6185], [-0.4506, 1.6139], [-0.4644, 1.6065], [-0.4766, 1.5966], [-0.4865, 1.5844], [-0.4939, 1.5706], [-0.4985, 1.5556], [-0.5, 1.54]], "depth": 0.45 });
    if (!endpoint_body_upper_1) {
        mesh_body_upper_1Geometry.scale(1.0, 1.0, 1.0);
    }
    const mesh_body_upper_1 = new THREE.Mesh(mesh_body_upper_1Geometry, materialMap["glass-green"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 }));
    mesh_body_upper_1.name = "Body upper (green glass)";
    if (endpoint_body_upper_1) {
        mesh_body_upper_1.position.copy(endpoint_body_upper_1.midpoint);
        mesh_body_upper_1.quaternion.copy(endpoint_body_upper_1.quaternion);
    }
    mesh_body_upper_1.castShadow = options.castShadow ?? true;
    mesh_body_upper_1.receiveShadow = options.receiveShadow ?? true;
    mesh_body_upper_1.userData.sculptComponent = { "id": "body-upper", "name": "Body upper (green glass)", "level": "macro", "role": "body", "importance": 1.0, "confidence": 0.8, "primitive": "extrude", "topologyClass": "assembled-solid", "topologyRationale": "Same extruded outline as the lower zone, continuing to the rounded shoulders.", "geometryDescriptor": { "topologyIntent": "extruded filleted profile, shoulder fillet r0.08", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry", "profile2D": { "points": [[-0.49562654320987654, 1.075], [0.49562654320987654, 1.075], [0.5, 1.54], [0.4985, 1.5556], [0.4939, 1.5706], [0.4865, 1.5844], [0.4766, 1.5966], [0.4644, 1.6065], [0.4506, 1.6139], [0.4356, 1.6185], [0.42, 1.62], [-0.42, 1.62], [-0.4356, 1.6185], [-0.4506, 1.6139], [-0.4644, 1.6065], [-0.4766, 1.5966], [-0.4865, 1.5844], [-0.4939, 1.5706], [-0.4985, 1.5556], [-0.5, 1.54]], "depth": 0.45 } }, "parent": "body-lower", "attachment": { "parentId": "body-lower", "parentSocket": "split-line", "localStart": [0, 1.07, 0], "localEnd": [0, 1.62, 0], "contactType": "butt", "embedDepth": 0.005, "gapTolerance": 0.002, "evidenceRefs": ["zone:upper-third"] }, "dimensions": { "width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.8 }, "transform": { "position": [0, 0, 0], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "body-upper", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "glass-green" } }, "material": "glass-green", "materialLayers": ["glass-green"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{ "id": "shoulder-fillet", "type": "fillet", "radius": 0.08, "evidence": "reference rows y350-380" }], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:upper-third"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(1, 108, 83, 1.0)", "secondaryAlbedo": "rgba(1, 119, 92, 1.0)", "materialClass": "glass", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:upper-third"], "colorGradient": { "type": "linear", "stops": [{ "position": 0, "color": "rgba(1, 119, 92, 1.0)" }, { "position": 1, "color": "rgba(1, 105, 79, 1.0)" }] } } };
    node_body_upper_1.add(mesh_body_upper_1);
    meshes["body-upper"] = mesh_body_upper_1;
    colliders["body-upper"] = { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." };
    destructionGroups["body-upper"] ?? (destructionGroups["body-upper"] = []);
    destructionGroups["body-upper"].push(node_body_upper_1);
    const attachment_collar_2 = { "parentId": "body-lower", "parentSocket": "body-top-centre", "localStart": [0, 1.6150000000000002, 0.225], "localEnd": [0, 1.7000000000000002, 0.225], "contactType": "butt", "embedDepth": 0.005, "gapTolerance": 0.002, "evidenceRefs": ["zone:neck"], "baseRadius": 0.12, "endRadius": 0.12 };
    const endpoint_collar_2 = makeAttachmentEndpoint(attachment_collar_2);
    const node_collar_2 = new THREE.Group();
    node_collar_2.name = "Collar__pivot";
    node_collar_2.scale.set(1, 1, 1);
    if (endpoint_collar_2) {
        node_collar_2.position.copy(endpoint_collar_2.start);
        node_collar_2.rotation.set(0.0, 0.0, 0.0);
    }
    else {
        node_collar_2.position.set(0.0, 1.6600000000000001, 0.225);
        node_collar_2.rotation.set(0.0, 0.0, 0.0);
    }
    node_collar_2.userData.sculptComponent = { "id": "collar", "name": "Collar", "level": "macro", "role": "connector", "importance": 0.7, "confidence": 0.6, "primitive": "cylinder", "topologyClass": "assembled-solid", "topologyRationale": "Short round neck between shoulder and cap; radially symmetric.", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry" }, "parent": "body-lower", "attachment": { "parentId": "body-lower", "parentSocket": "body-top-centre", "localStart": [0, 1.6150000000000002, 0.225], "localEnd": [0, 1.7000000000000002, 0.225], "contactType": "butt", "embedDepth": 0.005, "gapTolerance": 0.002, "evidenceRefs": ["zone:neck"], "baseRadius": 0.12, "endRadius": 0.12 }, "dimensions": { "width": 0.24, "height": 0.08, "depth": 0.24, "units": "relative", "confidence": 0.6 }, "transform": { "position": [0, 1.6600000000000001, 0.225], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "collar", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "cap-black" } }, "material": "cap-black", "materialLayers": ["cap-black"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:neck"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(2, 2, 2, 1.0)", "secondaryAlbedo": "rgba(12, 12, 12, 1.0)", "materialClass": "plastic", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:neck"] } };
    node_collar_2.userData.actionProfile = { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "collar", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "cap-black" } };
    (nodes["body-lower"] ?? root).add(node_collar_2);
    nodes["collar"] = node_collar_2;
    const mesh_collar_2Geometry = endpoint_collar_2
        ? new THREE.CylinderGeometry(endpoint_collar_2.endRadius, endpoint_collar_2.baseRadius, endpoint_collar_2.length, 32, 12)
        : new THREE.CylinderGeometry(0.5, 0.5, 1, 48, 16);
    if (!endpoint_collar_2) {
        mesh_collar_2Geometry.scale(0.24, 0.08, 0.24);
    }
    const mesh_collar_2 = new THREE.Mesh(mesh_collar_2Geometry, materialMap["cap-black"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 }));
    mesh_collar_2.name = "Collar";
    if (endpoint_collar_2) {
        mesh_collar_2.position.copy(endpoint_collar_2.midpoint);
        mesh_collar_2.quaternion.copy(endpoint_collar_2.quaternion);
    }
    mesh_collar_2.castShadow = options.castShadow ?? true;
    mesh_collar_2.receiveShadow = options.receiveShadow ?? true;
    mesh_collar_2.userData.sculptComponent = { "id": "collar", "name": "Collar", "level": "macro", "role": "connector", "importance": 0.7, "confidence": 0.6, "primitive": "cylinder", "topologyClass": "assembled-solid", "topologyRationale": "Short round neck between shoulder and cap; radially symmetric.", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry" }, "parent": "body-lower", "attachment": { "parentId": "body-lower", "parentSocket": "body-top-centre", "localStart": [0, 1.6150000000000002, 0.225], "localEnd": [0, 1.7000000000000002, 0.225], "contactType": "butt", "embedDepth": 0.005, "gapTolerance": 0.002, "evidenceRefs": ["zone:neck"], "baseRadius": 0.12, "endRadius": 0.12 }, "dimensions": { "width": 0.24, "height": 0.08, "depth": 0.24, "units": "relative", "confidence": 0.6 }, "transform": { "position": [0, 1.6600000000000001, 0.225], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "collar", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "cap-black" } }, "material": "cap-black", "materialLayers": ["cap-black"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:neck"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(2, 2, 2, 1.0)", "secondaryAlbedo": "rgba(12, 12, 12, 1.0)", "materialClass": "plastic", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:neck"] } };
    node_collar_2.add(mesh_collar_2);
    meshes["collar"] = mesh_collar_2;
    colliders["collar"] = { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." };
    destructionGroups["collar"] ?? (destructionGroups["collar"] = []);
    destructionGroups["collar"].push(node_collar_2);
    const endpoint_overcap_3 = makeAttachmentEndpoint(null);
    const node_overcap_3 = new THREE.Group();
    node_overcap_3.name = "Overcap__pivot";
    node_overcap_3.scale.set(1, 1, 1);
    if (endpoint_overcap_3) {
        node_overcap_3.position.copy(endpoint_overcap_3.start);
        node_overcap_3.rotation.set(0.0, 0.0, 0.0);
    }
    else {
        node_overcap_3.position.set(0.0, 1.8350000000000002, 0.225);
        node_overcap_3.rotation.set(0.0, 0.0, 0.0);
    }
    node_overcap_3.userData.sculptComponent = { "id": "overcap", "name": "Overcap", "level": "macro", "role": "cap", "importance": 1.0, "confidence": 0.75, "primitive": "box", "topologyClass": "assembled-solid", "topologyRationale": "Squared block cap with small edge fillet; read as a cuboid at this scale.", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "bevel", "bevelRadius": 0.02, "segments": 2 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry" }, "parent": "body-lower", "attachment": { "parentId": "body-lower", "parentSocket": "collar-top", "localStart": [0, 1.6800000000000002, 0.225], "localEnd": [0, 1.9700000000000002, 0.225], "contactType": "socket", "overlap": 0.02, "gapTolerance": 0.002, "evidenceRefs": ["zone:cap"] }, "dimensions": { "width": 0.35, "height": 0.27, "depth": 0.3, "units": "relative", "confidence": 0.75 }, "transform": { "position": [0, 1.8350000000000002, 0.225], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "base", "localPosition": [0, -0.135, 0], "axis": [0, 1, 0], "confidence": 0.7 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "overcap", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "cap-black" } }, "material": "cap-black", "materialLayers": ["cap-black"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:cap"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(2, 2, 2, 1.0)", "secondaryAlbedo": "rgba(40, 40, 40, 1.0)", "materialClass": "plastic", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:cap"] } };
    node_overcap_3.userData.actionProfile = { "animationRole": "child", "pivot": { "mode": "base", "localPosition": [0, -0.135, 0], "axis": [0, 1, 0], "confidence": 0.7 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "overcap", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "cap-black" } };
    (nodes["body-lower"] ?? root).add(node_overcap_3);
    nodes["overcap"] = node_overcap_3;
    const mesh_overcap_3Geometry = endpoint_overcap_3
        ? new THREE.CylinderGeometry(endpoint_overcap_3.endRadius, endpoint_overcap_3.baseRadius, endpoint_overcap_3.length, 32, 12)
        : new THREE.BoxGeometry(1, 1, 1, 12, 12, 12);
    if (!endpoint_overcap_3) {
        mesh_overcap_3Geometry.scale(0.35, 0.27, 0.3);
    }
    const mesh_overcap_3 = new THREE.Mesh(mesh_overcap_3Geometry, materialMap["cap-black"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 }));
    mesh_overcap_3.name = "Overcap";
    if (endpoint_overcap_3) {
        mesh_overcap_3.position.copy(endpoint_overcap_3.midpoint);
        mesh_overcap_3.quaternion.copy(endpoint_overcap_3.quaternion);
    }
    mesh_overcap_3.castShadow = options.castShadow ?? true;
    mesh_overcap_3.receiveShadow = options.receiveShadow ?? true;
    mesh_overcap_3.userData.sculptComponent = { "id": "overcap", "name": "Overcap", "level": "macro", "role": "cap", "importance": 1.0, "confidence": 0.75, "primitive": "box", "topologyClass": "assembled-solid", "topologyRationale": "Squared block cap with small edge fillet; read as a cuboid at this scale.", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "bevel", "bevelRadius": 0.02, "segments": 2 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry" }, "parent": "body-lower", "attachment": { "parentId": "body-lower", "parentSocket": "collar-top", "localStart": [0, 1.6800000000000002, 0.225], "localEnd": [0, 1.9700000000000002, 0.225], "contactType": "socket", "overlap": 0.02, "gapTolerance": 0.002, "evidenceRefs": ["zone:cap"] }, "dimensions": { "width": 0.35, "height": 0.27, "depth": 0.3, "units": "relative", "confidence": 0.75 }, "transform": { "position": [0, 1.8350000000000002, 0.225], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "base", "localPosition": [0, -0.135, 0], "axis": [0, 1, 0], "confidence": 0.7 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "overcap", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "cap-black" } }, "material": "cap-black", "materialLayers": ["cap-black"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:cap"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(2, 2, 2, 1.0)", "secondaryAlbedo": "rgba(40, 40, 40, 1.0)", "materialClass": "plastic", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:cap"] } };
    node_overcap_3.add(mesh_overcap_3);
    meshes["overcap"] = mesh_overcap_3;
    colliders["overcap"] = { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." };
    destructionGroups["overcap"] ?? (destructionGroups["overcap"] = []);
    destructionGroups["overcap"].push(node_overcap_3);
    const endpoint_emblem_ring_4 = makeAttachmentEndpoint(null);
    const node_emblem_ring_4 = new THREE.Group();
    node_emblem_ring_4.name = "Emblem ring__pivot";
    node_emblem_ring_4.scale.set(1, 1, 1);
    if (endpoint_emblem_ring_4) {
        node_emblem_ring_4.position.copy(endpoint_emblem_ring_4.start);
        node_emblem_ring_4.rotation.set(0.0, 0.0, 0.0);
    }
    else {
        node_emblem_ring_4.position.set(0.0, 0.864, 0.454);
        node_emblem_ring_4.rotation.set(0.0, 0.0, 0.0);
    }
    node_emblem_ring_4.userData.sculptComponent = { "id": "emblem-ring", "name": "Emblem ring", "level": "meso", "role": "detail", "importance": 0.7, "confidence": 0.65, "primitive": "torus", "topologyClass": "surface-relief", "topologyRationale": "Raised circular rim around the emblem; a torus in the front plane.", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry", "torusTubeRatio": 0.13 }, "parent": "body-lower", "attachment": { "parentId": "body-lower", "parentSocket": "front-face-emblem", "localStart": [0, 0.864, 0.44], "localEnd": [0, 0.864, 0.465], "contactType": "embed", "embedDepth": 0.01, "gapTolerance": 0.001, "evidenceRefs": ["zone:emblem"] }, "dimensions": { "width": 0.46, "height": 0.46, "depth": 0.46, "units": "relative", "confidence": 0.65 }, "transform": { "position": [0, 0.864, 0.454], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "emblem-ring", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "lacquer-black" } }, "material": "lacquer-black", "materialLayers": ["lacquer-black"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:emblem"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(5, 5, 5, 1.0)", "secondaryAlbedo": "rgba(55, 55, 55, 1.0)", "materialClass": "glass", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:emblem"] } };
    node_emblem_ring_4.userData.actionProfile = { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "emblem-ring", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "lacquer-black" } };
    (nodes["body-lower"] ?? root).add(node_emblem_ring_4);
    nodes["emblem-ring"] = node_emblem_ring_4;
    const mesh_emblem_ring_4Geometry = endpoint_emblem_ring_4
        ? new THREE.CylinderGeometry(endpoint_emblem_ring_4.endRadius, endpoint_emblem_ring_4.baseRadius, endpoint_emblem_ring_4.length, 32, 12)
        : new THREE.TorusGeometry(0.45, 0.0585, 24, 96);
    if (!endpoint_emblem_ring_4) {
        mesh_emblem_ring_4Geometry.scale(0.46, 0.46, 0.46);
    }
    const mesh_emblem_ring_4 = new THREE.Mesh(mesh_emblem_ring_4Geometry, materialMap["lacquer-black"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 }));
    mesh_emblem_ring_4.name = "Emblem ring";
    if (endpoint_emblem_ring_4) {
        mesh_emblem_ring_4.position.copy(endpoint_emblem_ring_4.midpoint);
        mesh_emblem_ring_4.quaternion.copy(endpoint_emblem_ring_4.quaternion);
    }
    mesh_emblem_ring_4.castShadow = options.castShadow ?? true;
    mesh_emblem_ring_4.receiveShadow = options.receiveShadow ?? true;
    mesh_emblem_ring_4.userData.sculptComponent = { "id": "emblem-ring", "name": "Emblem ring", "level": "meso", "role": "detail", "importance": 0.7, "confidence": 0.65, "primitive": "torus", "topologyClass": "surface-relief", "topologyRationale": "Raised circular rim around the emblem; a torus in the front plane.", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry", "torusTubeRatio": 0.13 }, "parent": "body-lower", "attachment": { "parentId": "body-lower", "parentSocket": "front-face-emblem", "localStart": [0, 0.864, 0.44], "localEnd": [0, 0.864, 0.465], "contactType": "embed", "embedDepth": 0.01, "gapTolerance": 0.001, "evidenceRefs": ["zone:emblem"] }, "dimensions": { "width": 0.46, "height": 0.46, "depth": 0.46, "units": "relative", "confidence": 0.65 }, "transform": { "position": [0, 0.864, 0.454], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "emblem-ring", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "lacquer-black" } }, "material": "lacquer-black", "materialLayers": ["lacquer-black"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:emblem"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(5, 5, 5, 1.0)", "secondaryAlbedo": "rgba(55, 55, 55, 1.0)", "materialClass": "glass", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:emblem"] } };
    node_emblem_ring_4.add(mesh_emblem_ring_4);
    meshes["emblem-ring"] = mesh_emblem_ring_4;
    colliders["emblem-ring"] = { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." };
    destructionGroups["emblem-ring"] ?? (destructionGroups["emblem-ring"] = []);
    destructionGroups["emblem-ring"].push(node_emblem_ring_4);
    const attachment_emblem_disc_5 = { "parentId": "body-lower", "parentSocket": "front-face-emblem", "localStart": [0, 0.864, 0.449], "localEnd": [0, 0.864, 0.452], "contactType": "embed", "embedDepth": 0.001, "gapTolerance": 0.001, "evidenceRefs": ["zone:emblem"], "baseRadius": 0.2, "endRadius": 0.2 };
    const endpoint_emblem_disc_5 = makeAttachmentEndpoint(attachment_emblem_disc_5);
    const node_emblem_disc_5 = new THREE.Group();
    node_emblem_disc_5.name = "Emblem green disc__pivot";
    node_emblem_disc_5.scale.set(1, 1, 1);
    if (endpoint_emblem_disc_5) {
        node_emblem_disc_5.position.copy(endpoint_emblem_disc_5.start);
        node_emblem_disc_5.rotation.set(0.0, 0.0, 0.0);
    }
    else {
        node_emblem_disc_5.position.set(0.0, 0.864, 0.452);
        node_emblem_disc_5.rotation.set(0.0, 0.0, 0.0);
    }
    node_emblem_disc_5.userData.sculptComponent = { "id": "emblem-disc", "name": "Emblem green disc", "level": "meso", "role": "detail", "importance": 0.7, "confidence": 0.6, "primitive": "cylinder", "topologyClass": "surface-relief", "topologyRationale": "Flat green inlay disc inside the ring; rotated to face +Z.", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry" }, "parent": "body-lower", "attachment": { "parentId": "body-lower", "parentSocket": "front-face-emblem", "localStart": [0, 0.864, 0.449], "localEnd": [0, 0.864, 0.452], "contactType": "embed", "embedDepth": 0.001, "gapTolerance": 0.001, "evidenceRefs": ["zone:emblem"], "baseRadius": 0.2, "endRadius": 0.2 }, "dimensions": { "width": 0.4, "height": 0.006, "depth": 0.4, "units": "relative", "confidence": 0.6 }, "transform": { "position": [0, 0.864, 0.452], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "emblem-disc", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "emblem-green" } }, "material": "emblem-green", "materialLayers": ["emblem-green"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:emblem"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(0, 114, 85, 1.0)", "secondaryAlbedo": "rgba(2, 96, 72, 1.0)", "materialClass": "glass", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:emblem"] } };
    node_emblem_disc_5.userData.actionProfile = { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "emblem-disc", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "emblem-green" } };
    (nodes["body-lower"] ?? root).add(node_emblem_disc_5);
    nodes["emblem-disc"] = node_emblem_disc_5;
    const mesh_emblem_disc_5Geometry = endpoint_emblem_disc_5
        ? new THREE.CylinderGeometry(endpoint_emblem_disc_5.endRadius, endpoint_emblem_disc_5.baseRadius, endpoint_emblem_disc_5.length, 32, 12)
        : new THREE.CylinderGeometry(0.5, 0.5, 1, 48, 16);
    if (!endpoint_emblem_disc_5) {
        mesh_emblem_disc_5Geometry.scale(0.4, 0.006, 0.4);
    }
    const mesh_emblem_disc_5 = new THREE.Mesh(mesh_emblem_disc_5Geometry, materialMap["emblem-green"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 }));
    mesh_emblem_disc_5.name = "Emblem green disc";
    if (endpoint_emblem_disc_5) {
        mesh_emblem_disc_5.position.copy(endpoint_emblem_disc_5.midpoint);
        mesh_emblem_disc_5.quaternion.copy(endpoint_emblem_disc_5.quaternion);
    }
    mesh_emblem_disc_5.castShadow = options.castShadow ?? true;
    mesh_emblem_disc_5.receiveShadow = options.receiveShadow ?? true;
    mesh_emblem_disc_5.userData.sculptComponent = { "id": "emblem-disc", "name": "Emblem green disc", "level": "meso", "role": "detail", "importance": 0.7, "confidence": 0.6, "primitive": "cylinder", "topologyClass": "surface-relief", "topologyRationale": "Flat green inlay disc inside the ring; rotated to face +Z.", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry" }, "parent": "body-lower", "attachment": { "parentId": "body-lower", "parentSocket": "front-face-emblem", "localStart": [0, 0.864, 0.449], "localEnd": [0, 0.864, 0.452], "contactType": "embed", "embedDepth": 0.001, "gapTolerance": 0.001, "evidenceRefs": ["zone:emblem"], "baseRadius": 0.2, "endRadius": 0.2 }, "dimensions": { "width": 0.4, "height": 0.006, "depth": 0.4, "units": "relative", "confidence": 0.6 }, "transform": { "position": [0, 0.864, 0.452], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "emblem-disc", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "emblem-green" } }, "material": "emblem-green", "materialLayers": ["emblem-green"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:emblem"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(0, 114, 85, 1.0)", "secondaryAlbedo": "rgba(2, 96, 72, 1.0)", "materialClass": "glass", "materialClassConfidence": 0.8, "evidenceRefs": ["zone:emblem"] } };
    node_emblem_disc_5.add(mesh_emblem_disc_5);
    meshes["emblem-disc"] = mesh_emblem_disc_5;
    colliders["emblem-disc"] = { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." };
    destructionGroups["emblem-disc"] ?? (destructionGroups["emblem-disc"] = []);
    destructionGroups["emblem-disc"].push(node_emblem_disc_5);
    const endpoint_emblem_glyph_decal_6 = makeAttachmentEndpoint(null);
    const node_emblem_glyph_decal_6 = new THREE.Group();
    node_emblem_glyph_decal_6.name = "Double-G glyph print__pivot";
    node_emblem_glyph_decal_6.scale.set(1, 1, 1);
    if (endpoint_emblem_glyph_decal_6) {
        node_emblem_glyph_decal_6.position.copy(endpoint_emblem_glyph_decal_6.start);
        node_emblem_glyph_decal_6.rotation.set(0.0, 0.0, 0.0);
    }
    else {
        node_emblem_glyph_decal_6.position.set(0.0, 0.864, 0.4535);
        node_emblem_glyph_decal_6.rotation.set(0.0, 0.0, 0.0);
    }
    node_emblem_glyph_decal_6.userData.sculptComponent = { "id": "emblem-glyph-decal", "name": "Double-G glyph print", "level": "meso", "role": "detail", "importance": 0.7, "confidence": 0.5, "primitive": "plane-card", "topologyClass": "material-only", "topologyRationale": "Printed emblem glyph, wordmark line and subline on the front face; flat decal carrying a generated canvas texture. Part of the emblem sub-assembly (ring + inlay + glyph).", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry" }, "parent": "body-lower", "attachment": null, "dimensions": { "width": 0.46, "height": 0.46, "depth": 1, "units": "relative", "confidence": 0.5 }, "transform": { "position": [0, 0.864, 0.4535], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "emblem-glyph-decal", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "print-green" } }, "material": "print-green", "materialLayers": ["print-green"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{ "id": "double-g-glyph", "type": "print", "y": 0.864 }], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:emblem"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(15, 138, 95, 1.0)", "secondaryAlbedo": "rgba(0, 35, 23, 1.0)", "materialClass": "unknown", "materialClassConfidence": 0.4, "evidenceRefs": ["zone:emblem"] } };
    node_emblem_glyph_decal_6.userData.actionProfile = { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "emblem-glyph-decal", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "print-green" } };
    (nodes["body-lower"] ?? root).add(node_emblem_glyph_decal_6);
    nodes["emblem-glyph-decal"] = node_emblem_glyph_decal_6;
    const mesh_emblem_glyph_decal_6Geometry = endpoint_emblem_glyph_decal_6
        ? new THREE.CylinderGeometry(endpoint_emblem_glyph_decal_6.endRadius, endpoint_emblem_glyph_decal_6.baseRadius, endpoint_emblem_glyph_decal_6.length, 32, 12)
        : new THREE.PlaneGeometry(1, 1, 24, 24);
    if (!endpoint_emblem_glyph_decal_6) {
        mesh_emblem_glyph_decal_6Geometry.scale(0.46, 0.46, 1.0);
    }
    const mesh_emblem_glyph_decal_6 = new THREE.Mesh(mesh_emblem_glyph_decal_6Geometry, materialMap["print-green"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 }));
    mesh_emblem_glyph_decal_6.name = "Double-G glyph print";
    if (endpoint_emblem_glyph_decal_6) {
        mesh_emblem_glyph_decal_6.position.copy(endpoint_emblem_glyph_decal_6.midpoint);
        mesh_emblem_glyph_decal_6.quaternion.copy(endpoint_emblem_glyph_decal_6.quaternion);
    }
    mesh_emblem_glyph_decal_6.castShadow = options.castShadow ?? true;
    mesh_emblem_glyph_decal_6.receiveShadow = options.receiveShadow ?? true;
    mesh_emblem_glyph_decal_6.userData.sculptComponent = { "id": "emblem-glyph-decal", "name": "Double-G glyph print", "level": "meso", "role": "detail", "importance": 0.7, "confidence": 0.5, "primitive": "plane-card", "topologyClass": "material-only", "topologyRationale": "Printed emblem glyph, wordmark line and subline on the front face; flat decal carrying a generated canvas texture. Part of the emblem sub-assembly (ring + inlay + glyph).", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry" }, "parent": "body-lower", "attachment": null, "dimensions": { "width": 0.46, "height": 0.46, "depth": 1, "units": "relative", "confidence": 0.5 }, "transform": { "position": [0, 0.864, 0.4535], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "emblem-glyph-decal", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "print-green" } }, "material": "print-green", "materialLayers": ["print-green"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{ "id": "double-g-glyph", "type": "print", "y": 0.864 }], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:emblem"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(15, 138, 95, 1.0)", "secondaryAlbedo": "rgba(0, 35, 23, 1.0)", "materialClass": "unknown", "materialClassConfidence": 0.4, "evidenceRefs": ["zone:emblem"] } };
    node_emblem_glyph_decal_6.add(mesh_emblem_glyph_decal_6);
    meshes["emblem-glyph-decal"] = mesh_emblem_glyph_decal_6;
    colliders["emblem-glyph-decal"] = { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." };
    destructionGroups["emblem-glyph-decal"] ?? (destructionGroups["emblem-glyph-decal"] = []);
    destructionGroups["emblem-glyph-decal"].push(node_emblem_glyph_decal_6);
    const endpoint_text_decal_7 = makeAttachmentEndpoint(null);
    const node_text_decal_7 = new THREE.Group();
    node_text_decal_7.name = "Wordmark and subline print__pivot";
    node_text_decal_7.scale.set(1, 1, 1);
    if (endpoint_text_decal_7) {
        node_text_decal_7.position.copy(endpoint_text_decal_7.start);
        node_text_decal_7.rotation.set(0.0, 0.0, 0.0);
    }
    else {
        node_text_decal_7.position.set(0.0, 0.4, 0.453);
        node_text_decal_7.rotation.set(0.0, 0.0, 0.0);
    }
    node_text_decal_7.userData.sculptComponent = { "id": "text-decal", "name": "Wordmark and subline print", "level": "micro", "role": "detail", "importance": 0.7, "confidence": 0.5, "primitive": "plane-card", "topologyClass": "material-only", "topologyRationale": "Printed emblem glyph, wordmark line and subline on the front face; flat decal carrying a generated canvas texture.", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry" }, "parent": "body-lower", "attachment": null, "dimensions": { "width": 0.8, "height": 0.6, "depth": 1, "units": "relative", "confidence": 0.5 }, "transform": { "position": [0, 0.4, 0.453], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "text-decal", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "print-green" } }, "material": "print-green", "materialLayers": ["print-green"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{ "id": "wordmark", "type": "print", "y": 0.606 }, { "id": "subline", "type": "print", "y": 0.187 }], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:print"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(15, 138, 95, 1.0)", "secondaryAlbedo": "rgba(0, 35, 23, 1.0)", "materialClass": "unknown", "materialClassConfidence": 0.4, "evidenceRefs": ["zone:print"] } };
    node_text_decal_7.userData.actionProfile = { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "text-decal", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "print-green" } };
    (nodes["body-lower"] ?? root).add(node_text_decal_7);
    nodes["text-decal"] = node_text_decal_7;
    const mesh_text_decal_7Geometry = endpoint_text_decal_7
        ? new THREE.CylinderGeometry(endpoint_text_decal_7.endRadius, endpoint_text_decal_7.baseRadius, endpoint_text_decal_7.length, 32, 12)
        : new THREE.PlaneGeometry(1, 1, 24, 24);
    if (!endpoint_text_decal_7) {
        mesh_text_decal_7Geometry.scale(0.8, 0.6, 1.0);
    }
    const mesh_text_decal_7 = new THREE.Mesh(mesh_text_decal_7Geometry, materialMap["print-green"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 }));
    mesh_text_decal_7.name = "Wordmark and subline print";
    if (endpoint_text_decal_7) {
        mesh_text_decal_7.position.copy(endpoint_text_decal_7.midpoint);
        mesh_text_decal_7.quaternion.copy(endpoint_text_decal_7.quaternion);
    }
    mesh_text_decal_7.castShadow = options.castShadow ?? true;
    mesh_text_decal_7.receiveShadow = options.receiveShadow ?? true;
    mesh_text_decal_7.userData.sculptComponent = { "id": "text-decal", "name": "Wordmark and subline print", "level": "micro", "role": "detail", "importance": 0.7, "confidence": 0.5, "primitive": "plane-card", "topologyClass": "material-only", "topologyRationale": "Printed emblem glyph, wordmark line and subline on the front face; flat decal carrying a generated canvas texture.", "geometryDescriptor": { "topologyIntent": "low-poly blockout with bevel-ready edges", "edgeTreatment": { "type": "none", "bevelRadius": 0.0, "segments": 1 }, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "vertex normals from generated geometry" }, "parent": "body-lower", "attachment": null, "dimensions": { "width": 0.8, "height": 0.6, "depth": 1, "units": "relative", "confidence": 0.5 }, "transform": { "position": [0, 0.4, 0.453], "rotation": [0, 0, 0] }, "actionProfile": { "animationRole": "child", "pivot": { "mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.5 }, "transformChannels": { "translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true }, "sockets": [], "collider": { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." }, "constraints": [], "destruction": { "breakable": false, "fractureGroup": "text-decal", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0.0, "debrisMaterial": "print-green" } }, "material": "print-green", "materialLayers": ["print-green"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{ "id": "wordmark", "type": "print", "y": 0.606 }, { "id": "subline", "type": "print", "y": 0.187 }], "surfaceDetail": { "macroRoughness": 0.0, "microRoughness": 0.0, "bumpAmplitude": 0.0, "normalPattern": "", "displacementPattern": "", "occlusionPattern": "", "edgeWearPattern": "", "notes": "" }, "evidenceRefs": ["zone:print"], "details": [], "fidelityTier": "form", "colorMaterialRecipe": { "dominantAlbedo": "rgba(15, 138, 95, 1.0)", "secondaryAlbedo": "rgba(0, 35, 23, 1.0)", "materialClass": "unknown", "materialClassConfidence": 0.4, "evidenceRefs": ["zone:print"] } };
    node_text_decal_7.add(mesh_text_decal_7);
    meshes["text-decal"] = mesh_text_decal_7;
    colliders["text-decal"] = { "type": "box", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Replace with sphere/capsule/compound proxy when the object shape demands it." };
    destructionGroups["text-decal"] ?? (destructionGroups["text-decal"] = []);
    destructionGroups["text-decal"].push(node_text_decal_7);
    root.userData.sculptRuntime = { nodes, meshes, sockets, colliders, destructionGroups };
    root.userData.lookDevTargets = { "qualityPriority": "reference-fidelity", "materialPass": { "albedoPaletteRequired": true, "roughnessVariationRequired": true, "normalOrBumpRequired": true, "localOverridesRequired": true, "minimumTextureResolution": 1024, "preferredTextureResolution": 2048, "independentMapChannels": ["albedo", "roughness", "height", "normal", "ambient-occlusion"], "requiredSurfaceFrequencyBands": ["macro", "meso", "micro"], "geometryReliefRequiredWhenSilhouetteAffected": true, "referencePbrExtraction": { "requiredWhenSourceImagePresent": true, "targetThreshold": 0.7, "stopOnLowConfidence": true, "script": "forge/stage1_intake/extract_pbr_evidence.py", "acceptedLimitation": "single-image extraction is reference-derived inference, not exact photogrammetry" }, "mustAvoid": ["single flat albedo per material", "uniform roughness", "albedo texture reused as roughness/height/normal/AO", "single-frequency random noise", "plastic-looking smooth bark, stone, cloth, foliage, or aged material", "local color/detail described only in prose without material masks", "claiming exact PBR recovery when confidence is below the target threshold"] }, "lightingPass": { "requiredTerms": ["key light", "fill light", "rim or environment light", "exposure", "tone mapping", "background", "contact shadow"], "mustAvoid": ["ambient-only lighting", "flat value range", "missing contact shadow", "reference lighting copied without separating material readability"] }, "screenshotReview": ["Compare albedo palette and local color zones.", "Compare roughness/normal/bump response under light.", "Compare cavity dirt, edge wear, stains, moss, scratches, or other local masks.", "Compare key/fill/rim structure, exposure, tone mapping, background, and contact shadows.", "Capture a neutral-light render to verify material readability without reference lighting.", "Capture a grazing-light close-up to expose flat normals, uniform roughness, tiling, and plastic highlights.", "Capture a reference-matched render from the same camera framing as the source."] };
    root.userData.actionReadiness = {
        note: 'Use root.userData.sculptRuntime.nodes for transforms, sockets for attachments, colliders for physics proxies, and destructionGroups for breakable sets.',
    };
    return root;
}
export function createFragranceFlaconTwoZoneLookDevLights(mode = 'neutral') {
    const lights = new THREE.Group();
    lights.name = "Fragrance Flacon Two-Zone look-dev lights";
    const hemi = new THREE.HemisphereLight(mode === 'reference' ? 0xfff0d6 : 0xf2f4ff, 0x363b42, mode === 'grazing' ? 0.28 : mode === 'reference' ? 0.72 : 0.85);
    lights.add(hemi);
    const key = new THREE.DirectionalLight(mode === 'reference' ? 0xffcf8a : 0xfff4e8, mode === 'grazing' ? 4.2 : mode === 'reference' ? 2.6 : 2.15);
    if (mode === 'grazing')
        key.position.set(7.5, 1.1, 4.0);
    else if (mode === 'reference')
        key.position.set(-4.5, 7.5, 5.0);
    else
        key.position.set(-4.0, 6.0, 5.5);
    key.castShadow = true;
    key.shadow.mapSize.set(4096, 4096);
    key.shadow.bias = -0.00025;
    key.shadow.normalBias = 0.018;
    key.shadow.radius = 7;
    key.shadow.blurSamples = 24;
    key.shadow.camera.near = 0.5;
    key.shadow.camera.far = 30;
    key.shadow.camera.left = -2.6;
    key.shadow.camera.right = 2.6;
    key.shadow.camera.top = 2.6;
    key.shadow.camera.bottom = -2.6;
    key.shadow.camera.updateProjectionMatrix();
    lights.add(key);
    const fill = new THREE.DirectionalLight(0xa8c4ff, mode === 'grazing' ? 0.12 : 0.42);
    fill.position.set(4.0, 3.0, 3.5);
    lights.add(fill);
    const rim = new THREE.DirectionalLight(0xfff1c4, mode === 'grazing' ? 0.28 : 0.85);
    rim.position.set(0.5, 4.5, -6.0);
    lights.add(rim);
    lights.userData.reviewMode = mode;
    lights.userData.lightingFromPhoto = [{ "role": "key light", "type": "directional", "direction": "front-left-high", "intensity": 2.2, "note": "Soft studio key; produces vertical highlight bands on cap and body edges" }, { "role": "fill light", "type": "hemisphere", "intensity": 0.5, "note": "Low fill keeps black lacquer near rgb 3 except highlights" }, { "role": "rim or environment light", "type": "environment", "note": "RoomEnvironment PMREM for gloss reflections on lacquer and cap" }, { "role": "exposure and tone mapping", "toneMapping": "ACESFilmic", "exposure": 1.0 }, { "role": "background and contact shadow", "background": "transparent over page void #000000", "contactShadow": "soft ground shadow under base, ambient occlusion at cap/collar join" }];
    lights.userData.lookDevTargets = { "qualityPriority": "reference-fidelity", "materialPass": { "albedoPaletteRequired": true, "roughnessVariationRequired": true, "normalOrBumpRequired": true, "localOverridesRequired": true, "minimumTextureResolution": 1024, "preferredTextureResolution": 2048, "independentMapChannels": ["albedo", "roughness", "height", "normal", "ambient-occlusion"], "requiredSurfaceFrequencyBands": ["macro", "meso", "micro"], "geometryReliefRequiredWhenSilhouetteAffected": true, "referencePbrExtraction": { "requiredWhenSourceImagePresent": true, "targetThreshold": 0.7, "stopOnLowConfidence": true, "script": "forge/stage1_intake/extract_pbr_evidence.py", "acceptedLimitation": "single-image extraction is reference-derived inference, not exact photogrammetry" }, "mustAvoid": ["single flat albedo per material", "uniform roughness", "albedo texture reused as roughness/height/normal/AO", "single-frequency random noise", "plastic-looking smooth bark, stone, cloth, foliage, or aged material", "local color/detail described only in prose without material masks", "claiming exact PBR recovery when confidence is below the target threshold"] }, "lightingPass": { "requiredTerms": ["key light", "fill light", "rim or environment light", "exposure", "tone mapping", "background", "contact shadow"], "mustAvoid": ["ambient-only lighting", "flat value range", "missing contact shadow", "reference lighting copied without separating material readability"] }, "screenshotReview": ["Compare albedo palette and local color zones.", "Compare roughness/normal/bump response under light.", "Compare cavity dirt, edge wear, stains, moss, scratches, or other local masks.", "Compare key/fill/rim structure, exposure, tone mapping, background, and contact shadows.", "Capture a neutral-light render to verify material readability without reference lighting.", "Capture a grazing-light close-up to expose flat normals, uniform roughness, tiling, and plastic highlights.", "Capture a reference-matched render from the same camera framing as the source."] };
    return lights;
}
// PBR materials (clearcoat/iridescence/transmission/anisotropy) need an environment
// map to visually behave as intended — call this once per renderer and assign the
// result to scene.environment before rendering. No external HDR asset required.
export function createFragranceFlaconTwoZoneEnvironment(renderer) {
    const pmrem = new THREE.PMREMGenerator(renderer);
    const texture = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    return texture;
}
// Plan 1.3 §3.2 — auto-framing by bounding box. The Divine Eye can only compare a
// render to the reference if the object is FRAMED consistently (an object framed
// differently scores as wrong even when its shape is right). This positions the camera
// deterministically from the object's bounding box so it fills the frame at a stable
// margin, and sets near/far to the object scale. Call after adding the model to the
// scene, and again on resize (after updating camera.aspect).
export function frameFragranceFlaconTwoZoneCamera(camera, object, options = {}) {
    const box = new THREE.Box3().setFromObject(object);
    if (box.isEmpty())
        return;
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const margin = options.margin ?? 1.15;
    const maxDim = Math.max(size.x, size.y, size.z) * margin;
    const fov = (camera.fov * Math.PI) / 180;
    // distance so the largest object dimension fits vertically in the frame
    const distance = (maxDim / 2) / Math.tan(fov / 2);
    const az = ((options.azimuthDeg ?? 0) * Math.PI) / 180;
    const el = ((options.elevationDeg ?? 0) * Math.PI) / 180;
    const dir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el));
    camera.position.copy(center).addScaledVector(dir, distance);
    camera.near = Math.max(0.01, distance - maxDim);
    camera.far = distance + maxDim * 2;
    camera.lookAt(center);
    camera.updateProjectionMatrix();
}
// Plan 1.3 §3.2c — PRESENTATION composer (DOF + bloom). CRITICAL (R-POSTFX): this is
// for the showcase/hero render ONLY. The Divine Eye's EVALUATION render MUST use a
// plain renderer with NO composer — bloom blows highlights and DOF blurs edges, which
// would corrupt the deterministic IoU/DCD/edge/blowout signals. Enable dof/bloom ONLY
// when the reference photo actually exhibits them (detect_reference_effects.py authorizes).
export function createFragranceFlaconTwoZonePresentationComposer(renderer, scene, camera, options = {}) {
    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    if (options.dof) {
        composer.addPass(new BokehPass(scene, camera, {
            focus: options.dofFocus ?? 10.0,
            aperture: options.dofAperture ?? 0.0002,
            maxblur: 0.01,
        }));
    }
    if (options.bloom) {
        const size = new THREE.Vector2();
        renderer.getSize(size);
        composer.addPass(new UnrealBloomPass(size, options.bloomStrength ?? 0.4, 0.4, 0.85));
    }
    return composer;
}
export function configureFragranceFlaconTwoZoneRenderer(renderer) {
    // Load-bearing for view-dependent finishes (anodized / Doppler): without ACES + sRGB
    // the environment reflection reads flat/washed instead of a believable metal response.
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
}
export function createFragranceFlaconTwoZoneInspectControls(camera, domElement) {
    // View-dependent finishes only read correctly once the user orbits — their color
    // comes from the environment reflection, not albedo, so free rotation matters here.
    const controls = new OrbitControls(camera, domElement);
    controls.enableDamping = true;
    controls.minDistance = 1.0;
    controls.maxDistance = 8.0;
    controls.autoRotate = false;
    return controls;
}
// ---------------------------------------------------------------------------------------------
// Hand refinement (refine-code, material-pass, user review 2026-10-13). Recorded in the spec as
// `handRefinement`; regenerate-safe because it runs after the generated factory.
//  - body: ONE bevelled extrusion (rounded front/back edges, rounder fillets) instead of two
//    sharp-edged extrusions; the green/black split is a local-space discard in the shader so the
//    seam stays exact while the model turns.
//  - glass: transmissive shell (ior 1.5) around an opaque liquid volume, faint mould-ripple normal.
//  - lacquer: matte black with a fine grain bump. Cap: rounded box, gloss black.
//  - lighting: studio softbox environment for the vertical highlight bands seen on the reference.
// ---------------------------------------------------------------------------------------------
const FLACON = { H: 1.62, D: 0.45, SPLIT: 1.075, HB: 0.487, HT: 0.5, RT: 0.1, RB: 0.14, BEVEL: 0.085 };
function flaconShape(inset, y0, y1) {
    const { H, HB, HT, RT, RB } = FLACON;
    const hw = (y) => HB + (HT - HB) * (y / H) - inset;
    const rt = Math.max(0.01, RT - inset * 0.5), rb = Math.max(0.01, RB - inset * 0.5);
    const s = new THREE.Shape();
    s.moveTo(-hw(y0) + rb, y0);
    s.lineTo(hw(y0) - rb, y0);
    s.quadraticCurveTo(hw(y0), y0, hw(y0 + rb), y0 + rb);
    s.lineTo(hw(y1 - rt), y1 - rt);
    s.quadraticCurveTo(hw(y1), y1, hw(y1) - rt, y1);
    s.lineTo(-hw(y1) + rt, y1);
    s.quadraticCurveTo(-hw(y1), y1, -hw(y1 - rt), y1 - rt);
    s.lineTo(-hw(y0 + rb), y0 + rb);
    s.quadraticCurveTo(-hw(y0), y0, -hw(y0) + rb, y0);
    return s;
}
function bevelledBody(inset, y0, y1, depth) {
    const b = Math.min(FLACON.BEVEL, depth / 2 - 0.01);
    const g = new THREE.ExtrudeGeometry(flaconShape(inset + b, y0 + b, y1 - b), {
        depth: depth - 2 * b, bevelEnabled: true, bevelThickness: b, bevelSize: b,
        bevelSegments: 12, curveSegments: 48, steps: 1,
    });
    g.translate(0, 0, (FLACON.D - depth) / 2 + b); // spans [(D-depth)/2, (D+depth)/2] like the original extrusion
    g.computeVertexNormals();
    return g;
}
// Keep fragments above (keep=1) or below (keep=-1) the split, in the mesh's local space.
function clipAtSplit(material, keep) {
    material.onBeforeCompile = (shader) => {
        shader.vertexShader = shader.vertexShader
            .replace('#include <common>', '#include <common>\nvarying float vLocalY;')
            .replace('#include <begin_vertex>', '#include <begin_vertex>\nvLocalY = position.y;');
        shader.fragmentShader = shader.fragmentShader
            .replace('#include <common>', '#include <common>\nvarying float vLocalY;')
            .replace('void main() {', `void main() {\n  if (${keep === 1 ? 'vLocalY < ' : 'vLocalY > '}${FLACON.SPLIT.toFixed(4)}) discard;`);
    };
    material.customProgramCacheKey = () => `clip${keep}`;
}
function noiseCanvas(size, seed, draw) {
    const c = document.createElement('canvas');
    c.width = c.height = size;
    let a = seed;
    const rnd = () => { a = (a * 1664525 + 1013904223) >>> 0; return a / 4294967296; };
    draw(c.getContext('2d'), rnd);
    return c;
}
// Fine grain for the matte lacquer (bump map, deterministic seed).
function lacquerGrain() {
    const c = noiseCanvas(512, 7, (g, rnd) => {
        const img = g.createImageData(512, 512);
        for (let i = 0; i < img.data.length; i += 4) {
            const v = 118 + rnd() * 20;
            img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
            img.data[i + 3] = 255;
        }
        g.putImageData(img, 0, 0);
    });
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(3, 3);
    return t;
}
// Faint horizontal mould ripple for the glass (tangent-space normal map, deterministic).
function glassRipple() {
    const c = noiseCanvas(256, 11, (g, rnd) => {
        const img = g.createImageData(256, 256);
        const phase = Array.from({ length: 6 }, () => rnd() * Math.PI * 2);
        for (let y = 0; y < 256; y++) {
            let dy = 0;
            for (let k = 0; k < 6; k++)
                dy += Math.cos((y / 256) * Math.PI * 2 * (k + 2) + phase[k]) / (k + 2);
            const ny = 128 + dy * 22;
            for (let x = 0; x < 256; x++) {
                const i = (y * 256 + x) * 4;
                img.data[i] = 128 + (rnd() - 0.5) * 6;
                img.data[i + 1] = ny;
                img.data[i + 2] = 255;
                img.data[i + 3] = 255;
            }
        }
        g.putImageData(img, 0, 0);
    });
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(1.5, 1.5);
    return t;
}
export function refineFragranceFlaconTwoZoneModel(root) {
    const rt = root.userData.sculptRuntime;
    const parent = rt.nodes['body-lower'];
    const oldLower = rt.meshes['body-lower'], oldUpper = rt.meshes['body-upper'];
    if (oldLower)
        oldLower.visible = false;
    if (oldUpper)
        oldUpper.visible = false;
    const { H, D, SPLIT } = FLACON;
    const lacquer = new THREE.MeshPhysicalMaterial({
        color: 0x050505, roughness: 0.58, metalness: 0, bumpMap: lacquerGrain(), bumpScale: 0.6,
        sheen: 1, sheenRoughness: 0.4, sheenColor: new THREE.Color(0x707070),
        envMapIntensity: 0.95, side: THREE.DoubleSide,
    });
    clipAtSplit(lacquer, -1);
    const glass = new THREE.MeshPhysicalMaterial({
        color: 0xf2fff9, metalness: 0, roughness: 0.035, transmission: 1, thickness: 0.09, ior: 1.5,
        attenuationColor: new THREE.Color(0x46c9a0), attenuationDistance: 0.45,
        clearcoat: 1, clearcoatRoughness: 0.02, specularIntensity: 1, envMapIntensity: 1.15,
        normalMap: glassRipple(), normalScale: new THREE.Vector2(0.06, 0.06),
    });
    clipAtSplit(glass, 1);
    const liquidGeom = bevelledBody(0.045, 0.02, H - 0.05, D - 0.09);
    // Liquid gets lighter toward the bottom of the green zone (reference stops #01694F -> #01775C).
    const pos = liquidGeom.getAttribute('position');
    const col = new Float32Array(pos.count * 3), top = new THREE.Color(0x035e46), low = new THREE.Color(0x0c9e72), tmp = new THREE.Color();
    for (let i = 0; i < pos.count; i++) {
        const t = THREE.MathUtils.clamp((pos.getY(i) - SPLIT) / (H - SPLIT), 0, 1);
        tmp.copy(low).lerp(top, t);
        col.set([tmp.r, tmp.g, tmp.b], i * 3);
    }
    liquidGeom.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const liquid = new THREE.MeshPhysicalMaterial({ vertexColors: true, roughness: 0.3, metalness: 0, emissive: 0x03543c, emissiveIntensity: 0.45, envMapIntensity: 0.4 });
    clipAtSplit(liquid, 1);
    const shell = bevelledBody(0, 0, H, D);
    const add = (name, geom, mat) => {
        const m = new THREE.Mesh(geom, mat);
        m.name = name;
        m.castShadow = true;
        m.receiveShadow = true;
        parent.add(m);
        return m;
    };
    rt.meshes['body-lower'] = add('Body lower (black lacquer)', shell, lacquer);
    rt.meshes['body-upper'] = add('Body upper (green glass)', shell, glass);
    rt.meshes['liquid'] = add('Liquid', liquidGeom, liquid);
    rt.meshes['body-upper'].renderOrder = 2;
    if (oldLower)
        oldLower.name = 'Body lower (generated, hidden)';
    if (oldUpper)
        oldUpper.name = 'Body upper (generated, hidden)';
    const capBlack = new THREE.MeshPhysicalMaterial({ color: 0x050505, roughness: 0.18, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.06, envMapIntensity: 1.1 });
    const cap = rt.meshes['overcap'];
    if (cap) {
        cap.geometry.dispose();
        cap.geometry = new RoundedBoxGeometry(0.35, 0.27, 0.3, 8, 0.045);
        cap.material = capBlack;
    }
    const collar = rt.meshes['collar'];
    if (collar)
        collar.material = capBlack;
    const ring = rt.meshes['emblem-ring'];
    if (ring)
        ring.material = new THREE.MeshPhysicalMaterial({ color: 0x060606, roughness: 0.22, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.08, envMapIntensity: 1.2 });
}
// Studio environment: a dark room with two tall softboxes left/right and one overhead strip, so
// rounded edges pick up the vertical highlight bands the reference photo shows.
export function createFragranceFlaconStudioEnvironment(renderer) {
    const room = new THREE.Scene();
    room.background = new THREE.Color(0x020202);
    const panel = (w, h, intensity, pos, rotY, rotX = 0) => {
        const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(intensity, intensity, intensity), side: THREE.DoubleSide }));
        m.position.set(...pos);
        m.rotation.set(rotX, rotY, 0);
        room.add(m);
    };
    panel(0.8, 6, 3.2, [-4, 0.5, 1.5], Math.PI / 2.4);
    panel(0.8, 6, 2.4, [4, 0.5, 1.5], -Math.PI / 2.4);
    panel(5, 1.0, 2.2, [0, 4, 0], 0, Math.PI / 2);
    panel(2.5, 2.5, 0.5, [0, 0.6, 5], 0);
    panel(0.6, 5, 1.6, [-1.2, 0.5, -4.5], 0);
    const pmrem = new THREE.PMREMGenerator(renderer);
    const tex = pmrem.fromScene(room, 0.02).texture;
    pmrem.dispose();
    return tex;
}
// Two side-rear rim lights: on a matte black body the silhouette only reads where a grazing
// light catches the rounded edges (sheen); without them the lacquer merges with a black page.
export function createFragranceFlaconRimLights() {
    const g = new THREE.Group();
    g.name = 'Flacon rim lights';
    const left = new THREE.DirectionalLight(0xdfe8ff, 3.2);
    left.position.set(-5, 2.5, -3.5);
    const right = new THREE.DirectionalLight(0xfff1dc, 2.0);
    right.position.set(5, 1.5, -3);
    g.add(left, right);
    return g;
}
