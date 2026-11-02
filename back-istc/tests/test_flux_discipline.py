"""
Flux : sanctions disciplinaires.

1. La scolarité (droit Étudiants en écriture) enregistre une sanction ; une exclusion temporaire
   exige une date de fin (la durée est calculée).
2. Elle corrige, lève (avec motif) ou supprime une sanction ; la liste se filtre par état.
3. L'étudiant voit ses sanctions dans son portail, sans accès à celles des autres.
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from etudiants.models import SanctionDisciplinaire
from smart_back.testing import client_api, creer_role, creer_utilisateur

pytestmark = pytest.mark.django_db
URL = "/api/etudiants/sanctions/"


def _sanction(client, etudiant, **extra):
    data = {"etudiant": etudiant.id, "type_sanction": "Avertissement", "motif": "Retards répétés en cours",
            "date_sanction": timezone.localdate().isoformat()}
    data.update(extra)
    return client.post(URL, data, format="json")


def test_enregistrer_un_avertissement(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    res = _sanction(client_admin, etudiant)
    assert res.status_code == 201, res.data
    assert res.data["etat"] == "active" and res.data["enregistree_par_nom"]
    assert res.data["classe_nom"] == monde.classe.nom and res.data["date_fin"] is None


def test_exclusion_temporaire_exige_une_date_de_fin(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    aujourdhui = timezone.localdate()
    res = _sanction(client_admin, etudiant, type_sanction="Exclusion temporaire")
    assert res.status_code == 400 and "date_fin" in res.data
    res = _sanction(client_admin, etudiant, type_sanction="Exclusion temporaire",
                    date_fin=(aujourdhui - timedelta(days=1)).isoformat())
    assert res.status_code == 400 and "date_fin" in res.data
    res = _sanction(client_admin, etudiant, type_sanction="Exclusion temporaire",
                    date_fin=(aujourdhui + timedelta(days=2)).isoformat())
    assert res.status_code == 201, res.data
    assert res.data["duree"] == "3 jours"


def test_validations(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    assert _sanction(client_admin, etudiant, motif="ras").status_code == 400
    demain = (timezone.localdate() + timedelta(days=1)).isoformat()
    assert _sanction(client_admin, etudiant, date_sanction=demain).status_code == 400
    assert _sanction(client_admin, etudiant, type_sanction="Renvoi").status_code == 400


def test_correction_et_changement_de_type(monde, client_admin):
    etudiant, autre = monde.nouvel_etudiant(), monde.nouvel_etudiant()
    debut = timezone.localdate() - timedelta(days=10)
    sid = _sanction(client_admin, etudiant, type_sanction="Exclusion temporaire", date_sanction=debut.isoformat(),
                    date_fin=(debut + timedelta(days=4)).isoformat()).data["id"]
    # Exclusion terminée : elle reste au dossier mais n'est plus « en cours ».
    assert client_admin.get(f"{URL}{sid}/").data["etat"] == "terminee"
    res = client_admin.patch(f"{URL}{sid}/", {"type_sanction": "Blâme"}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["date_fin"] is None and res.data["duree"] is None and res.data["etat"] == "active"
    res = client_admin.patch(f"{URL}{sid}/", {"etudiant": autre.id}, format="json")
    assert res.status_code == 400
    # « active » ne se modifie pas directement : il faut lever la sanction.
    client_admin.patch(f"{URL}{sid}/", {"active": False}, format="json")
    assert SanctionDisciplinaire.objects.get(pk=sid).active is True


def test_lever_puis_retablir(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    sid = _sanction(client_admin, etudiant).data["id"]
    assert client_admin.post(f"{URL}{sid}/lever/", {}, format="json").status_code == 400
    res = client_admin.post(f"{URL}{sid}/lever/", {"motif_levee": "Bon comportement depuis un mois"}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["etat"] == "levee" and res.data["date_levee"] and res.data["levee_par_nom"]
    assert client_admin.post(f"{URL}{sid}/lever/", {"motif_levee": "Encore une fois"},
                             format="json").status_code == 400
    res = client_admin.post(f"{URL}{sid}/retablir/")
    assert res.data["etat"] == "active" and res.data["motif_levee"] == ""


def test_filtres_et_statistiques(monde, client_admin):
    a, b = monde.nouvel_etudiant(nom="Abena Paul"), monde.nouvel_etudiant()
    aujourdhui = timezone.localdate()
    s1 = _sanction(client_admin, a).data["id"]
    _sanction(client_admin, b, type_sanction="Exclusion temporaire",
              date_fin=(aujourdhui + timedelta(days=3)).isoformat())
    _sanction(client_admin, b, type_sanction="Blâme", motif="Fraude à l'examen de mi-parcours")
    client_admin.post(f"{URL}{s1}/lever/", {"motif_levee": "Avertissement purgé"}, format="json")

    assert len(client_admin.get(URL).data) == 3
    assert len(client_admin.get(URL, {"etat": "active"}).data) == 2
    assert [s["id"] for s in client_admin.get(URL, {"etat": "levee"}).data] == [s1]
    assert len(client_admin.get(URL, {"etudiant": b.id}).data) == 2
    assert len(client_admin.get(URL, {"q": "abena"}).data) == 1
    assert len(client_admin.get(URL, {"q": "fraude"}).data) == 1
    assert len(client_admin.get(URL, {"classe": monde.classe.id, "type": "Blâme"}).data) == 1
    stats = client_admin.get(f"{URL}statistiques/").data
    assert (stats["total"], stats["actives"], stats["levees"]) == (3, 2, 1)
    assert stats["etudiants_concernes"] == 1 and stats["exclusions_en_cours"] == 1
    assert stats["par_type"]["Blâme"] == 1


def test_suppression(monde, client_admin):
    sid = _sanction(client_admin, monde.nouvel_etudiant()).data["id"]
    assert client_admin.delete(f"{URL}{sid}/").status_code == 204
    assert not SanctionDisciplinaire.objects.filter(pk=sid).exists()


def test_droits(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    sid = _sanction(client_admin, etudiant).data["id"]
    creer_role("pedagogie_lecture", pedagogie="lecture")
    creer_role("logistique", logistique="ecriture")
    lecteur = client_api(creer_utilisateur(role="pedagogie_lecture"))
    assert lecteur.get(URL).status_code == 200
    assert _sanction(lecteur, etudiant).status_code == 403
    assert lecteur.post(f"{URL}{sid}/lever/", {"motif_levee": "Tentative sans droit"}, format="json").status_code == 403
    assert client_api(creer_utilisateur(role="logistique")).get(URL).status_code == 403
    # Les comptes portail n'ont pas accès à la gestion
    assert client_api(etudiant.user).get(URL).status_code == 403
    formateur = monde.nouveau_formateur()
    assert client_api(formateur.user).get(URL).status_code == 403


def test_portail_etudiant(monde, client_admin):
    etudiant, autre = monde.nouvel_etudiant(), monde.nouvel_etudiant()
    debut = timezone.localdate()
    _sanction(client_admin, etudiant, type_sanction="Exclusion temporaire",
              date_fin=(debut + timedelta(days=1)).isoformat())
    _sanction(client_admin, autre)
    sanctions = client_api(etudiant.user).get("/api/etudiants/me/").data["sanctions"]
    assert len(sanctions) == 1
    assert sanctions[0]["etat"] == "active" and sanctions[0]["date_fin"] == (debut + timedelta(days=1)).isoformat()
