#!/usr/bin/env node
/*
 * Regenerates AIDMWallpaper/manifest.json - the single index the app reads
 * to discover content (see the app's core/content/repo_catalog.dart). The
 * app lists ONLY the files named here, so this must be regenerated whenever
 * files are added/removed under AIDMWallpaper/.
 *
 * Zero dependencies - runs on any Node 16+ with nothing installed. Run from
 * the repository root:
 *     node scripts/generate-manifest.js
 *
 * Output shape (unchanged from the existing manifest):
 *     { "generatedAt": ISO8601, "count": N, "files": ["AIDMWallpaper/...", ...] }
 * Every path is repo-root-relative with forward slashes and the
 * "AIDMWallpaper/" prefix, sorted, excluding the manifest itself and
 * dotfiles.
 */
'use strict';

const fs = require('fs');
const path = require('path');

// Content root, relative to the repo root (where this script is run from).
const ROOT = 'AIDMWallpaper';
const MANIFEST_PATH = path.join(ROOT, 'manifest.json');
const MANIFEST_REL = toPosix(MANIFEST_PATH);

function toPosix(p) {
  return p.split(path.sep).join('/');
}

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    // Skip hidden files/folders (.git, .DS_Store, etc.).
    if (entry.name.startsWith('.')) continue;

    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walk(full));
    } else if (entry.isFile()) {
      out.push(full);
    }
  }
  return out;
}

function main() {
  if (!fs.existsSync(ROOT) || !fs.statSync(ROOT).isDirectory()) {
    console.error(
      `Error: "${ROOT}/" not found. Run this from the repository root.`
    );
    process.exit(1);
  }

  const files = walk(ROOT)
    .map(toPosix)
    .filter((p) => p !== MANIFEST_REL)
    .sort((a, b) => a.localeCompare(b));

  const manifest = {
    generatedAt: new Date().toISOString(),
    count: files.length,
    files,
  };

  // 1-space indent to match the existing manifest and keep diffs minimal.
  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 1) + '\n');
  console.log(`Wrote ${MANIFEST_REL} with ${files.length} files.`);
}

main();
