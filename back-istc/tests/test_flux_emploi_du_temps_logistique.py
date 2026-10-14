"""
Flux : emploi du temps (création de créneaux, conflits) et logistique (stock, demandes).
"""
from datetime import time

import pytest
from django.contrib.contenttypes.models import ContentType

from academique.models import AnneeAcademique, Classe
from emploidutemps.models import EmploiDuTemps
from formateurs.models import Formateur
from inventaires.models import Article, Exemplaire, Mouvement

pytestmark = pytest.mark.django_db
EDT = "/api/emploi-du-temps/"


def _creneau(monde, formateur, **extra):
    data = {"classe": monde.classe.id, "module": monde.module.id, "formateur": formateur.id,
            "salle": monde.salle.id, "jour": "Mardi", "heure_debut": "08:00", "heure_fin": "10:00"}
    data.update(extra)
    return data


class TestEmploiDuTemps:
    def test_creation_d_un_creneau(self, monde, client_admin):
        f = monde.nouveau_formateur()
        res = client_admin.post(EDT, _creneau(monde, f), format="json")
        assert res.status_code == 201, res.data
        assert res.data["niveau"] == monde.niveau.id  # déduit de la classe

    @pytest.mark.parametrize("modif, message", [
        ({"heure_debut": "11:30", "heure_fin": "12:30"}, "pause"),
        ({"heure_debut": "10:00", "heure_fin": "09:00"}, "fin"),
        ({"heure_debut": "06:00", "heure_fin": "07:30"}, "créneau"),
    ])
    def test_horaires_invalides(self, monde, client_admin, modif, message):
        f = monde.nouveau_formateur()
        res = client_admin.post(EDT, _creneau(monde, f, **modif), format="json")
        assert res.status_code == 400
        assert message in str(res.data).lower()

    def test_conflits_de_salle_et_de_formateur(self, monde, client_admin):
        from modules.models import Module
        f1, f2 = monde.nouveau_formateur(), monde.nouveau_formateur()
        autre_module = Module.objects.create(nom="Réseaux")
        assert client_admin.post(EDT, _creneau(monde, f1), format="json").status_code == 201
        # Même salle, même heure, autre module
        res = client_admin.post(EDT, _creneau(monde, f2, module=autre_module.id), format="json")
        assert res.status_code == 400 and "salle" in str(res.data).lower()

    def test_l_annee_precedente_ne_bloque_pas(self, monde, client_admin):
        f = monde.nouveau_formateur()
        client_admin.post(EDT, _creneau(monde, f), format="json")
        suivante = AnneeAcademique.objects.create(libelle="2027-2028")
        classe_suivante = Classe.objects.get(niveau=monde.niveau, annee_academique=suivante)
        res = client_admin.post(EDT, _creneau(monde, f, classe=classe_suivante.id), format="json")
        assert res.status_code == 201, res.data

    def test_visible_dans_les_portails(self, monde, client_admin):
        f = monde.nouveau_formateur()
        etudiant = monde.nouvel_etudiant()
        client_admin.post(EDT, _creneau(monde, f), format="json")
        from smart_back.testing import client_api
        assert len(client_api(etudiant.user).get(f"{EDT}me/").data) == 1
        assert len(client_api(f.user).get("/api/formateurs/portal/mon-emploi-du-temps/").data) == 1


class TestLogistique:
    def test_cycle_complet_d_une_demande(self, monde, client_admin):
        res = client_admin.post("/api/inventaires/articles/", {"nom": "Vidéoprojecteur", "categorie": "Autre",
                                                              "quantite_initiale": 2}, format="json")
        assert res.status_code == 201, res.data
        article = Article.objects.get(nom="Vidéoprojecteur")
        assert article.quantite_en_stock == 2

        demandeur = Formateur.objects.create(nom="Demandeur", email="dem@t.local", contact="1")
        res = client_admin.post("/api/demandes/", {
            "objet": "Cours du lundi", "priorite": "normale",
            "demandeur_content_type": ContentType.objects.get_for_model(Formateur).id,
            "demandeur_object_id": demandeur.id,
            "lignes": [{"article": article.id, "quantite_demandee": 1}],
        }, format="json")
        assert res.status_code == 201, res.data
        demande_id = client_admin.get("/api/demandes/").data[0]["id"]

        for etape in ("soumettre", "approuver", "livrer"):
            res = client_admin.post(f"/api/demandes/{demande_id}/{etape}/", {}, format="json")
            assert res.status_code == 200, (etape, res.data)
        assert res.data["statut"] == "livree"
        assert Exemplaire.objects.filter(article=article, statut="en_utilisation").count() == 1
        assert Mouvement.objects.filter(type_mouvement="sortie").count() == 1

    def test_refus_d_une_demande(self, monde, client_admin):
        article = Article.objects.create(nom="Chaise")
        res = client_admin.post("/api/demandes/", {"objet": "Chaises", "lignes": [{"article": article.id,
                                                                                   "quantite_demandee": 4}]},
                                format="json")
        demande_id = client_admin.get("/api/demandes/").data[0]["id"]
        client_admin.post(f"/api/demandes/{demande_id}/soumettre/")
        res = client_admin.post(f"/api/demandes/{demande_id}/refuser/", {"commentaire": "Budget épuisé"}, format="json")
        assert res.status_code == 200 and res.data["statut"] == "refusee"

    def test_livraison_refusee_si_stock_insuffisant(self, monde, client_admin):
        article = Article.objects.create(nom="Tableau blanc")
        client_admin.post(f"/api/inventaires/articles/{article.id}/ajouter_stock/", {"quantite": 1}, format="json")
        client_admin.post("/api/demandes/", {"objet": "Salles", "lignes": [{"article": article.id,
                                                                            "quantite_demandee": 3}]}, format="json")
        demande_id = client_admin.get("/api/demandes/").data[0]["id"]
        client_admin.post(f"/api/demandes/{demande_id}/soumettre/")
        client_admin.post(f"/api/demandes/{demande_id}/approuver/")
        res = client_admin.post(f"/api/demandes/{demande_id}/livrer/")
        assert res.status_code == 400 and "1/3" in res.data["warnings"][0]
        # Rien n'est sorti du stock
        assert Exemplaire.objects.filter(article=article, statut="en_stock").count() == 1
        assert not Mouvement.objects.filter(type_mouvement="sortie").exists()

    def test_reference_unique_apres_suppression(self, client_admin, db):
        from demandes.models import DemandeArticle
        d1 = DemandeArticle.objects.create(objet="A")
        DemandeArticle.objects.create(objet="B")
        d1.delete()
        d3 = DemandeArticle.objects.create(objet="C")  # échouait : référence déjà utilisée
        assert d3.reference

    def test_attribution_et_retour_d_un_exemplaire(self, monde, client_admin):
        article = Article.objects.create(nom="Ordinateur")
        client_admin.post(f"/api/inventaires/articles/{article.id}/ajouter_stock/", {"quantite": 1}, format="json")
        ex = Exemplaire.objects.get(article=article)
        ct = ContentType.objects.get_for_model(Formateur)
        f = Formateur.objects.create(nom="Utilisateur", email="u@t.local", contact="2")
        res = client_admin.post(f"/api/inventaires/exemplaires/{ex.id}/attribuer/",
                                {"attributaire_content_type": ct.id, "attributaire_object_id": f.id}, format="json")
        assert res.status_code == 200
        # déjà attribué : refus
        assert client_admin.post(f"/api/inventaires/exemplaires/{ex.id}/attribuer/",
                                 {"attributaire_content_type": ct.id, "attributaire_object_id": f.id},
                                 format="json").status_code == 400
        assert client_admin.post(f"/api/inventaires/exemplaires/{ex.id}/retourner/", {}, format="json").status_code == 200
        ex.refresh_from_db()
        assert ex.statut == "en_stock"
