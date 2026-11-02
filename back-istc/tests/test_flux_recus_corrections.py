"""
Flux : reçus et factures PDF, correction et suppression des paiements.

1. Chaque paiement reçoit un numéro de reçu (REC-AAAA-NNNNNN) et garde qui l'a saisi.
2. Le reçu PDF d'un paiement et la facture d'un étudiant se téléchargent (administration et portail).
3. La finance corrige ou supprime un paiement avec un motif : soldes et échéancier sont
   recalculés, et l'opération est inscrite au journal.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from paiements.documents_pdf import montant_en_lettres, nombre_en_lettres
from paiements.models import (
    FiliereInstallmentTemplate, FilierePaymentPolicy, Frais, JournalPaiement, Paiement, StudentPaymentPlan,
)
from smart_back.testing import client_api, creer_role, creer_utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def frais(monde):
    return {
        "inscription": Frais.objects.create(classe=monde.classe, libelle="Frais d'inscription", montant=Decimal("25000")),
        "scolarite": Frais.objects.create(classe=monde.classe, libelle="Scolarité", montant=Decimal("400000")),
    }


def _payer(client, etudiant, montant, type_="FORMATION", frais=None, moyen="cash"):
    data = {"etudiant": etudiant.id, "paiement_type": type_, "montant_paye": str(montant), "moyen_paiement": moyen}
    if frais is not None:
        data["frais"] = frais.id
    return client.post("/api/paiements/", data, format="json")


def _plan_quatre_tranches(monde, client, etudiant):
    policy = FilierePaymentPolicy.objects.create(filiere=monde.filiere, four_installments_enabled=True)
    debut = date.today() + timedelta(days=30)
    for i in range(1, 5):
        FiliereInstallmentTemplate.objects.create(policy=policy, order=i, label=f"Tranche {i}",
                                                  due_date=debut + timedelta(days=30 * i), amount_due=Decimal("100000"))
    res = client.post("/api/paiements/plans/", {"etudiant": etudiant.id, "mode": "FOUR_INSTALLMENTS",
                                                "total_amount": "400000"}, format="json")
    assert res.status_code == 201, res.data
    return StudentPaymentPlan.objects.get(etudiant=etudiant)


def _est_un_pdf(res):
    contenu = b"".join(res.streaming_content) if getattr(res, "streaming", False) else res.content
    return res["Content-Type"] == "application/pdf" and contenu.startswith(b"%PDF") and len(contenu) > 1500


# --------------------------------------------------------------------------- montants en lettres

@pytest.mark.parametrize("n, texte", [
    (21, "vingt et un"), (71, "soixante et onze"), (80, "quatre-vingts"), (81, "quatre-vingt-un"),
    (200, "deux cents"), (201, "deux cent un"), (1000, "mille"), (80000, "quatre-vingt mille"),
    (200000, "deux cent mille"), (250500, "deux cent cinquante mille cinq cents"),
    (1200000, "un million deux cent mille"), (200000000, "deux cents millions"),
])
def test_nombre_en_lettres(n, texte):
    assert nombre_en_lettres(n) == texte


def test_montant_en_lettres():
    assert montant_en_lettres(Decimal("150000.00")) == "Cent cinquante mille francs CFA"


# --------------------------------------------------------------------------- reçus et factures

def test_numero_de_recu_et_auteur(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    res = _payer(client_admin, etudiant, 150000, frais=frais["scolarite"])
    assert res.status_code == 201, res.data
    annee = timezone.now().year
    assert res.data["numero_recu"] == f"REC-{annee}-{res.data['id']:06d}"
    assert res.data["enregistre_par_nom"]
    assert JournalPaiement.objects.filter(action="creation", numero_recu=res.data["numero_recu"]).exists()


def test_recu_et_facture_pdf(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    _plan_quatre_tranches(monde, client_admin, etudiant)
    _payer(client_admin, etudiant, 25000, type_="INSCRIPTION", frais=frais["inscription"])
    pid = _payer(client_admin, etudiant, 150000, frais=frais["scolarite"], moyen="orange_money").data["id"]
    res = client_admin.get(f"/api/paiements/{pid}/recu/")
    assert res.status_code == 200 and _est_un_pdf(res)
    assert "attachment" in res["Content-Disposition"] and "REC-" in res["Content-Disposition"]
    assert "inline" in client_admin.get(f"/api/paiements/{pid}/recu/?telecharger=0")["Content-Disposition"]
    res = client_admin.get(f"/api/paiements/facture/{etudiant.id}/")
    assert res.status_code == 200 and _est_un_pdf(res)


def test_facture_sans_paiement_ni_classe(monde, client_admin):
    etudiant = monde.nouvel_etudiant(inscrire=False)
    res = client_admin.get(f"/api/paiements/facture/{etudiant.id}/")
    assert res.status_code == 200 and _est_un_pdf(res)


def test_documents_lisibles_par_la_scolarite_pas_sans_droit(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    pid = _payer(client_admin, etudiant, 50000, frais=frais["scolarite"]).data["id"]
    creer_role("scolarite_lecture", etudiants="lecture")
    creer_role("logistique", logistique="ecriture")
    lecteur = client_api(creer_utilisateur(role="scolarite_lecture"))
    assert lecteur.get(f"/api/paiements/{pid}/recu/").status_code == 200
    assert lecteur.get(f"/api/paiements/facture/{etudiant.id}/").status_code == 200
    logistique = client_api(creer_utilisateur(role="logistique"))
    assert logistique.get(f"/api/paiements/{pid}/recu/").status_code == 403


def test_portail_etudiant_ses_recus_et_sa_facture(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    autre = monde.nouvel_etudiant()
    pid = _payer(client_admin, etudiant, 50000, frais=frais["scolarite"]).data["id"]
    pid_autre = _payer(client_admin, autre, 50000, frais=frais["scolarite"]).data["id"]
    client = client_api(etudiant.user)
    resume = client.get("/api/paiements/me/").data
    assert [p["id"] for p in resume["paiements"]] == [pid]
    assert resume["paiements"][0]["numero_recu"].startswith("REC-")
    assert _est_un_pdf(client.get(f"/api/paiements/me/recus/{pid}/"))
    assert client.get(f"/api/paiements/me/recus/{pid_autre}/").status_code == 404
    assert _est_un_pdf(client.get("/api/paiements/me/facture/"))
    # les routes d'administration restent fermées au portail
    assert client.get(f"/api/paiements/{pid}/recu/").status_code == 403
    assert client.get(f"/api/paiements/facture/{etudiant.id}/").status_code == 403


# --------------------------------------------------------------------------- corrections

def test_correction_recalcule_soldes_et_echeancier(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    plan = _plan_quatre_tranches(monde, client_admin, etudiant)
    p1 = _payer(client_admin, etudiant, 150000, frais=frais["scolarite"]).data
    p2 = _payer(client_admin, etudiant, 100000, frais=frais["scolarite"]).data
    assert Decimal(p2["solde_restant"]) == Decimal("150000")

    res = client_admin.patch(f"/api/paiements/{p1['id']}/", {"montant_paye": "50000", "moyen_paiement": "virement",
                                                             "motif": "Erreur de saisie du montant"}, format="json")
    assert res.status_code == 200, res.data
    assert Decimal(res.data["solde_restant"]) == Decimal("350000")
    assert res.data["numero_recu"] == p1["numero_recu"]  # le numéro ne change pas
    assert Decimal(Paiement.objects.get(pk=p2["id"]).solde_restant) == Decimal("250000")
    payes = [t.amount_paid for t in plan.installments.order_by("order")]
    assert payes == [Decimal("100000"), Decimal("50000"), 0, 0]

    entree = JournalPaiement.objects.get(action="modification")
    assert entree.motif == "Erreur de saisie du montant"
    assert entree.avant["montant_paye"] == "150000.00" and entree.apres["montant_paye"] == "50000.00"
    assert entree.utilisateur_nom


def test_correction_de_la_date(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    pid = _payer(client_admin, etudiant, 50000, frais=frais["scolarite"]).data["id"]
    hier = (timezone.now() - timedelta(days=1)).replace(microsecond=0)
    res = client_admin.patch(f"/api/paiements/{pid}/", {"date_paiement": hier.isoformat(),
                                                        "motif": "Paiement reçu la veille"}, format="json")
    assert res.status_code == 200, res.data
    assert Paiement.objects.get(pk=pid).date_paiement == hier
    demain = timezone.now() + timedelta(days=2)
    res = client_admin.patch(f"/api/paiements/{pid}/", {"date_paiement": demain.isoformat(),
                                                        "motif": "Date dans le futur"}, format="json")
    assert res.status_code == 400 and "date_paiement" in res.data


def test_changement_de_type_recalcule_les_deux_groupes(monde, client_admin):
    etudiant = monde.nouvel_etudiant()
    Frais.objects.create(classe=monde.classe, libelle="Frais d'inscription", montant=Decimal("25000"))
    Frais.objects.create(classe=monde.classe, libelle="Scolarité", montant=Decimal("400000"))
    pid = _payer(client_admin, etudiant, 25000, type_="FORMATION").data["id"]  # saisi sur le mauvais type
    res = client_admin.patch(f"/api/paiements/{pid}/", {"paiement_type": "INSCRIPTION",
                                                        "motif": "C'était l'inscription"}, format="json")
    assert res.status_code == 200, res.data
    assert Decimal(res.data["montant_du"]) == Decimal("25000") and Decimal(res.data["solde_restant"]) == 0


def test_motif_obligatoire_et_montant_positif(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    pid = _payer(client_admin, etudiant, 50000, frais=frais["scolarite"]).data["id"]
    assert client_admin.patch(f"/api/paiements/{pid}/", {"montant_paye": "40000"}, format="json").status_code == 400
    assert client_admin.patch(f"/api/paiements/{pid}/", {"montant_paye": "40000", "motif": "ok"},
                              format="json").status_code == 400
    res = client_admin.patch(f"/api/paiements/{pid}/", {"montant_paye": "0", "motif": "Montant nul"}, format="json")
    assert res.status_code == 400 and "montant_paye" in res.data
    assert client_admin.delete(f"/api/paiements/{pid}/").status_code == 400
    assert Paiement.objects.filter(pk=pid, montant_paye=Decimal("50000")).exists()
    assert _payer(client_admin, etudiant, 0, frais=frais["scolarite"]).status_code == 400


def test_un_paiement_ne_change_pas_d_etudiant(monde, client_admin, frais):
    etudiant, autre = monde.nouvel_etudiant(), monde.nouvel_etudiant()
    pid = _payer(client_admin, etudiant, 50000, frais=frais["scolarite"]).data["id"]
    res = client_admin.patch(f"/api/paiements/{pid}/", {"etudiant": autre.id, "motif": "Mauvais étudiant"},
                             format="json")
    assert res.status_code == 400 and "etudiant" in res.data


def test_suppression_recalcule_et_journalise(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    plan = _plan_quatre_tranches(monde, client_admin, etudiant)
    p1 = _payer(client_admin, etudiant, 400000, frais=frais["scolarite"]).data
    plan.refresh_from_db()
    assert plan.status == "COMPLETED"
    p2 = _payer(client_admin, etudiant, 0.5, frais=frais["scolarite"]).data  # doublon saisi par erreur

    res = client_admin.delete(f"/api/paiements/{p1['id']}/?motif=Chèque%20rejeté%20par%20la%20banque")
    assert res.status_code == 204
    assert not Paiement.objects.filter(pk=p1["id"]).exists()
    plan.refresh_from_db()
    assert plan.status == "ACTIVE"
    assert [t.status for t in plan.installments.order_by("order")][0] in ("PARTIAL", "PENDING")
    restant = Paiement.objects.get(pk=p2["id"])
    assert restant.montant_du == Decimal("400000") and restant.solde_restant == Decimal("399999.50")

    entree = JournalPaiement.objects.get(action="suppression")
    assert entree.numero_recu == p1["numero_recu"] and entree.motif == "Chèque rejeté par la banque"
    assert entree.avant["montant_paye"] == "400000.00" and entree.etudiant_id == etudiant.id
    journal = client_admin.get(f"/api/paiements/journal/?etudiant={etudiant.id}").data
    assert [e["action"] for e in journal][:2] == ["suppression", "creation"]


def test_suppression_avec_motif_dans_le_corps(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    pid = _payer(client_admin, etudiant, 50000, frais=frais["scolarite"]).data["id"]
    res = client_admin.delete(f"/api/paiements/{pid}/", {"motif": "Saisi en double"}, format="json")
    assert res.status_code == 204


def test_correction_reservee_a_la_finance_en_ecriture(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    pid = _payer(client_admin, etudiant, 50000, frais=frais["scolarite"]).data["id"]
    creer_role("finance_lecture", finance="lecture", etudiants="ecriture")
    creer_role("caisse", finance="ecriture")
    lecteur = client_api(creer_utilisateur(role="finance_lecture"))
    corps = {"montant_paye": "40000", "motif": "Correction du montant"}
    assert lecteur.patch(f"/api/paiements/{pid}/", corps, format="json").status_code == 403
    assert lecteur.delete(f"/api/paiements/{pid}/?motif=Suppression%20test").status_code == 403
    assert client_api(etudiant.user).delete(f"/api/paiements/{pid}/?motif=Suppression%20test").status_code == 403
    caisse = client_api(creer_utilisateur(role="caisse"))
    assert caisse.patch(f"/api/paiements/{pid}/", corps, format="json").status_code == 200


def test_migration_numerote_les_paiements_existants(monde, frais):
    import importlib

    from django.apps import apps

    etudiant = monde.nouvel_etudiant()
    p = Paiement.objects.create(etudiant=etudiant, frais=frais["scolarite"], montant_paye=Decimal("1000"))
    Paiement.objects.filter(pk=p.pk).update(numero_recu=None)
    migration = importlib.import_module("paiements.migrations.0004_recus_et_journal")
    migration.numeroter_paiements_existants(apps, None)
    p.refresh_from_db()
    assert p.numero_recu == f"REC-{p.date_paiement.year}-{p.pk:06d}"
