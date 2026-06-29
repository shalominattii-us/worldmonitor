#!/usr/bin/env node
import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';

function run(cmd, cwd) {
  console.log(`\n==> [${cwd}] $ ${cmd}`);
  const r = spawnSync(cmd, { shell: true, stdio: 'inherit', cwd });
  if (r.error) {
    console.error(r.error);
    return r.status || 1;
  }
  return r.status ?? 0;
}

function loadPackageScripts(cwd) {
  try {
    const pj = JSON.parse(fs.readFileSync(path.join(cwd, 'package.json'), 'utf8'));
    return pj.scripts || {};
  } catch (e) {
    return {};
  }
}

const argv = process.argv.slice(2).filter(a => !a.startsWith('--cwd='));
const cwdArgs = process.argv.slice(2).find(a => a.startsWith('--cwd='));
const targets = (cwdArgs ? [cwdArgs.split('=')[1]] : (argv.length ? argv : ['.']));
const useFull = process.argv.includes('--full') || process.env.DIAGNOSTICS_FULL === '1';

const baseCommands = [
  useFull ? 'npm ci' : 'npm ci --ignore-scripts --no-optional',
  'npm run typecheck',
  'npm run typecheck:api',
  'npm run test:convex',
  'npm run test:data',
  'npm run test:sidecar'
];

const summary = [];
for (const t of targets) {
  const targetPath = path.resolve(process.cwd(), t);
  if (!fs.existsSync(targetPath)) {
    console.warn(`Path not found: ${targetPath} — skipping`);
    summary.push({ target: t, ok: false, reason: 'missing' });
    continue;
  }

  const scripts = loadPackageScripts(targetPath);
  const cmds = baseCommands.filter(c => {
    if (!c.startsWith('npm run ')) return true;
    const name = c.replace('npm run ', '').split(' ')[0];
    return Object.prototype.hasOwnProperty.call(scripts, name);
  });

  console.log(`\nRunning diagnostics for ${targetPath}`);
  let ok = true;
  for (const cmd of cmds) {
    const code = run(cmd, targetPath);
    if (code !== 0) {
      console.error(`Command failed with exit ${code}: ${cmd}`);
      summary.push({ target: t, ok: false, failed: cmd, code });
      ok = false;
      break;
    }
  }
  if (ok) summary.push({ target: t, ok: true });
}

console.log('\nDiagnostics summary:');
for (const s of summary) {
  if (s.ok) console.log(`- ${s.target}: OK`);
  else console.log(`- ${s.target}: FAILED (${s.reason || s.failed})`);
}

const failed = summary.some(s => !s.ok);
process.exit(failed ? 2 : 0);
