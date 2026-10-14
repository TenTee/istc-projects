# SmartCampus — Interface (Next.js)

```bash
npm install
cp .env.example .env.local     # NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_RECAPTCHA_SITE_KEY
npm run dev                    # http://localhost:3000
npm run lint                   # ESLint
npm run build && npm start     # production
```

- Pages : `src/app/(dashboard)` (administration), `src/app/(formateur-portal)`, `src/app/(portal)` (étudiant), `login`, `preinscription`.
- Appels API : uniquement via `src/services/api/services.js`.
- Menus : `src/config/routes.js` ; droits : `src/utils/permissions.js`.

Documentation complète : `../docs/` (architecture, conventions, guide d'utilisation).
