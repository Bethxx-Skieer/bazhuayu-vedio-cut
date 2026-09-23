#!/usr/bin/env node

import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(here, '..');
const example = path.join(skillRoot, 'assets', 'project.example.json');
const template = path.join(skillRoot, 'assets', 'project-manifest.template.json');
const build = path.join(here, 'build.mjs');
const validator = path.join(here, 'validate_project.py');
const python = process.env.PYTHON || 'python';

const exec = (command, args) => {
  const result = spawnSync(command, args, {encoding: 'utf8'});
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(' ')} failed\n${result.stdout}\n${result.stderr}`);
  }
  return result;
};

const execExpectFailure = (command, args) => {
  const result = spawnSync(command, args, {encoding: 'utf8'});
  if (result.status === 0) {
    throw new Error(`${command} ${args.join(' ')} unexpectedly succeeded`);
  }
  return result;
};

exec(python, [validator, template]);
exec(python, [validator, example]);
exec(process.execPath, [build, '--validate', example]);

const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'knowledge-explainer-test-'));
const output = path.join(tempRoot, 'remotion-preview');
try {
  execExpectFailure(process.execPath, [build, example, path.join(tempRoot, 'invalid-final')]);
  exec(process.execPath, [build, '--preview', example, output]);
  assert.ok(fs.existsSync(path.join(output, 'package.json')));
  assert.ok(fs.existsSync(path.join(output, 'src', 'project.generated.ts')));
  assert.ok(fs.existsSync(path.join(output, 'project-manifest.json')));
  assert.ok(fs.existsSync(path.join(output, 'src', 'CustomScenes.tsx')));
  assert.ok(!fs.existsSync(path.join(output, 'node_modules')));
  const generated = fs.readFileSync(path.join(output, 'src', 'project.generated.ts'), 'utf8');
  assert.match(generated, /knowledge-explainer-example/);

  const enhanced = JSON.parse(fs.readFileSync(example, 'utf8'));
  enhanced.schemaVersion = '1.1';
  enhanced.status = 'timeline_locked';
  enhanced.voiceover = {mode: 'manual', path: 'voice.wav', durationSec: 28, locked: true};
  enhanced.captions = {enabled: true, sourcePath: 'captions.json', style: {fontSize: 40, bottom: 42, maxWidth: 1400, maxLines: 2}};
  enhanced.music = {enabled: true, path: 'music.wav', sourceId: 'SRC002', license: 'test-fixture', gain: 0.2, ducking: true};
  enhanced.sources.push({sourceId: 'SRC002', type: 'background-music', license: 'test-fixture'});
  enhanced.narrative.sentences.forEach((sentence, index) => {
    sentence.startSec = index * 9;
    sentence.endSec = Math.min(28, index * 9 + 8);
  });
  enhanced.scenes.forEach((scene) => {
    scene.storyAction = {
      question: '这一段解决什么问题？', concept: '一次清晰的能力变化', actorId: null,
      objectIds: [scene.visualBeats[0].beatId], action: '展示改动过程', outcome: '观众看见改动结果',
      triggerNarrationId: scene.narrationIds[0], startSec: 0.5, endSec: 7, holdSec: 1,
    };
    scene.visualBeats[0].surface = 'none';
    scene.visualBeats[0].changeRole = 'major';
  });
  fs.writeFileSync(path.join(tempRoot, 'voice.wav'), 'test fixture');
  fs.writeFileSync(path.join(tempRoot, 'music.wav'), 'test fixture');
  fs.writeFileSync(path.join(tempRoot, 'captions.json'), JSON.stringify([
    {text: '第一句', startMs: 0, endMs: 900, timestampMs: null, confidence: null},
    {text: '第二句', startMs: 1000, endMs: 1800, timestampMs: null, confidence: null},
  ]));
  const enhancedPath = path.join(tempRoot, 'enhanced.json');
  fs.writeFileSync(enhancedPath, JSON.stringify(enhanced));
  exec(python, [validator, enhancedPath]);
  exec(process.execPath, [build, '--validate', enhancedPath]);
  const finalOutput = path.join(tempRoot, 'remotion-final');
  exec(process.execPath, [build, enhancedPath, finalOutput]);
  assert.match(fs.readFileSync(path.join(finalOutput, 'captions.srt'), 'utf8'), /第一句/);
  assert.ok(fs.existsSync(path.join(finalOutput, 'public', 'audio', 'music.wav')));
  assert.match(fs.readFileSync(path.join(finalOutput, 'src', 'project.generated.ts'), 'utf8'), /"storyAction"/);

  enhanced.captions.enabled = false;
  enhanced.music.enabled = false;
  enhanced.scenes[0].storyAction.objectIds = ['missing-beat'];
  fs.writeFileSync(enhancedPath, JSON.stringify(enhanced));
  execExpectFailure(python, [validator, enhancedPath]);
  console.log(JSON.stringify({status: 'ok', tests: 19}, null, 2));
} finally {
  fs.rmSync(tempRoot, {recursive: true, force: true});
}
