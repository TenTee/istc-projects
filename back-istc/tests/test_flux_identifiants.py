"""
Flux : identifiants des comptes.

1. Chacun (personnel, étudiant, formateur) consulte « Mon profil » et change son nom
   d'utilisateur ou son mot de passe (le mot de passe actuel est toujours exigé).
2. Le personnel habilité réinitialise le mot de passe d'un étudiant (droit Étudiants en
   écriture), d'un formateur (droit RH en écriture) ou d'un compte (administrateur) et reçoit
   les identifiants à transmettre.
3. L'approbation d'une pré-inscription renvoie les identifiants du nouveau portail étudiant.
"""
import pytest
from django.contrib.auth import get_user_model

from academique.models import PreInscription
from smart_back.testing import client_api, creer_role, creer_utilisateur
from users.utils import erreurs_mot_de_passe, generer_mot_de_passe

pytestmark = pytest.mark.django_db
User = get_user_model()

ME = "/api/auth/me/"
MDP = "/api/auth/me/mot-de-passe/"
LOGIN = "/api/auth/login/"
ACTUEL = "Ancien-MotDePasse-42"
NOUVEAU = "Nouveau-Secret-2026"


def _avec_mot_de_passe(user, mdp=ACTUEL):
    user.set_password(mdp)
    user.save()
    return user


def _connexion(username, mdp):
    return client_api().post(LOGIN, {"username": username, "password": mdp}, format="json").status_code


# --------------------------------------------------------------------------- outils

def test_mot_de_passe_genere_lisible_et_valide():
    for _ in range(50):
        mdp = generer_mot_de_passe()
        assert len(mdp) == 10
        assert not set(mdp) & set("0O1lI")
        assert any(c.isdigit() for c in mdp) and any(c.isalpha() for c in mdp)
    assert erreurs_mot_de_passe(generer_mot_de_passe()) == []
    assert erreurs_mot_de_passe("123")  # trop court, numérique, courant


# --------------------------------------------------------------------------- Mon profil

class TestMonProfil:
    def test_chaque_type_de_compte_lit_son_profil(self, monde):
        etudiant = monde.nouvel_etudiant()
        formateur = monde.nouveau_formateur()
        for user in (monde.admin, etudiant.user, formateur.user):
            res = client_api(user).get(ME)
            assert res.status_code == 200, (user.role, res.status_code)
            assert res.data["username"] == user.username
            assert res.data["role"] == user.role
            assert "password" not in res.data

    def test_anonyme_refuse(self, client_anonyme):
        assert client_anonyme.get(ME).status_code == 401

    def test_changer_son_nom_d_utilisateur(self, monde):
        etudiant = monde.nouvel_etudiant()
        user = _avec_mot_de_passe(etudiant.user)
        res = client_api(user).patch(ME, {"username": "alice.ngono", "mot_de_passe_actuel": ACTUEL}, format="json")
        assert res.status_code == 200, res.data
        assert res.data["username"] == "alice.ngono"
        assert _connexion("alice.ngono", ACTUEL) == 200

    def test_nom_d_utilisateur_refuse(self, monde):
        user = _avec_mot_de_passe(monde.admin)
        autre = creer_utilisateur(role="admin", username="deja.pris")
        client = client_api(user)
        res = client.patch(ME, {"username": "DEJA.PRIS", "mot_de_passe_actuel": ACTUEL}, format="json")
        assert res.status_code == 400 and "username" in res.data
        res = client.patch(ME, {"username": "avec espace", "mot_de_passe_actuel": ACTUEL}, format="json")
        assert res.status_code == 400 and "username" in res.data
        res = client.patch(ME, {"username": "libre.nom", "mot_de_passe_actuel": "faux"}, format="json")
        assert res.status_code == 400 and "mot_de_passe_actuel" in res.data
        user.refresh_from_db()
        assert user.username != "libre.nom" and autre.username == "deja.pris"

    def test_changer_son_mot_de_passe(self, monde):
        etudiant = monde.nouvel_etudiant()
        assert etudiant.initial_password
        user = _avec_mot_de_passe(etudiant.user)
        res = client_api(user).post(MDP, {"mot_de_passe_actuel": ACTUEL, "nouveau_mot_de_passe": NOUVEAU,
                                          "confirmation": NOUVEAU}, format="json")
        assert res.status_code == 200, res.data
        assert _connexion(user.username, NOUVEAU) == 200
        assert _connexion(user.username, ACTUEL) != 200
        etudiant.refresh_from_db()
        assert not etudiant.initial_password  # le mot de passe provisoire n'est plus affiché

    def test_formateur_change_son_mot_de_passe(self, monde):
        user = _avec_mot_de_passe(monde.nouveau_formateur().user)
        res = client_api(user).post(MDP, {"mot_de_passe_actuel": ACTUEL, "nouveau_mot_de_passe": NOUVEAU,
                                          "confirmation": NOUVEAU}, format="json")
        assert res.status_code == 200, res.data

    @pytest.mark.parametrize("donnees, champ", [
        ({"mot_de_passe_actuel": "faux", "nouveau_mot_de_passe": NOUVEAU, "confirmation": NOUVEAU},
         "mot_de_passe_actuel"),
        ({"mot_de_passe_actuel": ACTUEL, "nouveau_mot_de_passe": NOUVEAU, "confirmation": "autre"}, "confirmation"),
        ({"mot_de_passe_actuel": ACTUEL, "nouveau_mot_de_passe": "password", "confirmation": "password"},
         "nouveau_mot_de_passe"),
        ({"mot_de_passe_actuel": ACTUEL, "nouveau_mot_de_passe": ACTUEL, "confirmation": ACTUEL},
         "nouveau_mot_de_passe"),
    ])
    def test_mot_de_passe_refuse(self, monde, donnees, champ):
        user = _avec_mot_de_passe(monde.admin)
        res = client_api(user).post(MDP, donnees, format="json")
        assert res.status_code == 400 and champ in res.data, res.data
        user.refresh_from_db()
        assert user.check_password(ACTUEL)


# --------------------------------------------------------------------------- réinitialisation

class TestReinitialisation:
    def test_etudiant_par_la_scolarite(self, monde):
        etudiant = monde.nouvel_etudiant()
        ancien = etudiant.initial_password
        creer_role("scolarite", etudiants="ecriture")
        res = client_api(creer_utilisateur(role="scolarite")).post(f"/api/etudiants/{etudiant.id}/reset-password/")
        assert res.status_code == 200, res.data
        assert res.data["username"] == etudiant.user.username
        assert res.data["password"] != ancien and res.data["telephone"] == etudiant.contact
        etudiant.refresh_from_db()
        assert etudiant.initial_password == res.data["password"]
        assert _connexion(etudiant.user.username, res.data["password"]) == 200

    def test_etudiant_refuse_sans_droit_d_ecriture(self, monde):
        etudiant = monde.nouvel_etudiant()
        creer_role("lecteur", etudiants="lecture")
        url = f"/api/etudiants/{etudiant.id}/reset-password/"
        assert client_api(creer_utilisateur(role="lecteur")).post(url).status_code == 403
        assert client_api(monde.nouvel_etudiant().user).post(url).status_code == 403

    def test_formateur_par_les_rh(self, monde):
        formateur = monde.nouveau_formateur()
        creer_role("rh", rh="ecriture")
        res = client_api(creer_utilisateur(role="rh")).post(f"/api/formateurs/{formateur.id}/reset-password/")
        assert res.status_code == 200, res.data
        assert _connexion(formateur.user.username, res.data["password"]) == 200

    def test_formateur_refuse_sans_droit_rh_ou_sans_compte(self, monde, client_admin):
        formateur = monde.nouveau_formateur()
        creer_role("scolarite", etudiants="ecriture")
        url = f"/api/formateurs/{formateur.id}/reset-password/"
        assert client_api(creer_utilisateur(role="scolarite")).post(url).status_code == 403
        sans_compte = monde.nouveau_formateur(avec_compte=False)
        assert client_admin.post(f"/api/formateurs/{sans_compte.id}/reset-password/").status_code == 400

    def test_compte_du_personnel_par_l_administrateur(self, monde, client_admin):
        agent = creer_utilisateur(role="admin")
        res = client_admin.post(f"/api/auth/{agent.id}/reset-password/")
        assert res.status_code == 200, res.data
        assert res.data["password"] == res.data["new_password"]
        assert _connexion(agent.username, res.data["password"]) == 200

    def test_un_superutilisateur_n_est_reinitialise_que_par_un_superutilisateur(self, monde, client_admin):
        chef = User.objects.create_superuser(username="chef", email="chef@test.local", password=ACTUEL)
        assert client_admin.post(f"/api/auth/{chef.id}/reset-password/").status_code == 403
        chef.refresh_from_db()
        assert chef.check_password(ACTUEL)


# --------------------------------------------------------------------------- approbation

def test_approbation_renvoie_les_identifiants(monde, client_admin):
    client_api().post("/api/v2/pre-inscriptions/", {
        "nom_candidat": "Ngono", "prenom_candidat": "Alice", "email": "alice@candidat.cm",
        "telephone": "699112233", "date_naissance": "2005-04-12",
        "filiere_souhaitee": monde.filiere.id, "cycle_souhaite": monde.cycle.id,
        "niveau_souhaite": monde.niveau.id, "classe_souhaitee": monde.classe.id,
        "nom_parent": "Ngono Paul", "whatsapp_parent": "677000000",
    }, format="json")
    pre = PreInscription.objects.latest("id")
    res = client_admin.post(f"/api/v2/pre-inscriptions/{pre.id}/approve/", {}, format="json")
    assert res.status_code == 200, res.data
    ident = res.data["identifiants"]
    assert ident["username"] and ident["password"] and ident["email"] == "alice@candidat.cm"
    assert _connexion(ident["username"], ident["password"]) == 200
