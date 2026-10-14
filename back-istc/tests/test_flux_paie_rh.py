"""
Flux : paie du personnel et des formateurs, congés.

Paie : primes / retenues / avances → génération de la campagne du mois → validation →
paiement (bulletins payés, dépenses créées, avances remboursées).
Congés : demande → acceptation (solde débité) → refus (solde rendu).
"""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType

from conges.models import Conge
from depenses.models import Depense
from paie.models import AvanceSalaire, BulletinPaie, CampagnePaie, Prime, Retenue
from personnels.models import Personnel

pytestmark = pytest.mark.django_db


def _ct(obj):
    return ContentType.objects.get_for_model(obj)


class TestPaie:
    def test_campagne_personnel_complete(self, monde, client_admin):
        agent = monde.nouveau_personnel(salaire=Decimal("200000"))
        Prime.objects.create(beneficiaire_content_type=_ct(agent), beneficiaire_object_id=agent.id,
                             type_prime="transport", montant=Decimal("20000"))
        Retenue.objects.create(beneficiaire_content_type=_ct(agent), beneficiaire_object_id=agent.id,
                               type_retenue="cnps", montant=Decimal("8400"))
        AvanceSalaire.objects.create(beneficiaire_content_type=_ct(agent), beneficiaire_object_id=agent.id,
                                     montant_total=Decimal("60000"), nombre_echeances=3)

        res = client_admin.post("/api/paie/campagnes/generer/", {"mois": 9, "annee": 2026,
                                                               "type_beneficiaire": "personnel"}, format="json")
        assert res.status_code == 201, res.data
        bulletin = BulletinPaie.objects.get(beneficiaire_object_id=agent.id, beneficiaire_content_type=_ct(agent))
        # 200 000 + 20 000 de prime − 8 400 CNPS − 20 000 d'échéance d'avance
        assert bulletin.salaire_net == Decimal("191600.00")

        campagne = CampagnePaie.objects.get(pk=res.data["id"])
        assert client_admin.post(f"/api/paie/campagnes/{campagne.id}/payer/").status_code == 400  # pas validée
        assert client_admin.post(f"/api/paie/campagnes/{campagne.id}/valider/").status_code == 200
        assert client_admin.post(f"/api/paie/campagnes/{campagne.id}/payer/").status_code == 200

        campagne.refresh_from_db()
        bulletin.refresh_from_db()
        assert campagne.statut == "payee" and bulletin.statut == "paye"
        assert Depense.objects.filter(montant=Decimal("191600.00")).exists()
        assert AvanceSalaire.objects.get().montant_rembourse == Decimal("20000")
        # Une campagne payée ne peut plus être supprimée (dépenses déjà enregistrées)
        assert client_admin.delete(f"/api/paie/campagnes/{campagne.id}/").status_code == 400
        assert CampagnePaie.objects.filter(pk=campagne.pk).exists()

    def test_suppression_d_une_campagne_non_payee(self, monde, client_admin):
        monde.nouveau_personnel()
        res = client_admin.post("/api/paie/campagnes/generer/", {"mois": 11, "annee": 2026,
                                                               "type_beneficiaire": "personnel"}, format="json")
        assert client_admin.delete(f"/api/paie/campagnes/{res.data['id']}/").status_code == 204
        assert not BulletinPaie.objects.filter(mois=11).exists()

    def test_vacataire_sans_heures_non_paye_et_permanent_paye(self, monde, client_admin):
        permanent = monde.nouveau_formateur(salaire=Decimal("300000"))
        vacataire = monde.nouveau_formateur(vacataire=True)
        res = client_admin.post("/api/paie/campagnes/generer/", {"mois": 9, "annee": 2026,
                                                               "type_beneficiaire": "formateur"}, format="json")
        assert res.status_code == 201
        payes = set(BulletinPaie.objects.values_list("beneficiaire_object_id", flat=True))
        assert permanent.id in payes and vacataire.id not in payes

    def test_heures_saisies_manuellement_pour_un_vacataire(self, monde, client_admin):
        vacataire = monde.nouveau_formateur(vacataire=True, taux_horaire=Decimal("4000"))
        client_admin.post("/api/paie/campagnes/generer/", {
            "mois": 9, "annee": 2026, "type_beneficiaire": "formateur",
            "heures_formateurs": [{"formateur_id": vacataire.id, "heures": 12}],
        }, format="json")
        bulletin = BulletinPaie.objects.get(beneficiaire_object_id=vacataire.id)
        assert bulletin.heures_travaillees == Decimal("12") and bulletin.salaire_base == Decimal("48000.00")

    def test_une_seule_campagne_par_mois_et_par_type(self, monde, client_admin):
        monde.nouveau_personnel()
        data = {"mois": 10, "annee": 2026, "type_beneficiaire": "personnel"}
        assert client_admin.post("/api/paie/campagnes/generer/", data, format="json").status_code == 201
        assert client_admin.post("/api/paie/campagnes/generer/", data, format="json").status_code == 400

    def test_prime_ponctuelle_limitee_a_sa_periode(self, monde, client_admin):
        agent = monde.nouveau_personnel(salaire=Decimal("100000"))
        Prime.objects.create(beneficiaire_content_type=_ct(agent), beneficiaire_object_id=agent.id,
                             type_prime="rendement", montant=Decimal("15000"), est_permanente=False,
                             date_debut=date(2026, 7, 1), date_fin=date(2026, 7, 31))
        client_admin.post("/api/paie/campagnes/generer/", {"mois": 7, "annee": 2026, "type_beneficiaire": "personnel"},
                          format="json")
        client_admin.post("/api/paie/campagnes/generer/", {"mois": 8, "annee": 2026, "type_beneficiaire": "personnel"},
                          format="json")
        juillet, aout = (BulletinPaie.objects.get(mois=m) for m in (7, 8))
        assert juillet.total_primes == Decimal("15000") and aout.total_primes == 0


class TestConges:
    @pytest.fixture
    def agent(self):
        return Personnel.objects.create(nom="Agent", contact="1", date_embauche=date(2020, 1, 6),
                                        solde_conges_initial=10)

    def test_demande_puis_acceptation_puis_refus(self, agent, client_admin):
        res = client_admin.post("/api/conges/", {"personnel_id": agent.id, "date_debut": "2026-11-02",
                                                 "date_fin": "2026-11-06", "type_conge": "annuel"}, format="json")
        assert res.status_code == 201, res.data
        conge_id = res.data["id"]
        agent.refresh_from_db()
        assert agent.solde_conges_restant == 10  # une demande ne débite rien

        assert client_admin.patch(f"/api/conges/{conge_id}/", {"statut": "accepte"}, format="json").status_code == 200
        agent.refresh_from_db()
        assert agent.solde_conges_restant == 5

        client_admin.patch(f"/api/conges/{conge_id}/", {"statut": "refuse"}, format="json")
        agent.refresh_from_db()
        assert agent.solde_conges_restant == 10

    def test_suppression_d_un_conge_accepte_rend_le_solde(self, agent, client_admin):
        conge = Conge.objects.create(personnel=agent, date_debut=date(2026, 11, 2), date_fin=date(2026, 11, 3),
                                     type_conge="annuel", statut="accepte")
        agent.refresh_from_db()
        assert agent.solde_conges_restant == 8
        assert client_admin.delete(f"/api/conges/{conge.id}/").status_code == 204
        agent.refresh_from_db()
        assert agent.solde_conges_restant == 10

    def test_personnel_recent_non_eligible(self, client_admin):
        nouveau = Personnel.objects.create(nom="Nouveau", contact="2", date_embauche=date.today(), solde_conges_initial=10)
        res = client_admin.post("/api/conges/", {"personnel_id": nouveau.id, "date_debut": "2026-11-02",
                                                 "date_fin": "2026-11-03", "type_conge": "annuel"}, format="json")
        assert res.status_code == 400

    def test_periode_uniquement_week_end(self, agent, client_admin):
        res = client_admin.post("/api/conges/", {"personnel_id": agent.id, "date_debut": "2026-11-07",
                                                 "date_fin": "2026-11-08", "type_conge": "annuel"}, format="json")
        assert res.status_code == 400
