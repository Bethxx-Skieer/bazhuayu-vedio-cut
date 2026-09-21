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
  const generated = fs.readFileSync(path.join(output, 'src', 'project.generated.ts'), 'utf8');
  assert.match(generated, /knowledge-explainer-example/);
  console.log(JSON.stringify({status: 'ok', tests: 9}, null, 2));
} finally {
  fs.rmSync(tempRoot, {recursive: true, force: true});
}
