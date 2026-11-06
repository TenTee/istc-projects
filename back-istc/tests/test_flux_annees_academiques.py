"""
Flux : droits sur les années académiques.

1. Le droit « Gestion des années académiques » d'un rôle permet de créer, modifier, activer et
   supprimer (si vide) une année ; sans lui, ces actions sont refusées.
2. Le droit « Années archivées » (aucun / lecture / écriture) ouvre l'accès aux années non actives,
   en plus des droits par domaine.
3. Les deux droits figurent dans le rôle (API) et dans le jeton de connexion.
"""
import importlib

import pytest
from django.apps import apps

from academique.models import AnneeAcademique, Classe
from etudiants.models import Inscription
from smart_back.testing import client_api, creer_role, creer_utilisateur
from users.models import Role
from users.serializers import MyTokenObtainPairSerializer

pytestmark = pytest.mark.django_db
URL = "/api/v2/annees-academiques/"


def _client(code, archives="none", annees=False, annee=None, **droits):
    creer_role(code, **droits)
    Role.objects.filter(code=code).update(acces_annees_archivees=archives, can_manage_annees=annees)
    return client_api(creer_utilisateur(role=code), annee=annee)


@pytest.fixture
def archivee(monde):
    return AnneeAcademique.objects.create(libelle="2020-2021", est_active=False)


# --------------------------------------------------------------------------- gestion des années

def test_gestion_reservee_au_droit_dedie(monde):
    pedagogie = _client("pedagogie", pedagogie="ecriture")
    assert pedagogie.get(URL).status_code == 200
    res = pedagogie.post(URL, {"libelle": "2027-2028"}, format="json")
    assert res.status_code == 403 and "années académiques" in res.json()["detail"]

    gestionnaire = _client("scolarite_chef", annees=True)
    res = gestionnaire.post(URL, {"libelle": "2027-2028", "date_debut": "2027-09-01", "date_fin": "2028-07-31"},
                            format="json")
    assert res.status_code == 201, res.data
    nouvelle = res.data["id"]
    assert gestionnaire.patch(f"{URL}{nouvelle}/", {"description": "Rentrée"}, format="json").status_code == 200


def test_activer_une_annee_archive_l_ancienne(monde):
    gestionnaire = _client("direction", annees=True)
    nouvelle = AnneeAcademique.objects.create(libelle="2027-2028")
    res = gestionnaire.post(f"{URL}{nouvelle.id}/activer/")
    assert res.status_code == 200 and res.data["est_active"] is True
    monde.annee.refresh_from_db()
    assert monde.annee.est_active is False
    assert list(AnneeAcademique.objects.filter(est_active=True)) == [nouvelle]
    # Activer par modification (case « active ») fonctionne aussi
    res = gestionnaire.patch(f"{URL}{monde.annee.id}/", {"est_active": True}, format="json")
    assert res.status_code == 200
    assert AnneeAcademique.objects.get(est_active=True) == monde.annee


def test_l_annee_active_ne_se_desactive_pas_sans_remplacante(monde):
    gestionnaire = _client("direction", annees=True)
    res = gestionnaire.patch(f"{URL}{monde.annee.id}/", {"est_active": False}, format="json")
    assert res.status_code == 400 and "est_active" in res.data
    monde.annee.refresh_from_db()
    assert monde.annee.est_active is True


def test_suppression_protegee(monde, archivee):
    gestionnaire = _client("direction", annees=True)
    assert gestionnaire.delete(f"{URL}{monde.annee.id}/").status_code == 400   # année active
    etudiant = monde.nouvel_etudiant(inscrire=False)
    classe_archivee = Classe.objects.filter(annee_academique=archivee, niveau=monde.niveau).first()
    assert classe_archivee is not None  # classes recopiées à la création de l'année
    Inscription.objects.create(etudiant=etudiant, classe=classe_archivee, niveau=monde.niveau,
                               annee_academique=archivee.libelle, annee_academique_ref=archivee)
    res = gestionnaire.delete(f"{URL}{archivee.id}/")
    assert res.status_code == 400 and "inscriptions" in res.json()["detail"]
    vide = AnneeAcademique.objects.create(libelle="2030-2031")
    assert gestionnaire.delete(f"{URL}{vide.id}/").status_code == 204
    assert _client("pedagogie", pedagogie="ecriture").delete(f"{URL}{archivee.id}/").status_code == 403


def test_les_portails_ne_gerent_pas_les_annees(monde):
    etudiant = monde.nouvel_etudiant()
    assert client_api(etudiant.user).post(URL, {"libelle": "2031-2032"}, format="json").status_code == 403


# --------------------------------------------------------------------------- années archivées

def test_sans_droit_les_archives_sont_fermees(monde, archivee):
    client = _client("scolarite", etudiants="ecriture", annee=archivee)
    res = client.get("/api/etudiants/")
    assert res.status_code == 403 and "2020-2021" in res.json()["detail"]
    assert client.get(URL).status_code == 200   # la liste des années reste lisible


def test_archives_en_lecture_seule(monde, archivee):
    client = _client("scolarite", archives="lecture", etudiants="ecriture", annee=archivee)
    assert client.get("/api/etudiants/").status_code == 200
    res = client.post("/api/etudiants/sanctions/", {}, format="json")
    assert res.status_code == 403 and "consulter mais pas la modifier" in res.json()["detail"]


def test_archives_en_ecriture_et_droits_par_domaine(monde, archivee):
    client = _client("scolarite", archives="ecriture", etudiants="ecriture", annee=archivee)
    etudiant = monde.nouvel_etudiant()
    res = client.post("/api/etudiants/sanctions/", {"etudiant": etudiant.id, "type_sanction": "Avertissement",
                                                    "motif": "Retards répétés en cours"}, format="json")
    assert res.status_code == 201, res.data
    # Le droit sur les archives n'ouvre pas les domaines que le rôle n'a pas.
    assert client.get("/api/paie/campagnes/").status_code == 403


def test_administrateurs_et_portails(monde, archivee):
    admin = client_api(creer_utilisateur(role="admin"), annee=archivee)
    assert admin.get("/api/etudiants/").status_code == 200
    etudiant = monde.nouvel_etudiant()
    assert client_api(etudiant.user, annee=archivee).get("/api/etudiants/me/").status_code == 403


# --------------------------------------------------------------------------- rôles et jeton

def test_les_droits_se_reglent_dans_le_role(monde, client_admin):
    res = client_admin.post("/api/auth/roles/", {"code": "direction_etudes", "libelle": "Direction des études",
                                                 "can_manage_pedagogie": "lecture", "can_manage_annees": True,
                                                 "acces_annees_archivees": "lecture"}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["can_manage_annees"] is True and res.data["acces_annees_archivees"] == "lecture"
    res = client_admin.post("/api/auth/roles/", {"code": "x", "libelle": "x", "acces_annees_archivees": "tout"},
                            format="json")
    assert res.status_code == 400

    jeton = MyTokenObtainPairSerializer.get_token(creer_utilisateur(role="direction_etudes"))
    assert jeton["permissions"]["can_manage_annees"] is True
    assert jeton["permissions"]["acces_annees_archivees"] == "lecture"


def test_migration_conserve_le_droit_des_roles_pedagogie(db):
    creer_role("ancien_peda", pedagogie="ecriture")
    creer_role("lecteur", pedagogie="lecture")
    Role.objects.update(can_manage_annees=False)
    migration = importlib.import_module("users.migrations.0004_droits_annees_academiques")
    migration.conserver_les_droits_existants(apps, None)
    assert Role.objects.get(code="ancien_peda").can_manage_annees is True
    assert Role.objects.get(code="lecteur").can_manage_annees is False
