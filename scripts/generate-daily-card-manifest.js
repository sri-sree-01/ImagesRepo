#!/usr/bin/env node
/*
 * Regenerates ttd_info/daily_card/manifest.json — the plate list the TTD Info
 * app's "Today's Srivari Card" reads (lib/daily_card/daily_card_service.dart).
 *
 * Drop a .jpg/.jpeg/.png/.webp into ttd_info/daily_card/ and push: this adds
 * it to the rotation. Nothing else to edit.
 *   • layout is detected from the image size: portrait (taller than ~1.4×
 *     wide) → "full" (drawn edge to edge); anything squarer → "square"
 *     (framed in the middle of the card);
 *   • label comes from the file name ("govinda_namalu.jpg" → "Govinda Namalu");
 *   • entries already in the manifest keep their hand-written label/layout
 *     and their order; new files are appended; deleted files are dropped;
 *   • the "vahanams" map (ttd_info/daily_card/vahanams/, used for the
 *     automatic Brahmotsavam cards) is rebuilt from that folder, keyed by the
 *     file name without extension (must match brahmotsavam_sevas.image_key).
 *
 * Keep images ~1080px and under ~300 KB (JPEG q75) — phones download each
 * one once and then cache it.
 *
 * Zero dependencies. Run from the repository root:
 *     node scripts/generate-daily-card-manifest.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join('ttd_info', 'daily_card');
const VAHANAMS = path.join(ROOT, 'vahanams');
const MANIFEST = path.join(ROOT, 'manifest.json');
const IMG = /\.(jpe?g|png|webp)$/i;

/** Width/height from a PNG/JPEG/WebP header, or null. */
function imageSize(file) {
  const b = fs.readFileSync(file);
  // PNG: IHDR at byte 16.
  if (b.length > 24 && b.readUInt32BE(0) === 0x89504e47) {
    return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  }
  // JPEG: walk segments to the first SOFn marker.
  if (b.length > 4 && b[0] === 0xff && b[1] === 0xd8) {
    let i = 2;
    while (i + 9 < b.length) {
      if (b[i] !== 0xff) { i++; continue; }
      const marker = b[i + 1];
      const len = b.readUInt16BE(i + 2);
      if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
        return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7) };
      }
      i += 2 + len;
    }
  }
  // WebP (VP8X / VP8 / VP8L).
  if (b.length > 30 && b.toString('ascii', 0, 4) === 'RIFF' && b.toString('ascii', 8, 12) === 'WEBP') {
    const chunk = b.toString('ascii', 12, 16);
    if (chunk === 'VP8X') return { w: 1 + b.readUIntLE(24, 3), h: 1 + b.readUIntLE(27, 3) };
    if (chunk === 'VP8 ') return { w: b.readUInt16LE(26) & 0x3fff, h: b.readUInt16LE(28) & 0x3fff };
    if (chunk === 'VP8L') {
      const v = b.readUInt32LE(21);
      return { w: (v & 0x3fff) + 1, h: ((v >> 14) & 0x3fff) + 1 };
    }
  }
  return null;
}

function labelFrom(file) {
  return path.basename(file, path.extname(file))
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

function listImages(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((f) => IMG.test(f) && !f.startsWith('.'))
    .filter((f) => fs.statSync(path.join(dir, f)).isFile())
    .sort();
}

let old = { arts: [] };
if (fs.existsSync(MANIFEST)) {
  try { old = JSON.parse(fs.readFileSync(MANIFEST, 'utf8')); } catch (_) {}
}
const present = new Set(listImages(ROOT));

// Keep existing entries (and their order/labels) for files still present.
const arts = (old.arts || []).filter((a) => present.has(a.file));
const known = new Set(arts.map((a) => a.file));
for (const f of present) {
  if (known.has(f)) continue;
  const size = imageSize(path.join(ROOT, f));
  const layout = size && size.h > size.w * 1.4 ? 'full' : 'square';
  arts.push({ file: f, layout, label: labelFrom(f) });
}

const vahanams = {};
for (const f of listImages(VAHANAMS)) {
  vahanams[path.basename(f, path.extname(f)).toLowerCase()] = `vahanams/${f}`;
}

const next = {
  version: 2,
  updated: new Date().toISOString().slice(0, 10),
  arts,
  vahanams,
};

// Only rewrite (and bump "updated") when the content actually changed.
const strip = (m) => JSON.stringify({ arts: m.arts || [], vahanams: m.vahanams || {} });
if (strip(old) === strip(next)) {
  console.log(`Manifest unchanged (${arts.length} plates, ${Object.keys(vahanams).length} vahanams).`);
} else {
  fs.writeFileSync(MANIFEST, JSON.stringify(next, null, 2) + '\n');
  console.log(`Wrote ${MANIFEST}: ${arts.length} plates, ${Object.keys(vahanams).length} vahanams.`);
}
