"""
Flux : structure académique (universités, départements, filières, spécialités, niveaux, classes, salles).

1. Ajouter : une spécialité avec un type de cycle et un nombre de niveaux génère ses niveaux et
   une classe par niveau et par année académique.
2. Modifier : nom, filière, type de cycle et nombre de niveaux se répercutent automatiquement
   sur les niveaux et les classes (un nom de classe saisi à la main n'est pas écrasé).
3. Supprimer : refusé tant que des données sont rattachées (au lieu d'effacer les étudiants en
   cascade) ; un élément vide part avec ses niveaux et classes.
"""
import pytest

from academique.models import AnneeAcademique, Classe, Cycle, CycleGlobal, Departement, Filiere, Niveau, Specialite
from etudiants.models import Etudiant, Inscription

pytestmark = pytest.mark.django_db
SPEC = "/api/v2/specialites/"


@pytest.fixture
def licence(db):
    return CycleGlobal.objects.create(nom="Licence Pro")


@pytest.fixture
def bts(db):
    return CycleGlobal.objects.create(nom="BTS")


def _creer_specialite(client, monde, cycle, niveaux=3, nom="Développement Web"):
    res = client.post(SPEC, {"filiere": monde.filiere.id, "nom": nom, "type_cycle": cycle.id,
                             "nombre_niveaux": niveaux}, format="json")
    assert res.status_code == 201, res.data
    return res.data


def _noms_classes(specialite_id):
    return sorted(Classe.objects.filter(specialite_id=specialite_id).values_list("nom", flat=True))


def _modifier(client, item, **changements):
    """Comme l'écran : renvoie toute la fiche avec les champs modifiés."""
    payload = dict(item)
    payload.update(changements)
    return client.put(f"{SPEC}{item['id']}/", payload, format="json")


# --------------------------------------------------------------------------- spécialités

def test_creation_genere_niveaux_et_classes(monde, client_admin, licence):
    AnneeAcademique.objects.create(libelle="2027-2028")
    item = _creer_specialite(client_admin, monde, licence, niveaux=2)
    assert item["cycle_nom"] == "Licence Pro" and item["nombre_niveaux"] == 2 and item["type_cycle"] == licence.id
    assert _noms_classes(item["id"]) == [
        "Développement Web Licence Pro 1 (2026-2027)", "Développement Web Licence Pro 1 (2027-2028)",
        "Développement Web Licence Pro 2 (2026-2027)", "Développement Web Licence Pro 2 (2027-2028)",
    ]


def test_modifier_nom_type_et_niveaux(monde, client_admin, licence, bts):
    item = _creer_specialite(client_admin, monde, licence, niveaux=3)
    res = _modifier(client_admin, item, nom="Génie Logiciel", code="GL", type_cycle=bts.id, nombre_niveaux=2)
    assert res.status_code == 200, res.data
    assert (res.data["nom"], res.data["code"], res.data["cycle_nom"], res.data["nombre_niveaux"], res.data["type_cycle"]) \
        == ("Génie Logiciel", "GL", "BTS", 2, bts.id)
    assert sorted(Niveau.objects.filter(cycle__specialite_id=item["id"]).values_list("nom", flat=True)) == ["BTS 1", "BTS 2"]
    assert _noms_classes(item["id"]) == ["Génie Logiciel BTS 1 (2026-2027)", "Génie Logiciel BTS 2 (2026-2027)"]

    res = _modifier(client_admin, res.data, nombre_niveaux=4)
    assert res.status_code == 200 and res.data["nombre_niveaux"] == 4
    assert _noms_classes(item["id"])[-1] == "Génie Logiciel BTS 4 (2026-2027)"


def test_un_nom_de_classe_saisi_a_la_main_est_conserve(monde, client_admin, licence):
    item = _creer_specialite(client_admin, monde, licence, niveaux=1)
    classe = Classe.objects.get(specialite_id=item["id"])
    classe.nom = "Groupe du soir"
    classe.save()
    _modifier(client_admin, item, nom="Web et Mobile")
    classe.refresh_from_db()
    assert classe.nom == "Groupe du soir"


def test_retirer_un_niveau_qui_a_des_inscrits_est_refuse(monde, client_admin, licence):
    item = _creer_specialite(client_admin, monde, licence, niveaux=3)
    niveau3 = Niveau.objects.get(cycle__specialite_id=item["id"], ordre=3)
    etudiant = monde.nouvel_etudiant(inscrire=False)
    Inscription.objects.create(etudiant=etudiant, niveau=niveau3, classe=niveau3.classes.first(),
                               annee_academique=monde.annee.libelle)
    res = _modifier(client_admin, item, nombre_niveaux=2)
    assert res.status_code == 400 and "nombre_niveaux" in res.data and "inscriptions" in str(res.data)
    assert Niveau.objects.filter(cycle__specialite_id=item["id"]).count() == 3
    assert _modifier(client_admin, item, nombre_niveaux=0).status_code == 400


def test_changer_de_filiere(monde, client_admin, licence):
    item = _creer_specialite(client_admin, monde, licence, niveaux=1)
    autre = Filiere.objects.create(departement=monde.filiere.departement, nom="Gestion")
    res = _modifier(client_admin, item, filiere=autre.id)
    assert res.status_code == 200, res.data
    assert set(Classe.objects.filter(specialite_id=item["id"]).values_list("filiere_id", flat=True)) == {autre.id}
    assert set(Cycle.objects.filter(specialite_id=item["id"]).values_list("filiere_id", flat=True)) == {autre.id}

    # Avec des inscrits, la spécialité ne change plus de filière (les étudiants y sont rattachés).
    classe = Classe.objects.get(specialite_id=item["id"])
    Inscription.objects.create(etudiant=monde.nouvel_etudiant(inscrire=False), niveau=classe.niveau, classe=classe,
                               annee_academique=monde.annee.libelle)
    res = _modifier(client_admin, res.data, filiere=monde.filiere.id)
    assert res.status_code == 400 and "filiere" in res.data


def test_modification_sans_champs_de_cycle(monde, client_admin, licence):
    item = _creer_specialite(client_admin, monde, licence, niveaux=2)
    res = client_admin.patch(f"{SPEC}{item['id']}/", {"responsable_nom": "Mme Ndi"}, format="json")
    assert res.status_code == 200 and res.data["nombre_niveaux"] == 2


def test_doublons(monde, client_admin, licence):
    _creer_specialite(client_admin, monde, licence)
    res = client_admin.post(SPEC, {"filiere": monde.filiere.id, "nom": "développement web"}, format="json")
    assert res.status_code == 400 and "spécialité de ce nom" in str(res.data)
    res = client_admin.post("/api/v2/universites-tutelles/", {"nom": monde.filiere.departement.universite_tutelle.nom.upper()},
                            format="json")
    assert res.status_code == 400 and "Une université porte déjà ce nom" in str(res.data)
    res = client_admin.post("/api/v2/departements/", {"universite_tutelle": monde.filiere.departement.universite_tutelle_id,
                                                      "nom": monde.filiere.departement.nom}, format="json")
    assert res.status_code == 400 and "département de ce nom" in str(res.data)
    res = client_admin.post("/api/v2/filieres/", {"departement": monde.filiere.departement_id, "nom": f" {monde.filiere.nom} "},
                            format="json")
    assert res.status_code == 400 and "filière de ce nom" in str(res.data)


# --------------------------------------------------------------------------- filières et types de cycle

def test_renommer_une_filiere_renomme_ses_classes(monde, client_admin, licence):
    res = client_admin.post("/api/v2/filieres/", {"departement": monde.filiere.departement_id, "nom": "Comptabilité",
                                                  "type_cycle": licence.id, "nombre_niveaux": 2}, format="json")
    assert res.status_code == 201, res.data
    fid = res.data["id"]
    assert sorted(Classe.objects.filter(filiere_id=fid).values_list("nom", flat=True)) == [
        "Comptabilité Licence Pro 1 (2026-2027)", "Comptabilité Licence Pro 2 (2026-2027)"]
    payload = dict(res.data, nom="Comptabilité et Finance")
    assert client_admin.put(f"/api/v2/filieres/{fid}/", payload, format="json").status_code == 200
    assert sorted(Classe.objects.filter(filiere_id=fid).values_list("nom", flat=True))[0] == \
        "Comptabilité et Finance Licence Pro 1 (2026-2027)"


def test_renommer_un_type_de_cycle(monde, client_admin, licence):
    item = _creer_specialite(client_admin, monde, licence, niveaux=1)
    res = client_admin.patch(f"/api/v2/cycles-globaux/{licence.id}/", {"nom": "Licence Professionnelle"}, format="json")
    assert res.status_code == 200, res.data
    assert Cycle.objects.get(specialite_id=item["id"]).nom == "Licence Professionnelle"
    assert Niveau.objects.get(cycle__specialite_id=item["id"]).nom == "Licence Professionnelle 1"
    assert _noms_classes(item["id"]) == ["Développement Web Licence Professionnelle 1 (2026-2027)"]
    res = client_admin.delete(f"/api/v2/cycles-globaux/{licence.id}/")
    assert res.status_code == 400 and "utilisé" in str(res.data)


# --------------------------------------------------------------------------- suppressions

@pytest.mark.parametrize("url_de", [
    lambda m: f"/api/v2/universites-tutelles/{m.filiere.departement.universite_tutelle_id}/",
    lambda m: f"/api/v2/departements/{m.filiere.departement_id}/",
    lambda m: f"/api/v2/filieres/{m.filiere.id}/",
])
def test_suppression_refusee_si_des_etudiants_sont_rattaches(monde, client_admin, url_de):
    etudiant = monde.nouvel_etudiant()
    res = client_admin.delete(url_de(monde))
    assert res.status_code == 400 and "étudiants" in str(res.data)
    assert Etudiant.objects.filter(pk=etudiant.pk).exists()


def test_suppression_d_une_specialite(monde, client_admin, licence):
    item = _creer_specialite(client_admin, monde, licence, niveaux=2)
    classe = Classe.objects.filter(specialite_id=item["id"]).first()
    inscription = Inscription.objects.create(etudiant=monde.nouvel_etudiant(inscrire=False), niveau=classe.niveau,
                                             classe=classe, annee_academique=monde.annee.libelle)
    res = client_admin.delete(f"{SPEC}{item['id']}/")
    assert res.status_code == 400 and "inscriptions" in str(res.data)
    inscription.delete()
    assert client_admin.delete(f"{SPEC}{item['id']}/").status_code == 204
    assert not Specialite.objects.filter(pk=item["id"]).exists()
    assert not Classe.objects.filter(specialite_id=item["id"]).exists()
    assert not Niveau.objects.filter(cycle__specialite_id=item["id"]).exists()


def test_suppression_d_une_universite_vide(client_admin):
    res = client_admin.post("/api/v2/universites-tutelles/", {"nom": "Université sans filière"}, format="json")
    uid = res.data["id"]
    Departement.objects.create(universite_tutelle_id=uid, nom="Département vide")
    assert client_admin.delete(f"/api/v2/universites-tutelles/{uid}/").status_code == 204
    assert not Departement.objects.filter(universite_tutelle_id=uid).exists()


# --------------------------------------------------------------------------- salles et années

def test_salle_capacite_effacee(client_admin):
    res = client_admin.post("/api/salles/", {"nom": "Amphi A", "capacite": 120}, format="json")
    assert res.status_code == 201
    item = dict(res.data, capacite="")
    res = client_admin.put(f"/api/salles/{item['id']}/", item, format="json")
    assert res.status_code == 200 and res.data["capacite"] is None
    assert client_admin.post("/api/salles/", {"nom": "amphi a"}, format="json").status_code == 400


def test_nouvelle_annee_classes_au_format_automatique(monde, client_admin, licence):
    item = _creer_specialite(client_admin, monde, licence, niveaux=1)
    AnneeAcademique.objects.create(libelle="2028-2029")
    assert "Développement Web Licence Pro 1 (2028-2029)" in _noms_classes(item["id"])
