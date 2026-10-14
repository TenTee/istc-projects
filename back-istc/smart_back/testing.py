"""
Fabriques de données pour les tests.

Objectif : écrire un test lisible en 3 lignes sans recopier 30 lignes de mise en place.
Toutes les fonctions acceptent des paramètres nommés pour surcharger les valeurs par défaut.

    from smart_back.testing import Monde

    monde = Monde.creer()             # établissement complet : filière, classe, module…
    etudiant = monde.nouvel_etudiant()
    client = monde.client_pour(etudiant.user)   # client API authentifié par jeton JWT

Utilisable aussi bien avec `django.test.TestCase` / `APITestCase` qu'avec pytest
(voir les fixtures de `conftest.py`).
"""
from dataclasses import dataclass
from datetime import time
from decimal import Decimal
from itertools import count

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from academique.models import (
    AnneeAcademique, Classe, Cycle, CycleGlobal, Departement, Filiere, Niveau, UniversiteTutelle,
)
from emploidutemps.models import EmploiDuTemps, Salle
from etudiants.models import Etudiant, Inscription
from formateurs.models import Formateur
from modules.models import Module
from personnels.models import Personnel
from users.models import Role

User = get_user_model()
_seq = count(1)


def _n():
    return next(_seq)


# ---------------------------------------------------------------------------
# Comptes
# ---------------------------------------------------------------------------

def creer_role(code, **droits):
    """Rôle avec droits par module : rh, pedagogie, logistique, finance, etudiants = none|lecture|ecriture."""
    champs = {f"can_manage_{k}": v for k, v in droits.items()}
    role, _ = Role.objects.update_or_create(code=code, defaults={"libelle": code.title(), **champs})
    return role


def creer_utilisateur(role="admin", **kwargs):
    n = _n()
    data = {"noms": f"Nom{n}", "prenoms": f"Prenom{n}", "email": f"user{n}@test.local", "role": role}
    data.update(kwargs)
    return User.objects.create(**data)


def client_api(user=None, annee=None):
    """
    Client API authentifié par un vrai jeton JWT (et non `force_authenticate`), afin que
    les middlewares (contrôle d'accès des portails, année archivée) soient bien exercés.
    """
    client = APIClient()
    headers = {}
    if user is not None:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {AccessToken.for_user(user)}"
    if annee is not None:
        headers["HTTP_X_ACADEMIC_YEAR"] = str(getattr(annee, "pk", annee))
    client.credentials(**headers)
    return client


# ---------------------------------------------------------------------------
# Établissement complet
# ---------------------------------------------------------------------------

@dataclass
class Monde:
    annee: AnneeAcademique
    filiere: Filiere
    cycle: Cycle
    niveau: Niveau
    classe: Classe
    module: Module
    salle: Salle
    admin: object

    @classmethod
    def creer(cls, libelle_annee="2026-2027", semestre_module="Semestre 1"):
        n = _n()
        dept = Departement.objects.create(
            nom=f"Département {n}", universite_tutelle=UniversiteTutelle.objects.create(nom=f"Université {n}")
        )
        filiere = Filiere.objects.create(nom=f"Informatique {n}", departement=dept)
        annee = AnneeAcademique.objects.filter(libelle=libelle_annee).first() or AnneeAcademique.objects.create(
            libelle=libelle_annee, est_active=True
        )
        type_cycle = CycleGlobal.objects.create(nom=f"Licence {n}")
        cycle = Cycle.objects.create(type_cycle=type_cycle, filiere=filiere, nom="Licence")
        niveau = Niveau.objects.create(cycle=cycle, nom="L1")
        # La classe de l'année est créée automatiquement par signal à la création du niveau.
        classe = Classe.objects.get(niveau=niveau, annee_academique=annee)
        module = Module.objects.create(nom=f"Algorithmique {n}", semestre=semestre_module, coefficient=2)
        classe.modules.add(module)
        salle = Salle.objects.create(nom=f"Salle {n}")
        admin = creer_utilisateur(role="admin")
        return cls(annee, filiere, cycle, niveau, classe, module, salle, admin)

    # -- personnes ---------------------------------------------------------
    def nouvel_etudiant(self, inscrire=True, **kwargs):
        n = _n()
        data = {"nom": f"Étudiant {n}", "contact": f"6900{n:05d}", "email": f"etu{n}@test.local", "filiere": self.filiere}
        data.update(kwargs)
        etudiant = Etudiant.objects.create(**data)
        etudiant.refresh_from_db()  # récupère le compte créé par signal
        if inscrire:
            Inscription.objects.create(
                etudiant=etudiant, classe=self.classe, niveau=self.niveau, annee_academique=self.annee.libelle
            )
        return etudiant

    def nouveau_formateur(self, vacataire=False, avec_compte=True, **kwargs):
        n = _n()
        user = creer_utilisateur(role="formateur") if avec_compte else None
        data = {
            "nom": f"Formateur {n}", "email": f"form{n}@test.local", "contact": f"6700{n:05d}", "user": user,
            "type_formateur": "vacataire" if vacataire else "permanent",
            "taux_horaire": Decimal("5000") if vacataire else Decimal("0"),
            "salaire": Decimal("0") if vacataire else Decimal("250000"),
        }
        data.update(kwargs)
        return Formateur.objects.create(**data)

    def nouveau_personnel(self, **kwargs):
        n = _n()
        data = {"nom": f"Agent {n}", "contact": f"6500{n:05d}", "salaire": Decimal("150000")}
        data.update(kwargs)
        return Personnel.objects.create(**data)

    # -- pédagogie ---------------------------------------------------------
    def nouvelle_seance(self, formateur, jour="Lundi", debut=time(8, 0), fin=time(10, 0), **kwargs):
        data = {
            "classe": self.classe, "module": self.module, "formateur": formateur,
            "jour": jour, "heure_debut": debut, "heure_fin": fin, "salle": self.salle,
        }
        data.update(kwargs)
        return EmploiDuTemps.objects.create(**data)

    # -- clients -----------------------------------------------------------
    def client_pour(self, user, annee=None):
        return client_api(user, annee=annee)

    def client_admin(self):
        return client_api(self.admin)
