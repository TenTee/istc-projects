"""
Flux : portails étudiant et formateur, et cloisonnement des accès.

Chaque page des portails appelle des routes précises (voir `users/middleware.py`).
Ces tests vérifient :
- que TOUTES ces routes fonctionnent pour le bon type de compte (sinon une page du portail casse) ;
- que les routes d'administration sont refusées (403) aux comptes portail ;
- que le personnel garde accès à l'administration.
"""
import pytest

from academique.models import Affectation
from smart_back.testing import client_api, creer_role, creer_utilisateur

pytestmark = pytest.mark.django_db

ROUTES_ETUDIANT = [
    "/api/etudiants/me/",
    "/api/etudiants/me/situation/",
    "/api/etudiants/me/history/",
    "/api/etudiants/portal/carte-etudiant/",
    "/api/etudiants/portal/certificat-scolarite/",
    "/api/emploi-du-temps/me/",
    "/api/emploi-du-temps-documents/me/",
    "/api/paiements/me/",
    "/api/notes/me/",
    "/api/assiduite/",
    "/api/formateurs/cours-etudiants/",
    "/api/v2/epreuves/",
    "/api/v2/annees-academiques/",
    "/api/v2/configuration-etablissement/current/",
    "/api/auth/roles/",
]

ROUTES_FORMATEUR = [
    "/api/formateurs/portal/me/",
    "/api/formateurs/portal/dashboard/",
    "/api/formateurs/portal/mes-classes/",
    "/api/formateurs/portal/mon-emploi-du-temps/",
    "/api/formateurs/portal/mes-notes/",
    "/api/formateurs/portal/mon-suivi/",
    "/api/formateurs/portal/mes-epreuves/",
    "/api/formateurs/cours-documents/",
    "/api/emploi-du-temps-documents/formateur/",
    "/api/vacations/mes-heures/",
    "/api/vacations/mes-heures/historique/",
    "/api/v2/filieres/",
    "/api/v2/levels/",
    "/api/v2/semestres/",
    "/api/v2/parametres-globaux/",
    "/api/v2/annees-academiques/",
]

ROUTES_ADMINISTRATION = [
    "/api/etudiants/",
    "/api/formateurs/",
    "/api/personnels/",
    "/api/paiements/",
    "/api/paiements/aggregated/",
    "/api/paie/campagnes/",
    "/api/paie/bulletins/",
    "/api/revenus/",
    "/api/depenses/",
    "/api/conges/",
    "/api/inventaires/articles/",
    "/api/demandes/",
    "/api/notes/",
    "/api/v2/pre-inscriptions/",
    "/api/v2/inscriptions/",
    "/api/vacations/recaps/",
    "/api/auth/",
]


@pytest.fixture
def etudiant(monde):
    return monde.nouvel_etudiant()


@pytest.fixture
def formateur(monde):
    f = monde.nouveau_formateur()
    Affectation.objects.create(enseignant=f, module=monde.module, classe=monde.classe)
    monde.nouvelle_seance(f)
    return f


@pytest.mark.parametrize("url", ROUTES_ETUDIANT)
def test_routes_du_portail_etudiant_accessibles(url, etudiant):
    res = client_api(etudiant.user).get(url)
    assert res.status_code == 200, f"{url} → {res.status_code} {getattr(res, 'data', '')}"


@pytest.mark.parametrize("url", ROUTES_FORMATEUR)
def test_routes_du_portail_formateur_accessibles(url, formateur):
    res = client_api(formateur.user).get(url)
    assert res.status_code == 200, f"{url} → {res.status_code} {getattr(res, 'data', '')}"


@pytest.mark.parametrize("url", ROUTES_ADMINISTRATION)
def test_administration_refusee_aux_etudiants(url, etudiant):
    assert client_api(etudiant.user).get(url).status_code == 403


@pytest.mark.parametrize("url", ROUTES_ADMINISTRATION)
def test_administration_refusee_aux_formateurs(url, formateur):
    assert client_api(formateur.user).get(url).status_code == 403


@pytest.mark.parametrize("url", [u for u in ROUTES_ADMINISTRATION if u != "/api/auth/"])
def test_le_personnel_avec_droits_de_lecture_accede_a_l_administration(url, monde):
    creer_role("direction", etudiants="lecture", pedagogie="lecture", finance="lecture", logistique="lecture",
               rh="lecture")
    direction = creer_utilisateur(role="direction")
    assert client_api(direction).get(url).status_code == 200, url


def test_ecritures_interdites_meme_sur_routes_de_lecture(etudiant):
    client = client_api(etudiant.user)
    assert client.post("/api/assiduite/", {}, format="json").status_code == 403
    assert client.post("/api/v2/epreuves/", {}, format="json").status_code == 403
    assert client.delete("/api/v2/annees-academiques/1/").status_code == 403


def test_contenu_du_portail_etudiant(monde, etudiant, formateur):
    client = client_api(etudiant.user)
    situation = client.get("/api/etudiants/me/situation/").data
    assert situation["est_inscrit"] is True
    edt = client.get("/api/emploi-du-temps/me/").data
    assert len(edt) == 1 and edt[0]["formateur_nom"] == formateur.nom
    carte = client.get("/api/etudiants/portal/carte-etudiant/").data
    assert carte["matricule"] == etudiant.matricule and carte["classe"] == monde.classe.nom


def test_tableau_de_bord_formateur(monde, formateur, etudiant):
    data = client_api(formateur.user).get("/api/formateurs/portal/dashboard/").data
    assert data["stats"]["total_classes"] == 1
    assert data["stats"]["total_etudiants"] == 1
    assert data["profil"]["est_coordonnateur"] is False
