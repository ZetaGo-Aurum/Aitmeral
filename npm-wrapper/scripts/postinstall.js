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

console.log('📦 AITMERAL npm wrapper postinstall');

const pythonCmd = findPython();
if (!pythonCmd) {
  console.log('⚠️  Python 3 not found. AITMERAL will be installed on first run.');
  console.log('   Install Python 3.9+ first, then run: aitmeral');
  process.exit(0);
}

console.log(`🐍 Found Python: ${pythonCmd}`);

try {
  execSync(`${pythonCmd} -m pip install aitmeral`, { stdio: 'inherit' });
  console.log('✅ AITMERAL installed successfully!');
} catch (err) {
  console.log('⚠️  Auto-install skipped. Run "aitmeral" to install on first use.');
  console.log('   Or manually: pip install aitmeral');
}

console.log('');
console.log('🚀 Ready! Run "aitmeral" to start.');