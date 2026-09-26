#!/usr/bin/env node
'use strict';

import { spawn, execSync } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

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

function findAureus(pythonCmd) {
  try {
    const result = execSync(`${pythonCmd} -m aitmeral --help`, { 
      encoding: 'utf8', 
      stdio: ['ignore', 'pipe', 'ignore'] 
    });
    if (result.includes('AITMERAL')) return true;
  } catch {}
  return false;
}

function installAureus(pythonCmd) {
  console.log('📦 Installing AITMERAL via pip...');
  const pipCmd = `${pythonCmd} -m pip install aitmeral`;
  const child = spawn(pipCmd, { shell: true, stdio: 'inherit' });
  
  return new Promise((resolve, reject) => {
    child.on('close', (code) => {
      if (code === 0) {
        console.log('✅ AITMERAL installed successfully!');
        resolve();
      } else {
        reject(new Error(`pip install failed with code ${code}`));
      }
    });
  });
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--version') || args.includes('-V')) {
    console.log('aitmeral (npm wrapper) v1.0.0');
    console.log('Python package: aitmeral@1.0.0');
    return;
  }
  
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
AITMERAL — Video Enhancer, Upscaler & RAW Lossless Converter
npm wrapper for the Python package

Usage:
  aitmeral [command] [options]

Commands:
  aitmeral              Open TUI interface
  aitmeral tui          Open TUI interface
  aitmeral server       Start Web UI server
  aitmeral convert      Convert video file
  aitmeral url          Process video from URL
  aitmeral info         Show media info
  aitmeral doctor       Check system requirements
  aitmeral presets      List output presets
  aitmeral effects      List effects & shaders
  aitmeral --version    Show version

Installation:
  npm install -g aitmeral-enhancer     # Global install (this wrapper)
  pip install aitmeral        # Direct Python install
  bash <(curl -fsSL https://raw.githubusercontent.com/zetagoaurum/Aitmeral/main/install.sh)

The npm wrapper will auto-install the Python package on first run.
`);
    return;
  }

  const pythonCmd = findPython();
  if (!pythonCmd) {
    console.error('❌ Python 3 not found. Please install Python 3.9+');
    console.error('   Linux: sudo apt install python3 python3-pip');
    console.error('   macOS: brew install python');
    console.error('   Windows: winget install Python.Python.3.12');
    process.exit(1);
  }

  if (!findAureus(pythonCmd)) {
    console.log('🔍 AITMERAL not found, installing...');
    try {
      await installAureus(pythonCmd);
    } catch (err) {
      console.error('❌ Failed to install AITMERAL:', err.message);
      console.error('   Try manually: pip install aitmeral');
      process.exit(1);
    }
  }

  const child = spawn(pythonCmd, ['-m', 'aitmeral', ...args], { 
    stdio: 'inherit',
    shell: true 
  });
  
  child.on('close', (code) => {
    process.exit(code || 0);
  });
}

main().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});