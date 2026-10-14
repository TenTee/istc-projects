# Permissions et cloisonnement

La sécurité repose sur **trois niveaux**, tous côté serveur. Le masquage des menus dans le frontend n'est qu'un confort : **ne jamais compter dessus**.

## 1. Comptes portail : liste blanche `PORTAL_RULES`

Fichier : `back-istc/users/middleware.py`.

- Un utilisateur dont `role == "etudiant"` ou `role == "formateur"` (et non admin) ne peut appeler **que** les couples *(méthodes, regex d'URL)* listés dans `PORTAL_RULES[role]`. Tout le reste → **403**.
- `_REFERENTIEL` regroupe les routes de référence en lecture seule communes aux deux portails.
- Le middleware lit le JWT lui-même (`jwt_user`), car `request.user` n'est pas encore authentifié par DRF à ce stade.

!!! danger "Ajouter une route utilisée par un portail"
    1. Ajoutez la règle dans `PORTAL_RULES` (méthodes minimales : `SAFE` si lecture seule).
    2. Dans la **vue**, filtrez les données sur l'utilisateur connecté (le middleware autorise la route, pas les données !).
    3. Ajoutez l'URL à `ROUTES_ETUDIANT` / `ROUTES_FORMATEUR` dans `tests/test_flux_portails.py`.

    Sans l'étape 1, la page du portail reçoit un 403 ; sans l'étape 2, un étudiant pourrait lire les données d'un autre.

## 2. Personnel : matrice des droits `REGLES`

Fichier : `back-istc/users/acces_personnel.py` (middleware `StaffAccessMiddleware`, placé juste après `PortalAccessMiddleware`).

Pour un compte du personnel (ni administrateur, ni étudiant, ni formateur), chaque requête `/api/…` est comparée à la liste `REGLES` ; **la première règle qui correspond s'applique** :

```python
# (motif d'URL, domaines autorisés en lecture, domaines autorisés en écriture)
(r"^/api/etudiants(/|$)", (ET, PEDA, FIN), (ET,)),
(r"^/api/paie(/|$)",      (FIN, RH),       (FIN,)),
(r"^/api/v2/(parametres-globaux|cycles-globaux|configuration-etablissement)(/|$)", TOUS, ADMIN),
```

| Méthode | Condition |
|---|---|
| GET, HEAD, OPTIONS | niveau `lecture` ou `ecriture` sur **un** des domaines de lecture |
| POST, PUT, PATCH, DELETE | niveau `ecriture` sur **un** des domaines d'écriture |
| `TOUS` | tout compte du personnel |
| `ADMIN` | administrateurs uniquement |
| Route sans règle | **administrateurs uniquement** (refus par défaut) |

Le refus renvoie **403** avec un message explicite (« Accès refusé : votre rôle n'a pas le droit Finances en écriture. »).

!!! danger "Ajouter une route d'API"
    Ajoutez sa règle dans `REGLES` (sinon elle est réservée aux administrateurs) et un cas dans `tests/test_flux_droits_personnel.py`.

Les contrôles plus fins restent dans les vues (`users/permissions.py`) :

| Fonction / classe | Usage |
|---|---|
| `is_admin_user(user)` | `is_superuser` ou `role in ADMIN_ROLE_CODES` (`admin`, `superadmin`) |
| `get_role_access_level(user, "can_manage_finance")` | `none` / `lecture` / `ecriture` |
| `user_has_read_access` / `user_has_write_access` | contrôles dans les vues (validation des notes, etc.) |
| `UserAccountPermission` | `/api/auth/` : admin uniquement (sauf sa propre fiche) |
| `RolePermission` | rôles : lecture pour tous, écriture admin |

Un compte dont le code de rôle ne correspond à **aucun** `Role` n'a aucun droit (référentiels seulement). La migration `users/0003_roles_pour_codes_existants` crée les rôles manquants lors de la mise à jour, et `python manage.py audit_droits` affiche les droits effectifs de chaque compte.

Interrupteur d'urgence : `CONTROLE_DROITS_PERSONNEL=False` dans `.env` désactive la matrice (à n'utiliser que le temps de corriger un rôle).

## 3. Années archivées

`academique.middleware.ArchiveAcademicYearMiddleware` : si l'en-tête `X-Academic-Year` désigne une année non active, seuls les superusers passent. Exemptés : `/api/auth/`, `/api/v2/annees-academiques/`, `/api/v2/configuration-etablissement/`, `/admin/`.

## Matrice de contrôle (testée)

| Qui | Admin (`/api/etudiants/`, `/api/paie/…`, …) | Portail étudiant | Portail formateur |
|---|---|---|---|
| Étudiant | 403 | 200 (ses données) | 403 |
| Formateur | 403 | 403 | 200 (ses données) |
| Personnel sans droit sur le domaine | 403 | — | — |
| Personnel avec droit Lecture | 200 en lecture, 403 en écriture | — | — |
| Admin | 200 | — | — |

Tout est vérifié par `tests/test_flux_portails.py`, `tests/test_flux_droits_personnel.py` et `tests/test_flux_authentification.py`.
