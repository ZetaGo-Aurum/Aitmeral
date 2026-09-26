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
    const result = execSync(`${pythonCmd} -m aureus --help`, { 
      encoding: 'utf8', 
      stdio: ['ignore', 'pipe', 'ignore'] 
    });
    if (result.includes('AUREUS')) return true;
  } catch {}
  return false;
}

function installAureus(pythonCmd) {
  console.log('📦 Installing AUREUS via pip...');
  const pipCmd = `${pythonCmd} -m pip install aureus`;
  const child = spawn(pipCmd, { shell: true, stdio: 'inherit' });
  
  return new Promise((resolve, reject) => {
    child.on('close', (code) => {
      if (code === 0) {
        console.log('✅ AUREUS installed successfully!');
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
    console.log('aureus (npm wrapper) v1.0.0');
    console.log('Python package: aureus@1.0.0');
    return;
  }
  
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
AUREUS — Video Enhancer, Upscaler & RAW Lossless Converter
npm wrapper for the Python package

Usage:
  aureus [command] [options]

Commands:
  aureus              Open TUI interface
  aureus tui          Open TUI interface
  aureus server       Start Web UI server
  aureus convert      Convert video file
  aureus url          Process video from URL
  aureus info         Show media info
  aureus doctor       Check system requirements
  aureus presets      List output presets
  aureus effects      List effects & shaders
  aureus --version    Show version

Installation:
  npm install -g aureus-enhancer     # Global install (this wrapper)
  pip install aureus        # Direct Python install
  bash <(curl -fsSL https://raw.githubusercontent.com/zetagoaurum/Aureus/main/install.sh)

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
    console.log('🔍 AUREUS not found, installing...');
    try {
      await installAureus(pythonCmd);
    } catch (err) {
      console.error('❌ Failed to install AUREUS:', err.message);
      console.error('   Try manually: pip install aureus');
      process.exit(1);
    }
  }

  const child = spawn(pythonCmd, ['-m', 'aureus', ...args], { 
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