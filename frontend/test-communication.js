#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

function fail(message) {
  console.error(`[test:communication] FAIL: ${message}`);
  process.exitCode = 1;
}

function ok(message) {
  console.log(`[test:communication] OK: ${message}`);
}

function readFile(relPath) {
  const abs = path.join(__dirname, relPath);
  if (!fs.existsSync(abs)) {
    fail(`Missing file: ${relPath}`);
    return '';
  }
  return fs.readFileSync(abs, 'utf8');
}

function assertContains(relPath, snippet, label) {
  const txt = readFile(relPath);
  if (!txt) return;
  if (!txt.includes(snippet)) {
    fail(`${label} not found in ${relPath}`);
    return;
  }
  ok(`${label} present`);
}

function assertNotContains(relPath, snippet, label) {
  const txt = readFile(relPath);
  if (!txt) return;
  if (txt.includes(snippet)) {
    fail(`${label} unexpectedly found in ${relPath}`);
    return;
  }
  ok(`${label} absent`);
}

assertContains('src/features/astroclock/api.mjs', '/api/astro-clock/stream-ticket', 'stream ticket endpoint usage');
assertContains('src/features/astroclock/api.mjs', "return 'http://127.0.0.1:52525';", 'default API port fallback');
assertContains('main.js', "process.env.API_BASE_URL = API_BASE_URL;", 'electron dev API base alignment');
assertNotContains('main.js', 'http://localhost:5000', 'legacy dev backend port');

if (process.exitCode) {
  process.exit(process.exitCode);
}
ok('communication smoke checks passed');
