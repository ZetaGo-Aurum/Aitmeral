#!/usr/bin/env node
'use strict';

import { execSync } from 'child_process';

console.log('🧪 Testing AITMERAL npm wrapper...\n');

const pythonCmd = ['python3', 'python', 'py'].find(cmd => {
  try { execSync(`${cmd} --version`, { stdio: 'ignore' }); return true; } catch { return false; }
});

if (!pythonCmd) {
  console.log('❌ No Python found');
  process.exit(1);
}
console.log(`✅ Python: ${pythonCmd}`);

try {
  execSync(`${pythonCmd} -m aitmeral --version`, { stdio: 'pipe' });
  console.log('✅ AITMERAL Python package installed');
} catch {
  console.log('⚠️  AITMERAL not installed (will install on first run)');
}

console.log('\n✅ Wrapper test passed');