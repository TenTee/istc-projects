"""
Flux : droits du personnel appliqués par le serveur (users/acces_personnel.py).

Un rôle donne, pour chaque domaine, Aucun / Lecture / Écriture. Le serveur doit :
- refuser (403) toute route d'un domaine sur lequel le rôle n'a aucun droit ;
- autoriser la lecture mais refuser l'écriture avec le droit « Lecture » ;
- laisser les référentiels (classes, filières, années…) lisibles par tout le personnel ;
- ne jamais limiter les administrateurs.
"""
import pytest

from smart_back.testing import client_api, creer_role, creer_utilisateur
from users.acces_personnel import REGLES, regle_pour

pytestmark = pytest.mark.django_db

ROUTES_PAR_DOMAINE = {
    "etudiants": ["/api/etudiants/", "/api/v2/inscriptions/"],
    "finance": ["/api/paiements/", "/api/paiements/aggregated/", "/api/paie/campagnes/", "/api/revenus/",
                "/api/depenses/", "/api/v2/frais/", "/api/bourses/", "/api/vacations/recaps/"],
    "pedagogie": ["/api/notes/", "/api/assiduite/", "/api/v2/epreuves/", "/api/vacations/coordinations/"],
    "logistique": ["/api/inventaires/articles/", "/api/demandes/"],
    "rh": ["/api/conges/", "/api/personnels/"],
}
REFERENTIELS = ["/api/v2/classes/", "/api/v2/filieres/", "/api/v2/annees-academiques/", "/api/modules/",
                "/api/salles/", "/api/emploi-du-temps/", "/api/v2/configuration-etablissement/current/",
                "/api/auth/roles/"]


def compte(**droits):
    code = "role_" + "_".join(f"{k}{v[0]}" for k, v in sorted(droits.items())) if droits else "role_vide"
    creer_role(code, **droits)
    return client_api(creer_utilisateur(role=code))


@pytest.mark.parametrize("domaine", ROUTES_PAR_DOMAINE)
def test_sans_droit_le_domaine_est_refuse(monde, domaine):
    client = compte()  # rôle sans aucun droit
    for url in ROUTES_PAR_DOMAINE[domaine]:
        res = client.get(url)
        assert res.status_code == 403, url
        assert "Accès refusé" in res.json()["detail"]


@pytest.mark.parametrize("domaine", ROUTES_PAR_DOMAINE)
def test_le_droit_de_lecture_ouvre_son_domaine(monde, domaine):
    client = compte(**{domaine: "lecture"})
    for url in ROUTES_PAR_DOMAINE[domaine]:
        assert client.get(url).status_code == 200, url


def test_les_referentiels_sont_lisibles_par_tout_le_personnel(monde):
    client = compte()
    for url in REFERENTIELS:
        assert client.get(url).status_code == 200, url


def test_lecture_seule_interdit_l_ecriture(monde):
    client = compte(finance="lecture")
    res = client.post("/api/paie/campagnes/generer/", {"mois": 1, "annee": 2026, "type_beneficiaire": "personnel"},
                      format="json")
    assert res.status_code == 403
    assert "Finances en écriture" in res.json()["detail"]
    assert client.post("/api/revenus/", {}, format="json").status_code == 403


def test_un_compte_sans_droit_ne_peut_plus_generer_la_paie(monde):
    """Faille d'origine : un compte du personnel sans aucun droit générait une campagne de paie."""
    monde.nouveau_personnel()
    res = compte().post("/api/paie/campagnes/generer/", {"mois": 1, "annee": 2026, "type_beneficiaire": "personnel"},
                        format="json")
    assert res.status_code == 403


def test_le_droit_d_ecriture_permet_d_agir(monde):
    monde.nouveau_personnel()
    client = compte(finance="ecriture")
    res = client.post("/api/paie/campagnes/generer/", {"mois": 2, "annee": 2026, "type_beneficiaire": "personnel"},
                      format="json")
    assert res.status_code == 201


def test_lectures_croisees_utiles_aux_ecrans(monde):
    """La Scolarité (finance) lit les étudiants ; la paie lit le personnel et les formateurs."""
    client = compte(finance="ecriture")
    for url in ["/api/etudiants/", "/api/personnels/", "/api/formateurs/", "/api/v2/inscriptions/"]:
        assert client.get(url).status_code == 200, url
    # …mais ne peut pas les modifier
    assert client.post("/api/etudiants/", {}, format="json").status_code == 403
    assert client.post("/api/personnels/", {}, format="json").status_code == 403


def test_parametres_systeme_reserves_a_l_administration(monde):
    client = compte(pedagogie="ecriture", finance="ecriture", etudiants="ecriture", rh="ecriture",
                    logistique="ecriture")
    assert client.get("/api/v2/parametres-globaux/").status_code == 200
    assert client.post("/api/v2/cycles-globaux/", {"nom": "X"}, format="json").status_code == 403
    assert client.get("/api/logs/").status_code == 403


def test_un_role_inexistant_n_a_aucun_droit(monde):
    client = client_api(creer_utilisateur(role="code_inconnu"))
    assert client.get("/api/paiements/").status_code == 403
    assert client.get("/api/v2/classes/").status_code == 200


def test_les_administrateurs_ne_sont_pas_limites(monde, client_admin):
    for urls in ROUTES_PAR_DOMAINE.values():
        for url in urls:
            assert client_admin.get(url).status_code == 200, url


def test_interrupteur_d_urgence(monde, monkeypatch):
    monkeypatch.setenv("CONTROLE_DROITS_PERSONNEL", "False")
    assert compte().get("/api/paiements/").status_code == 200


def test_route_inconnue_reservee_a_l_administration():
    assert regle_pour("/api/route-inventee/") == ("administration", "administration")


def test_chaque_regle_est_un_motif_valide():
    import re
    for motif, lecture, ecriture in REGLES:
        re.compile(motif)
        assert lecture and ecriture


def test_audit_des_droits(monde, capsys):
    from django.core.management import call_command
    creer_utilisateur(role="code_inconnu", username="sans.role")
    call_command("audit_droits")
    sortie = capsys.readouterr().out
    assert "sans.role" in sortie and "rôle inexistant" in sortie


def test_migration_cree_les_roles_manquants(db):
    """Mise à jour : les codes de rôle utilisés sans fiche Rôle reçoivent un rôle (personne n'est bloqué)."""
    import importlib
    from django.apps import apps
    from users.models import Role
    migration = importlib.import_module("users.migrations.0003_roles_pour_codes_existants")
    creer_utilisateur(role="responsableRh")
    creer_utilisateur(role="secretaire_accueil")
    creer_utilisateur(role="code_maison")
    Role.objects.create(code="comptable", libelle="Comptable perso", can_manage_finance="lecture")
    creer_utilisateur(role="comptable")
    migration.creer_roles_manquants(apps, None)
    assert Role.objects.get(code="responsableRh").can_manage_rh == "ecriture"
    assert Role.objects.get(code="secretaire_accueil").can_manage_finance == "ecriture"
    assert Role.objects.get(code="code_maison").can_manage_finance == "none"
    assert Role.objects.get(code="comptable").libelle == "Comptable perso"  # rôle existant inchangé
