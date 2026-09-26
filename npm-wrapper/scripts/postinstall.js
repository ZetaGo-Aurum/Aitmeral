#!/usr/bin/env node
'use strict';

import { execSync } from 'child_process';

function findPython() {
  const candidates = ['python3', 'python', 'py'];
  for (const cmd of candidates) {
    try {
      execSync(`${cmd} --version`, { stdio: 'ignore' });
      return cmd;
    } catch {}
  }
  return null;
}

console.log('📦 AUREUS npm wrapper postinstall');

const pythonCmd = findPython();
if (!pythonCmd) {
  console.log('⚠️  Python 3 not found. AUREUS will be installed on first run.');
  console.log('   Install Python 3.9+ first, then run: aureus');
  process.exit(0);
}

console.log(`🐍 Found Python: ${pythonCmd}`);

try {
  execSync(`${pythonCmd} -m pip install aureus`, { stdio: 'inherit' });
  console.log('✅ AUREUS installed successfully!');
} catch (err) {
  console.log('⚠️  Auto-install skipped. Run "aureus" to install on first use.');
  console.log('   Or manually: pip install aureus');
}

console.log('');
console.log('🚀 Ready! Run "aureus" to start.');