"""
Flux : saisie, validation et consultation des notes.

1. L'inscription d'un étudiant dans une classe prépare une note vide par module.
2. La pédagogie (ou le formateur depuis son portail) saisit CC et SN.
3. Les notes restent invisibles pour l'étudiant tant qu'elles ne sont pas validées.
4. L'étudiant consulte ses notes validées et son relevé ; les rattrapages sont listés.
"""
from decimal import Decimal

import pytest

from academique.models import Affectation, ParametresGlobaux
from notes.models import Note
from smart_back.testing import client_api, creer_role, creer_utilisateur

pytestmark = pytest.mark.django_db


def _saisie(client, monde, etudiant, cc, sn):
    return client.post("/api/notes/batch-save/", {"notes": [{
        "etudiant_id": etudiant.id, "module_id": monde.module.id, "classe_id": monde.classe.id,
        "note_cc": cc, "note_sn": sn,
    }]}, format="json")


def test_inscription_prepare_une_note_par_module(monde):
    etudiant = monde.nouvel_etudiant()
    notes = Note.objects.filter(etudiant=etudiant)
    assert notes.count() == 1
    note = notes.get()
    assert note.module == monde.module and note.session == monde.module.semestre and note.note_finale is None


def test_saisie_groupee_par_la_pedagogie(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    res = client_admin.get(f"/api/notes/saisie-groupee/?classe={monde.classe.id}&module={monde.module.id}")
    assert res.status_code == 200 and res.data[0]["etudiant_id"] == etudiant.id

    res = _saisie(client_admin, monde, etudiant, 24, 49)
    assert res.status_code == 200, res.data
    note = Note.objects.get(etudiant=etudiant, module=monde.module)
    assert note.note_finale == Decimal("73.00")
    assert note.note_sur_20 == Decimal("14.60")
    assert note.validee is False
    assert Note.objects.filter(etudiant=etudiant).count() == 1  # pas de doublon créé


def test_note_au_dessus_du_plafond_signalee_sans_erreur_serveur(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    res = _saisie(client_admin, monde, etudiant, 35, 40)  # CC plafonné à 30 par défaut
    assert res.status_code == 200
    assert res.data["warnings"]
    assert Note.objects.get(etudiant=etudiant).note_cc is None


def test_lecture_seule_ne_peut_pas_saisir(monde):
    creer_role("lecteur", pedagogie="lecture")
    lecteur = creer_utilisateur(role="lecteur")
    etudiant = monde.nouvel_etudiant()
    assert _saisie(client_api(lecteur), monde, etudiant, 10, 20).status_code == 403


def test_visibilite_etudiant_apres_validation(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    _saisie(client_admin, monde, etudiant, 20, 40)
    client_etu = client_api(etudiant.user)

    assert client_etu.get("/api/notes/me/").data == []  # pas encore validée

    res = client_admin.post("/api/notes/valider/", {"classe_id": monde.classe.id, "module_id": monde.module.id},
                            format="json")
    assert res.status_code == 200 and res.data["validees"] == 1
    notes = client_etu.get("/api/notes/me/").data
    assert len(notes) == 1 and notes[0]["note_finale"] == Decimal("60.00")

    # Toute nouvelle saisie masque à nouveau la note jusqu'à re-validation
    _saisie(client_admin, monde, etudiant, 25, 40)
    assert client_etu.get("/api/notes/me/").data == []


def test_releve_de_notes(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    autre = monde.nouvel_etudiant()
    _saisie(client_admin, monde, etudiant, 25, 55)
    client_admin.post("/api/notes/valider/", {"classe_id": monde.classe.id}, format="json")

    res = client_api(etudiant.user).get(f"/api/notes/{etudiant.id}/releve-notes/")
    assert res.status_code == 200
    assert res.data["resume"]["moyenne_annuelle"] == 80.0
    assert res.data["resume"]["mention"] == "Très Bien"
    assert res.data["resume"]["effectif"] == 2

    # Un étudiant ne peut pas consulter le relevé d'un autre
    assert client_api(etudiant.user).get(f"/api/notes/{autre.id}/releve-notes/").status_code == 403


def test_liste_des_rattrapages(monde, client_admin):
    faible, bon = monde.nouvel_etudiant(), monde.nouvel_etudiant()
    _saisie(client_admin, monde, faible, 10, 20)
    _saisie(client_admin, monde, bon, 25, 50)
    res = client_admin.get(f"/api/notes/rattrapages/?classe={monde.classe.id}")
    assert [r["etudiant_id"] for r in res.data] == [faible.id]


def test_changement_des_pourcentages_recalcule_les_notes(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    _saisie(client_admin, monde, etudiant, 30, 70)  # 100/100
    params = ParametresGlobaux.get_parametres()
    params.pourcentage_cc, params.pourcentage_sn = 40, 60
    params.save()
    note = Note.objects.get(etudiant=etudiant)
    assert (note.note_cc, note.note_sn, note.note_finale) == (Decimal("40.00"), Decimal("60.00"), Decimal("100.00"))


class TestPortailFormateur:
    def test_le_formateur_saisit_les_notes_de_ses_classes(self, monde):
        formateur = monde.nouveau_formateur()
        Affectation.objects.create(enseignant=formateur, module=monde.module, classe=monde.classe)
        etudiant = monde.nouvel_etudiant()
        client = client_api(formateur.user)

        classes = client.get("/api/formateurs/portal/mes-classes/").data
        assert classes[0]["classe_id"] == monde.classe.id and classes[0]["effectif"] == 1

        res = client.post("/api/formateurs/portal/saisir-notes/", {"notes": [{
            "etudiant_id": etudiant.id, "module_id": monde.module.id, "classe_id": monde.classe.id,
            "note_cc": 20, "note_sn": 45,
        }]}, format="json")
        assert res.status_code == 200 and not res.data["errors"]
        note = Note.objects.get(etudiant=etudiant, module=monde.module)
        assert note.note_finale == Decimal("65.00") and note.validee is False

    def test_le_formateur_ne_peut_pas_valider_ni_utiliser_l_api_admin(self, monde):
        formateur = monde.nouveau_formateur()
        client = client_api(formateur.user)
        assert client.post("/api/notes/valider/", {}, format="json").status_code == 403
        assert client.get("/api/notes/").status_code == 403
