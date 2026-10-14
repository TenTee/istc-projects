// Outil de documentation : enregistre des captures d'écran de la démo locale.
// Actif UNIQUEMENT en développement ET si DEMO_CAPTURE_DIR est défini
// (voir outils/demo/lancer_demo.sh). En production, la route répond 404.
import { promises as fs } from 'fs';
import path from 'path';

const actif = () => process.env.NODE_ENV !== 'production' && Boolean(process.env.DEMO_CAPTURE_DIR);
const introuvable = () => new Response('Not found', { status: 404 });

// GET : fournit html2canvas (déjà dépendance du projet) à la page à capturer.
export async function GET() {
  if (!actif()) return introuvable();
  const lib = path.join(process.cwd(), 'node_modules', 'html2canvas', 'dist', 'html2canvas.min.js');
  const code = await fs.readFile(lib, 'utf8');
  return new Response(code, { headers: { 'Content-Type': 'application/javascript' } });
}

// POST { nom, image } : écrit image (data URL PNG/JPEG) dans DEMO_CAPTURE_DIR/<nom>.<ext>.
export async function POST(request) {
  if (!actif()) return introuvable();
  const { nom, image } = await request.json();
  const sur = String(nom || '').replace(/[^a-z0-9_-]/gi, '').slice(0, 80);
  const m = /^data:image\/(png|jpeg);base64,(.+)$/.exec(String(image || ''));
  if (!sur || !m) return new Response('Requête invalide', { status: 400 });
  const ext = m[1] === 'jpeg' ? 'jpg' : 'png';
  await fs.mkdir(process.env.DEMO_CAPTURE_DIR, { recursive: true });
  const fichier = path.join(process.env.DEMO_CAPTURE_DIR, `${sur}.${ext}`);
  await fs.writeFile(fichier, Buffer.from(m[2], 'base64'));
  return Response.json({ ok: true, fichier: `${sur}.${ext}` });
}
