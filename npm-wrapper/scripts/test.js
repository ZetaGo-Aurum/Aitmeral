#!/usr/bin/env node
'use strict';

import { execSync } from 'child_process';

console.log('🧪 Testing AUREUS npm wrapper...\n');

const pythonCmd = ['python3', 'python', 'py'].find(cmd => {
  try { execSync(`${cmd} --version`, { stdio: 'ignore' }); return true; } catch { return false; }
});

if (!pythonCmd) {
  console.log('❌ No Python found');
  process.exit(1);
}
console.log(`✅ Python: ${pythonCmd}`);

try {
  execSync(`${pythonCmd} -m aureus --version`, { stdio: 'pipe' });
  console.log('✅ AUREUS Python package installed');
} catch {
  console.log('⚠️  AUREUS not installed (will install on first run)');
}

console.log('\n✅ Wrapper test passed');