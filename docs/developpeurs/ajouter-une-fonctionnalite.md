# Ajouter une fonctionnalité

Recette type, illustrée par un exemple : **ajouter des « Bourses externes » (organisme financeur) visibles par l'étudiant**.

## 1. Modèle (backend)

Choisissez l'app du domaine (ici `paiements`). Dans `models.py` :

```python
class BourseExterne(models.Model):
    etudiant = models.ForeignKey("etudiants.Etudiant", on_delete=models.CASCADE, related_name="bourses_externes")
    organisme = models.CharField(max_length=150)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    annee_academique = models.ForeignKey("academique.AnneeAcademique", on_delete=models.PROTECT)

    def clean(self):           # règle métier ICI, pas dans la vue ni le frontend
        if self.montant <= 0:
            raise ValidationError({"montant": "Le montant doit être positif."})
```

```bash
python manage.py makemigrations paiements
python manage.py migrate
```

Committez **le fichier de migration** avec le code.

## 2. API

- `serializers.py` : un `ModelSerializer` ; appelez `instance.clean()` dans `validate()` si la règle est dans le modèle (voir `emploidutemps/serializers.py`).
- `views.py` : un `ModelViewSet` ; contrôlez les droits dans `perform_create/update/destroy` avec `user_has_write_access(request.user, "can_manage_finance")`.
- Filtrez par année : `get_current_academic_year_id()` (`academique.middleware`).
- `urls.py` : `router.register("bourses-externes", BourseExterneViewSet)`.

## 3. Droits et portails

- Route d'administration : ajoutez sa règle dans `REGLES` (`users/acces_personnel.py`), par exemple
  `(r"^/api/bourses-externes(/|$)", (FIN, ET), (FIN,))`. Sans règle, seule l'administration y accède. Elle est automatiquement interdite aux comptes portail.
- Route lue par le **portail étudiant** (ex. `/api/paiements/me/bourses-externes/`) : ajoutez-la à `PORTAL_RULES["etudiant"]` dans `users/middleware.py` **et** filtrez sur `request.user` dans la vue. Voir [Permissions](permissions.md).

## 4. Écran (frontend)

1. Endpoint dans `src/services/api/endpoints.js`, service dans `src/services/api/services.js` (réutilisez `createCrudService`).
2. Page dans `src/app/(dashboard)/<chemin>/page.js` (ou un composant dans `src/components/<domaine>/`).
3. Entrée de menu dans `src/config/routes.js` ; si elle dépend d'un domaine de droits, ajoutez son libellé au bon groupe dans `components/layout/Sidebar.js`.
4. Masquez les boutons d'écriture selon `useUserPermissions()` (`utils/permissions.js`) — le serveur reste juge.
5. Affichez les erreurs serveur (`getApiErrorMessage(err)`) dans un `Snackbar`.

## 5. Tests

Ajoutez un scénario dans `back-istc/tests/` (voir [Tests](tests.md)) :

- le cas nominal (création, effet attendu) ;
- un cas refusé (validation, droits insuffisants) ;
- la route de portail dans `ROUTES_ETUDIANT`, la route d'admin dans `ROUTES_ADMINISTRATION`.

## 6. Documentation

- Guide utilisateur : la page du module dans `docs/guide/…` (noms exacts des boutons, procédure pas à pas, messages d'erreur).
- `docs/developpeurs/applications.md` si une app ou un préfixe d'URL est ajouté.
- `docs/installation/configuration.md` si une variable `.env` est ajoutée (et `back-istc/.env.example`).

## Liste de contrôle avant la pull request

- [ ] Migration générée et committée
- [ ] Règle métier dans le modèle / un service, testée
- [ ] Droits contrôlés côté serveur (règle ajoutée dans `REGLES`)
- [ ] `PORTAL_RULES` mis à jour si la route sert un portail
- [ ] `python -m pytest -q` vert, `npm run lint` sans erreur, `npm run build` OK
- [ ] Guide utilisateur mis à jour
