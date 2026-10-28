#!/usr/bin/env node
/**
 * Build de l'interface pour une cible donnée : l'adresse de l'API est choisie au moment du build.
 *
 *   npm run build:prod   → API de production (api-cibles.json → "production")
 *   npm run build:dev    → API de développement (adresse déjà configurée : .env.local ou variables Vercel)
 *   npm run build        → identique à build:dev (comportement historique)
 *
 * Les variables NEXT_PUBLIC_* sont figées dans le code au moment du build : changer de cible = rebuild.
 * Une variable passée par le processus l'emporte sur les fichiers .env*, donc sur .env.local.
 */
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const racine = join(dirname(fileURLToPath(import.meta.url)), '..');
const cible = process.argv[2];
const cibles = JSON.parse(readFileSync(join(racine, 'api-cibles.json'), 'utf8'));

if (!cible || !(cible in cibles) || cible.startsWith('_')) {
  const connues = Object.keys(cibles).filter((c) => !c.startsWith('_')).join(', ');
  console.error(`Cible inconnue : « ${cible ?? ''} ». Cibles possibles : ${connues}.`);
  process.exit(1);
}

const env = { ...process.env, NEXT_PUBLIC_BUILD_CIBLE: cible };
const url = cibles[cible];
if (url) {
  if (!/^https?:\/\/[^/]+/.test(url)) {
    console.error(`Adresse invalide pour « ${cible} » dans api-cibles.json : ${url}`);
    process.exit(1);
  }
  env.NEXT_PUBLIC_API_BASE_URL = url.replace(/\/+$/, '');
}

console.log(`\n▶ Build « ${cible} » — API : ${env.NEXT_PUBLIC_API_BASE_URL || '(valeur de .env.local / variables Vercel)'}\n`);
const res = spawnSync('npx', ['next', 'build'], { cwd: racine, env, stdio: 'inherit', shell: process.platform === 'win32' });
process.exit(res.status ?? 1);
