#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(here, '..');
const templateRoot = path.join(skillRoot, 'assets', 'remotion-template');
const statusOrder = [
  'initialized', 'evidence_ready', 'content_approved', 'visual_direction_approved',
  'assets_ready', 'voice_locked', 'timeline_locked', 'preview_approved',
  'rendered', 'qa_passed', 'delivered',
];

const usage = () => {
  console.error('Usage: node build.mjs --validate manifest.json');
  console.error('   or: node build.mjs [--preview] manifest.json output-dir');
};

const readManifest = (manifestPath) => JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const rank = (status) => statusOrder.indexOf(status);

const validateForBuild = (manifest, preview) => {
  const errors = [];
  if (manifest.schemaVersion !== '1.0') errors.push("schemaVersion must be '1.0'");
  if (!manifest.projectId) errors.push('projectId is required');
  if (rank(manifest.status) < rank('visual_direction_approved')) {
    errors.push('build requires visual_direction_approved or later');
  }
  if (!Array.isArray(manifest.scenes) || manifest.scenes.length === 0) errors.push('scenes are required');
  if (manifest.approvals?.content?.status !== 'approved') errors.push('content approval is missing');
  if (manifest.approvals?.visualDirection?.status !== 'approved') errors.push('visual direction approval is missing');
  if (!preview) {
    if (rank(manifest.status) < rank('timeline_locked')) errors.push('final build requires timeline_locked or later');
    if (!manifest.voiceover?.locked || !manifest.voiceover?.path) errors.push('final build requires locked manual voiceover');
  }
  return errors;
};

const copySelectedAssets = (manifest, manifestDir, outputDir) => {
  const mediaDir = path.join(outputDir, 'public', 'media');
  fs.mkdirSync(mediaDir, {recursive: true});
  manifest.assets = (manifest.assets ?? []).map((asset) => {
    if (!asset.selected || !asset.path) return asset;
    const source = path.isAbsolute(asset.path) ? asset.path : path.resolve(manifestDir, asset.path);
    if (!fs.existsSync(source)) throw new Error(`Selected asset does not exist: ${source}`);
    const safeId = String(asset.assetId).replace(/[^a-zA-Z0-9_-]/g, '-');
    const targetName = `${safeId}${path.extname(source).toLowerCase()}`;
    fs.copyFileSync(source, path.join(mediaDir, targetName));
    return {...asset, publicPath: `media/${targetName}`};
  });
};

const copyVoiceover = (manifest, manifestDir, outputDir, preview) => {
  manifest.voiceover ??= {};
  if (!manifest.voiceover?.path) {
    manifest.voiceover.publicPath = null;
    if (!preview) throw new Error('Voiceover is required for a final build');
    return;
  }
  const source = path.isAbsolute(manifest.voiceover.path)
    ? manifest.voiceover.path
    : path.resolve(manifestDir, manifest.voiceover.path);
  if (!fs.existsSync(source)) throw new Error(`Voiceover does not exist: ${source}`);
  const audioDir = path.join(outputDir, 'public', 'audio');
  fs.mkdirSync(audioDir, {recursive: true});
  const targetName = `voiceover${path.extname(source).toLowerCase()}`;
  fs.copyFileSync(source, path.join(audioDir, targetName));
  manifest.voiceover.publicPath = `audio/${targetName}`;
};

const args = process.argv.slice(2);
const preview = args.includes('--preview');
const positional = args.filter((arg) => arg !== '--preview');
const unknownFlags = positional.filter((arg) => arg.startsWith('--') && arg !== '--validate');
if (unknownFlags.length > 0) {
  console.error(`Unknown option: ${unknownFlags.join(', ')}`);
  usage();
  process.exit(2);
}

if (positional.length < 2 && positional[0] !== '--validate') {
  usage();
  process.exit(2);
}

if (positional[0] === '--validate') {
  if (!positional[1] || positional.length !== 2 || preview) {
    usage();
    process.exit(2);
  }
  const manifest = readManifest(path.resolve(positional[1]));
  const validateAsPreview = !manifest.voiceover?.locked;
  const errors = validateForBuild(manifest, validateAsPreview);
  console.log(JSON.stringify({status: errors.length ? 'error' : 'ok', errors}, null, 2));
  process.exit(errors.length ? 1 : 0);
}

if (positional.length !== 2) {
  usage();
  process.exit(2);
}

const manifestPath = path.resolve(positional[0]);
const outputDir = path.resolve(positional[1]);
const manifest = readManifest(manifestPath);
const errors = validateForBuild(manifest, preview);
if (errors.length) {
  console.error(JSON.stringify({status: 'error', errors}, null, 2));
  process.exit(1);
}
if (fs.existsSync(outputDir)) throw new Error(`Output directory already exists: ${outputDir}`);

fs.cpSync(templateRoot, outputDir, {recursive: true});
copySelectedAssets(manifest, path.dirname(manifestPath), outputDir);
copyVoiceover(manifest, path.dirname(manifestPath), outputDir, preview);

const generated = `import type {ProjectManifest} from './types';\n\nexport const project = ${JSON.stringify(manifest, null, 2)} as ProjectManifest;\n`;
fs.writeFileSync(path.join(outputDir, 'src', 'project.generated.ts'), generated, 'utf8');
fs.writeFileSync(path.join(outputDir, 'project-manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({status: 'ok', mode: preview ? 'preview' : 'final', outputDir}, null, 2));
