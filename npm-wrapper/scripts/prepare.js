#!/usr/bin/env node
'use strict';

import { chmodSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = join(__filename, '..', '..');

try {
  chmodSync(join(__dirname, 'bin', 'aitmeral.js'), 0o755);
  chmodSync(join(__dirname, 'index.js'), 0o755);
} catch {}