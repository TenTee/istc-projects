"""
Flux : scolarité (frais, paiements, échéanciers, suivi).

1. La finance configure les frais d'une classe (inscription + scolarité).
2. Elle enregistre les paiements des étudiants ; le solde restant est calculé.
3. Un échéancier (plan) répartit la scolarité en tranches ; chaque paiement est imputé.
4. Le suivi (aggregated), le tableau de bord et le portail étudiant affichent les mêmes chiffres.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from paiements.models import (
    FiliereInstallmentTemplate, FilierePaymentPolicy, Frais, ReductionEtudiant, StudentPaymentPlan,
)
from smart_back.testing import client_api

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


def test_configuration_des_frais_par_l_api(monde, client_admin):
    res = client_admin.post("/api/v2/frais/", {"classe": monde.classe.id, "libelle": "Frais d'inscription",
                                              "montant": "25000"}, format="json")
    assert res.status_code == 201, res.data
    # Un même libellé ne peut pas être défini deux fois pour une classe
    res = client_admin.post("/api/v2/frais/", {"classe": monde.classe.id, "libelle": "Frais d'inscription",
                                              "montant": "30000"}, format="json")
    assert res.status_code == 400


def test_paiements_successifs_et_solde(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    res = _payer(client_admin, etudiant, 150000, frais=frais["scolarite"], moyen="orange_money")
    assert res.status_code == 201, res.data
    assert Decimal(res.data["solde_restant"]) == Decimal("250000.00")
    res = _payer(client_admin, etudiant, 100000, frais=frais["scolarite"])
    assert Decimal(res.data["solde_restant"]) == Decimal("150000.00")
    assert res.data["filiere"] == monde.filiere.id  # déduite de l'étudiant


def test_suivi_des_paiements(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    _payer(client_admin, etudiant, 25000, type_="INSCRIPTION", frais=frais["inscription"])
    _payer(client_admin, etudiant, 100000, frais=frais["scolarite"])
    ligne = next(r for r in client_admin.get("/api/paiements/aggregated/").data if r["etudiant"] == etudiant.id)
    assert Decimal(ligne["montant_du"]) == Decimal("425000")
    assert Decimal(ligne["montant_paye_total"]) == Decimal("125000")
    assert Decimal(ligne["solde_restant_inscription"]) == 0
    assert Decimal(ligne["solde_restant_formation"]) == Decimal("300000")


def test_portail_etudiant_et_suivi_coherents(monde, client_admin, frais):
    etudiant = monde.nouvel_etudiant()
    ReductionEtudiant.objects.create(etudiant=etudiant, type_reduction="LIBRE_FORMATION", target="FORMATION",
                                     montant_reduction=Decimal("40000"))
    _payer(client_admin, etudiant, 60000, frais=frais["scolarite"])

    portail = client_api(etudiant.user).get("/api/paiements/me/").data
    suivi = next(r for r in client_admin.get("/api/paiements/aggregated/").data if r["etudiant"] == etudiant.id)
    assert portail["formation"]["du"] == float(suivi["montant_du_formation"]) == 360000.0
    assert portail["formation"]["reste"] == float(suivi["solde_restant_formation"]) == 300000.0


def test_echeancier_en_quatre_tranches(monde, client_admin, frais):
    policy = FilierePaymentPolicy.objects.create(filiere=monde.filiere, four_installments_enabled=True)
    debut = date.today() + timedelta(days=30)
    for i in range(1, 5):
        FiliereInstallmentTemplate.objects.create(policy=policy, order=i, label=f"Tranche {i}",
                                                  due_date=debut + timedelta(days=30 * i), amount_due=Decimal("100000"))
    etudiant = monde.nouvel_etudiant()
    res = client_admin.post("/api/paiements/plans/", {
        "etudiant": etudiant.id, "mode": "FOUR_INSTALLMENTS", "total_amount": "400000",
    }, format="json")
    assert res.status_code == 201, res.data
    plan = StudentPaymentPlan.objects.get(etudiant=etudiant)
    assert plan.installments.count() == 4

    # 150 000 FCFA : tranche 1 payée, tranche 2 partiellement
    _payer(client_admin, etudiant, 150000, frais=frais["scolarite"])
    t1, t2 = plan.installments.order_by("order")[:2]
    assert (t1.status, t2.status, t2.amount_paid) == ("PAID", "PARTIAL", Decimal("50000"))


def test_alertes_d_echeance(monde, client_admin, frais):
    policy = FilierePaymentPolicy.objects.create(filiere=monde.filiere, four_installments_enabled=True)
    for i in range(1, 5):
        FiliereInstallmentTemplate.objects.create(policy=policy, order=i, label=f"T{i}",
                                                  due_date=date.today() + timedelta(days=-5 + 60 * (i - 1)),
                                                  amount_due=Decimal("100000"))
    etudiant = monde.nouvel_etudiant()
    client_admin.post("/api/paiements/plans/", {"etudiant": etudiant.id, "mode": "FOUR_INSTALLMENTS",
                                                "total_amount": "400000"}, format="json")
    alertes = client_admin.get("/api/paiements/alerts/").data
    assert len(alertes) == 1 and alertes[0]["severity"] == "high"
    tableau = client_admin.get("/api/paiements/dashboard/").data
    assert tableau["nb_echeances_retard"] == 1


def test_l_etudiant_ne_voit_pas_les_paiements_des_autres(monde):
    etudiant = monde.nouvel_etudiant()
    client = client_api(etudiant.user)
    assert client.get("/api/paiements/").status_code == 403
    assert client.get("/api/paiements/aggregated/").status_code == 403
    assert client.get("/api/paiements/me/").status_code == 200


def test_le_portail_affiche_l_echeancier_de_la_classe(monde, client_admin):
    """Sans échéancier personnel, l'étudiant voit l'échéancier de sa classe (comme l'administration)."""
    from paiements.models import ClassePaymentInstallment, ClassePaymentSchedule
    sch = ClassePaymentSchedule.objects.create(classe=monde.classe, total_amount=Decimal("200000"))
    for i in (1, 2):
        ClassePaymentInstallment.objects.create(schedule=sch, order=i, label=f"Tranche {i}",
                                                due_date=date.today() + timedelta(days=30 * i),
                                                amount_due=Decimal("100000"))
    Frais.objects.create(classe=monde.classe, libelle="Tranche 1", montant=Decimal("100000"))
    Frais.objects.create(classe=monde.classe, libelle="Tranche 2", montant=Decimal("100000"))
    etudiant = monde.nouvel_etudiant()
    _payer(client_admin, etudiant, 120000, frais=Frais.objects.get(libelle="Tranche 1"))
    echeances = client_api(etudiant.user).get("/api/paiements/me/").data["echeances"]
    assert [e["label"] for e in echeances] == ["Tranche 1", "Tranche 2"]
    assert echeances[0]["status"] == "PAID"
    assert Decimal(str(echeances[1]["amount_paid"])) == Decimal("20000")
