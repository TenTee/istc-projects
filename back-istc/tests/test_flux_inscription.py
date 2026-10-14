"""
Flux : du candidat à l'étudiant inscrit.

1. Le candidat remplit le formulaire public de pré-inscription (sans compte).
2. L'administration consulte la liste, puis approuve (avec paiement éventuel) ou rejette.
3. L'approbation crée l'étudiant, son compte portail, son inscription et ses paiements.
"""
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from academique.models import PreInscription
from etudiants.models import Etudiant, Inscription
from paiements.models import Bourse, Frais, Paiement, ReductionEtudiant
from smart_back.testing import client_api

pytestmark = pytest.mark.django_db
URL = "/api/v2/pre-inscriptions/"


def _formulaire(monde, **extra):
    data = {
        "nom_candidat": "Ngono", "prenom_candidat": "Alice", "email": "alice@candidat.cm",
        "telephone": "699112233", "date_naissance": "2005-04-12",
        "filiere_souhaitee": monde.filiere.id, "cycle_souhaite": monde.cycle.id,
        "niveau_souhaite": monde.niveau.id, "classe_souhaitee": monde.classe.id,
        "nom_parent": "Ngono Paul", "whatsapp_parent": "677000000",
    }
    data.update(extra)
    return data


def _pdf(nom="acte.pdf"):
    return SimpleUploadedFile(nom, b"%PDF-1.4 test", content_type="application/pdf")


class TestFormulairePublic:
    def test_les_listes_du_formulaire_sont_publiques(self, monde, client_anonyme):
        for url in ("/api/v2/filieres/", "/api/v2/cycles/", "/api/v2/levels/", "/api/v2/classes/"):
            assert client_anonyme.get(url).status_code == 200, url

    def test_envoi_avec_documents(self, monde, client_anonyme):
        data = _formulaire(monde, acte_naissance=_pdf(), photo=SimpleUploadedFile("p.png", b"img", content_type="image/png"))
        res = client_anonyme.post(URL, data, format="multipart")
        assert res.status_code == 201, res.data
        pre = PreInscription.objects.get(email="alice@candidat.cm")
        assert pre.statut == "EN_ATTENTE"
        assert pre.annee_academique == monde.annee
        assert {d.type_document for d in pre.documents.all()} == {"Acte de naissance", "Photo d'identité"}

    def test_fichier_dangereux_refuse(self, monde, client_anonyme):
        data = _formulaire(monde, cni=SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream"))
        assert client_anonyme.post(URL, data, format="multipart").status_code == 400
        assert not PreInscription.objects.exists()

    def test_doublon_en_attente_refuse(self, monde, client_anonyme):
        assert client_anonyme.post(URL, _formulaire(monde), format="json").status_code == 201
        res = client_anonyme.post(URL, _formulaire(monde, telephone="699999999"), format="json")
        assert res.status_code == 400
        assert "email" in res.data

    def test_la_liste_des_preinscriptions_n_est_pas_publique(self, client_anonyme):
        assert client_anonyme.get(URL).status_code == 401


class TestTraitementAdministratif:
    def _pre(self, monde, **extra):
        client_api().post(URL, _formulaire(monde, **extra), format="json")
        return PreInscription.objects.latest("id")

    def test_approbation_cree_etudiant_compte_inscription(self, monde, client_admin):
        pre = self._pre(monde)
        res = client_admin.post(f"{URL}{pre.id}/approve/", {}, format="json")
        assert res.status_code == 200, res.data

        etudiant = Etudiant.objects.get(email="alice@candidat.cm")
        assert etudiant.nom == "Ngono Alice"
        assert etudiant.statut == "Inscrit"
        assert etudiant.matricule.endswith("-0001")
        assert etudiant.user.role == "etudiant" and etudiant.initial_password
        inscription = Inscription.objects.get(etudiant=etudiant)
        assert inscription.classe == monde.classe
        assert inscription.annee_academique_ref == monde.annee
        assert not PreInscription.objects.filter(pk=pre.pk).exists()

    def test_approbation_avec_paiements_verses(self, monde, client_admin):
        Frais.objects.create(classe=monde.classe, libelle="Frais d'inscription", montant=Decimal("25000"))
        Frais.objects.create(classe=monde.classe, libelle="Scolarité", montant=Decimal("300000"))
        pre = self._pre(monde)
        res = client_admin.post(f"{URL}{pre.id}/approve/", {
            "montant_inscription_verse": "25000", "montant_formation_verse": "100000",
        }, format="json")
        assert res.status_code == 200, res.data
        etudiant = Etudiant.objects.get(email="alice@candidat.cm")
        paiements = {p.paiement_type: p for p in Paiement.objects.filter(etudiant=etudiant)}
        assert paiements["INSCRIPTION"].montant_paye == Decimal("25000")
        assert paiements["FORMATION"].solde_restant == Decimal("200000")

    def test_approbation_avec_bourse(self, monde, client_admin):
        Frais.objects.create(classe=monde.classe, libelle="Scolarité", montant=Decimal("300000"))
        Bourse.objects.create(code="EXCEL-2026", montant=Decimal("50000"))
        pre = self._pre(monde)
        res = client_admin.post(f"{URL}{pre.id}/approve/", {"type_reduction": "BOURSE", "bourse_code": "excel-2026"},
                                format="json")
        assert res.status_code == 200, res.data
        bourse = Bourse.objects.get(code="EXCEL-2026")
        assert bourse.est_utilisee and bourse.etudiant_beneficiaire.email == "alice@candidat.cm"
        assert ReductionEtudiant.objects.get(etudiant=bourse.etudiant_beneficiaire).montant_reduction == Decimal("50000")
        # Une bourse ne sert qu'une fois
        pre2 = self._pre(monde, email="bob@candidat.cm", telephone="699445566")
        res = client_admin.post(f"{URL}{pre2.id}/approve/", {"type_reduction": "BOURSE", "bourse_code": "EXCEL-2026"},
                                format="json")
        assert res.status_code == 400

    def test_rejet_supprime_la_preinscription(self, monde, client_admin):
        pre = self._pre(monde)
        assert client_admin.post(f"{URL}{pre.id}/reject/").status_code == 200
        assert not PreInscription.objects.exists()
        assert not Etudiant.objects.exists()

    def test_un_etudiant_ne_peut_pas_traiter_les_preinscriptions(self, monde):
        pre = self._pre(monde)
        etudiant = monde.nouvel_etudiant()
        client = client_api(etudiant.user)
        assert client.get(URL).status_code == 403
        assert client.post(f"{URL}{pre.id}/approve/", {}, format="json").status_code == 403


class TestInscriptionDirecte:
    def test_ajout_d_un_etudiant_par_le_secretariat(self, monde, client_admin):
        res = client_admin.post("/api/etudiants/", {
            "nom": "Mbarga Eric", "contact": "690000001", "email": "eric@ecole.cm",
            "filiere_id": monde.filiere.id, "classe_id": monde.classe.id,
        }, format="json")
        assert res.status_code == 201, res.data
        etudiant = Etudiant.objects.get(email="eric@ecole.cm")
        assert etudiant.inscriptions.get().classe == monde.classe
        assert res.data["username"] and res.data["initial_password"]

    def test_mot_de_passe_initial_non_modifiable(self, monde, client_admin):
        etudiant = monde.nouvel_etudiant()
        ancien = etudiant.initial_password
        client_admin.patch(f"/api/etudiants/{etudiant.id}/", {"initial_password": "pirate"}, format="json")
        etudiant.refresh_from_db()
        assert etudiant.initial_password == ancien


def test_approbation_avec_reduction_de_10_pourcent(monde, client_admin):
    """La réduction de 10 % est appliquée sur les tranches de formation de la classe."""
    from datetime import date, timedelta
    from paiements.models import ClassePaymentInstallment, ClassePaymentSchedule, StudentPaymentPlan

    schedule = ClassePaymentSchedule.objects.create(classe=monde.classe, total_amount=Decimal("400000"))
    for i in range(1, 5):
        ClassePaymentInstallment.objects.create(schedule=schedule, order=i, label=f"Tranche {i}",
                                                due_date=date.today() + timedelta(days=30 * i),
                                                amount_due=Decimal("100000"))
    client_api().post(URL, _formulaire(monde), format="json")
    pre = PreInscription.objects.latest("id")
    res = client_admin.post(f"{URL}{pre.id}/approve/", {"type_reduction": "PERCENT_10"}, format="json")
    assert res.status_code == 200, res.data
    plan = StudentPaymentPlan.objects.get(etudiant__email="alice@candidat.cm")
    montants = list(plan.installments.order_by("order").values_list("amount_due", flat=True))
    # 40 000 FCFA de réduction déduits en partant de la dernière tranche
    assert montants == [Decimal("100000"), Decimal("100000"), Decimal("100000"), Decimal("60000")]
    assert plan.total_amount == Decimal("360000")
