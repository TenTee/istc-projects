# Démonstration SmartCampus (données fictives)

```bash
./outils/demo/lancer_demo.sh          # premier lancement : crée la base puis démarre
./outils/demo/lancer_demo.sh --reset  # repartir d'une base de démo neuve
```

Ouvrez http://localhost:3001. Comptes (mot de passe `Demo2026!`) :

| Compte | Profil |
|---|---|
| `admin.demo` | Administrateur (tous les menus) |
| `formateur.demo` | Formateur permanent, coordonnateur de la filière Génie Informatique |
| `etudiant.demo` | Étudiante en Développement Web — Licence 1 |

Tout est inventé : établissement, personnes, montants. La base (`demo.sqlite3`) et les fichiers (`media/`)
restent dans ce dossier et ne touchent ni la base habituelle ni le dossier `back-istc/media/`.
Le contenu est défini dans `back-istc/academique/management/commands/seed_demo.py`.

Usages : formations, démonstrations, et captures d'écran du guide (`docs/images/captures/`).
Arrêtez d'abord tout autre `npm run dev` du projet (un seul serveur Next.js par dossier).

## Refaire les captures d'écran du guide

1. Lancez la démo (ci-dessus) : la route `/api/demo-capture`, active uniquement en développement, enregistre les images.
2. Ouvrez http://localhost:3001 dans Chrome (fenêtre de 1440 × 900), connectez-vous avec le compte voulu.
3. Ouvrez la console (F12), collez le contenu de `outils/demo/capture.js`, puis `await __cap('nom_de_la_capture')`.
   `__mark([élément, …])` encadre et numérote en rouge les boutons à montrer.
4. Les images arrivent dans `docs/images/captures/` ; relancez `outils/doc-word/construire.sh` pour le Word.

Les noms des captures utilisées et leurs légendes sont visibles dans les pages de `docs/guide/` (syntaxe `![légende](…/images/captures/nom.jpg)`).
