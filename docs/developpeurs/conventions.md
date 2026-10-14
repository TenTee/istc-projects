# Conventions de code

## Langue

- **Domaine métier en français** (modèles, champs, messages, tests) : `Inscription`, `solde_restant`, `test_une_bourse_ne_sert_qu_une_fois`. C'est la langue des utilisateurs et des messages d'erreur affichés.
- Termes techniques génériques en anglais acceptés (`serializer`, `queryset`, `payload`).
- Messages d'erreur destinés à l'utilisateur : phrase complète en français, qui dit **quoi faire** (« Le récapitulatif ne peut être clôturé qu'à partir du dernier jour du mois. »).

## Backend (Python / Django)

- Style PEP 8, lignes ≤ 120 caractères. Vérification : `ruff check back-istc` (si installé).
- Montants : `Decimal`, jamais `float`. Dates : `django.utils.timezone`.
- Opérations multi-tables (paiement d'une campagne, approbation d'une préinscription, congés) dans `transaction.atomic()`.
- Pas de requête dans une boucle quand un `select_related` / `prefetch_related` / agrégat suffit.
- Les imports à effet de bord (signaux dans `apps.py`) portent `# noqa: F401`.
- Ne jamais renvoyer un mot de passe ou un secret dans une liste ; `initial_password` est en lecture seule.
- Erreurs : `ValidationError` (400) pour une saisie invalide, `PermissionDenied` (403) pour un droit manquant.

## Frontend (Next.js / React)

- Composants fonctionnels + hooks ; une page = `page.js` dans `src/app/...`.
- Tout appel réseau passe par `src/services/api/services.js`.
- Formulaires : `react-hook-form` + `yup` quand le formulaire dépasse quelques champs.
- Libellés d'interface en français, cohérents avec le guide utilisateur (si vous renommez un bouton, mettez à jour `docs/guide/`).
- Pas de `alert()` pour une erreur serveur : `Snackbar` + `getApiErrorMessage`.
- `npm run lint` doit passer sans erreur. Configuration : `frontend/eslint.config.mjs` (`eslint-config-next`) ; `react/no-unescaped-entities` est désactivée (apostrophes françaises) et `react-hooks/set-state-in-effect` est en avertissement, le temps de migrer les composants concernés : ne pas ajouter de nouveaux avertissements.

## Git

- Branche par sujet : `feature/bourses-externes`, `fix/solde-portail`.
- Messages de commit à l'impératif, en français : `Corrige le calcul du solde avec réduction`.
- Une pull request = un sujet, avec : contexte, captures d'écran pour l'interface, tests ajoutés, impact migration / configuration.
- Ne jamais committer : `.env`, `db.sqlite3`, `media/`, `venv/`, `node_modules/`, `.next/` (voir `.gitignore`).

## Revue de code — points à vérifier

1. Les droits sont-ils vérifiés côté serveur ?
2. Une route de portail filtre-t-elle bien sur l'utilisateur connecté ?
3. Les calculs financiers passent-ils par `paiements/finance.py` ?
4. Y a-t-il une migration ? Est-elle réversible / sans perte ?
5. Un test couvre-t-il le changement ?
6. Le guide utilisateur est-il à jour ?
