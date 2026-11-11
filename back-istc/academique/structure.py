"""
Structure académique : répercussions automatiques des modifications et protection des suppressions.

Hiérarchie : Université → Département → Filière → Spécialité → Cycle → Niveaux → Classes (une par
année académique). Les niveaux et les classes sont générés automatiquement ; ce module garde
ces éléments générés cohérents quand on modifie un parent :

- renommer une spécialité, une filière ou un type de cycle renomme les niveaux et les classes
  qui portent encore leur nom automatique (un nom saisi à la main n'est jamais écrasé) ;
- changer le type de cycle ou le nombre de niveaux d'une spécialité ajoute ou retire des
  niveaux (et leurs classes) ;
- changer la filière d'une spécialité déplace ses cycles et ses classes.

Les suppressions en cascade de Django effaceraient sans prévenir les étudiants, notes et
paiements rattachés (Etudiant.filiere est en CASCADE) : `donnees_rattachees()` les compte et
les vues refusent la suppression tant qu'il en reste.
"""
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from .models import Classe, Cycle, CycleGlobal, Departement, Filiere, Niveau, Specialite, UniversiteTutelle


# --------------------------------------------------------------------------- noms automatiques

def _prefixe(classe):
    if classe.specialite_id:
        return classe.specialite.nom
    return classe.filiere.nom if classe.filiere_id else ""


def nom_automatique(classe):
    """Nom généré d'une classe : « <spécialité ou filière> <niveau> (<année>) »."""
    return f"{_prefixe(classe)} {classe.niveau.nom} ({classe.annee_academique.libelle})".strip()


def _noms_automatiques_possibles(classe):
    # Variantes produites par les anciennes versions du code (création, signal d'année, save()).
    prefixe, annee = _prefixe(classe), classe.annee_academique.libelle
    cycle_nom = classe.cycle.nom if classe.cycle_id else ""
    return {
        nom_automatique(classe),
        f"{prefixe} - {classe.niveau.nom} ({annee})",
        f"{prefixe} {cycle_nom} {classe.niveau.ordre} ({annee})",
    }


def _niveau_a_nom_automatique(niveau):
    return niveau.nom == f"{niveau.cycle.nom} {niveau.ordre}"


def classes_a_nom_automatique(classes):
    """Identifiants des classes qui portent encore un nom généré (à renommer après un changement)."""
    qs = classes.select_related("specialite", "filiere", "niveau", "cycle", "annee_academique")
    return [c.pk for c in qs if c.nom in _noms_automatiques_possibles(c)]


def renommer_classes(pks):
    for classe in Classe.objects.filter(pk__in=pks).select_related(
            "specialite", "filiere", "niveau", "cycle", "annee_academique"):
        nouveau = nom_automatique(classe)
        if classe.nom != nouveau:
            Classe.objects.filter(pk=classe.pk).update(nom=nouveau)


def renommer_niveaux(cycle, ancien_nom_cycle):
    for niveau in cycle.niveaux.all():
        if niveau.nom == f"{ancien_nom_cycle} {niveau.ordre}":
            Niveau.objects.filter(pk=niveau.pk).update(nom=f"{cycle.nom} {niveau.ordre}")


# --------------------------------------------------------------------------- données rattachées

def _portee(obj):
    """(filières, spécialités, niveaux, classes) concernés par l'élément, sous forme de querysets."""
    if isinstance(obj, UniversiteTutelle):
        filieres = Filiere.objects.filter(departement__universite_tutelle=obj)
    elif isinstance(obj, Departement):
        filieres = Filiere.objects.filter(departement=obj)
    elif isinstance(obj, Filiere):
        filieres = Filiere.objects.filter(pk=obj.pk)
    else:
        filieres = None

    if filieres is not None:
        niveaux = Niveau.objects.filter(Q(cycle__filiere__in=filieres) | Q(cycle__specialite__filiere__in=filieres))
        classes = Classe.objects.filter(filiere__in=filieres)
        return filieres, niveaux, classes
    if isinstance(obj, Specialite):
        return None, Niveau.objects.filter(cycle__specialite=obj), Classe.objects.filter(specialite=obj)
    if isinstance(obj, Cycle):
        return None, obj.niveaux.all(), obj.classes.all()
    if isinstance(obj, Niveau):
        return None, Niveau.objects.filter(pk=obj.pk), obj.classes.all()
    raise TypeError(obj)


def donnees_rattachees(obj, niveaux=None):
    """
    {libellé: nombre} des données qu'une suppression effacerait (seules les valeurs > 0 sont gardées).
    `niveaux` restreint le contrôle à certains niveaux (réduction du nombre de niveaux).
    """
    from emploidutemps.models import EmploiDuTemps
    from etudiants.models import Etudiant, Inscription
    from notes.models import Note
    from paiements.models import Frais, Paiement
    from academique.models import Affectation, Epreuve, PreInscription

    if niveaux is not None:
        filieres, classes = None, Classe.objects.filter(niveau__in=niveaux)
    else:
        filieres, niveaux, classes = _portee(obj)

    comptes = {
        "inscriptions": Inscription.objects.filter(Q(classe__in=classes) | Q(niveau__in=niveaux)).distinct().count(),
        "notes": Note.objects.filter(classe__in=classes).count(),
        "frais de scolarité": Frais.objects.filter(classe__in=classes).count(),
        "créneaux d'emploi du temps": EmploiDuTemps.objects.filter(Q(classe__in=classes) | Q(niveau__in=niveaux)).count(),
        "épreuves": Epreuve.objects.filter(niveau__in=niveaux).count(),
        "affectations d'enseignants": Affectation.objects.filter(classe__in=classes).count(),
        "pré-inscriptions": PreInscription.objects.filter(
            Q(niveau_souhaite__in=niveaux) | Q(classe_souhaitee__in=classes)).count(),
    }
    if filieres is not None:
        from vacations.models import Coordination, PointageEnseignant, RecapMensuel
        comptes.update({
            "étudiants": Etudiant.objects.filter(filiere__in=filieres).count(),
            "paiements": Paiement.objects.filter(filiere__in=filieres).count(),
            "pré-inscriptions": PreInscription.objects.filter(
                Q(filiere_souhaitee__in=filieres) | Q(niveau_souhaite__in=niveaux)).count(),
            "coordinations de filière": Coordination.objects.filter(filiere__in=filieres).count(),
            "pointages des vacataires": PointageEnseignant.objects.filter(filiere__in=filieres).count(),
            "récapitulatifs d'heures": RecapMensuel.objects.filter(filiere__in=filieres).count(),
        })
    return {nom: n for nom, n in comptes.items() if n}


def message_donnees(intitule, comptes):
    detail = ", ".join(f"{n} {nom}" for nom, n in comptes.items())
    return f"{intitule} contient des données ({detail}) : supprimez-les ou déplacez-les d'abord."


def verifier_suppression(obj, intitule):
    comptes = donnees_rattachees(obj)
    if comptes:
        raise ValidationError({"detail": message_donnees(intitule, comptes)})


# --------------------------------------------------------------------------- spécialités

def _creer_niveaux(cycle, de, a):
    """Crée les niveaux d'ordre `de`..`a` ; leurs classes (une par année) sont créées par signal."""
    for ordre in range(de, a + 1):
        Niveau.objects.create(cycle=cycle, nom=f"{cycle.nom} {ordre}", ordre=ordre)


def configurer_cycle(specialite=None, filiere=None, type_cycle=None, nombre_niveaux=None):
    """
    Crée ou met à jour le cycle généré d'une spécialité (ou d'une filière sans spécialité) :
    type de cycle et nombre de niveaux. Refuse de retirer des niveaux qui contiennent des données.
    """
    proprietaire = {"specialite": specialite} if specialite else {"filiere": filiere, "specialite": None}
    cycle = Cycle.objects.filter(**proprietaire).order_by("ordre", "pk").first()

    if cycle is None:
        if not type_cycle:
            return None
        cycle = Cycle.objects.create(
            specialite=specialite, filiere=specialite.filiere if specialite else filiere,
            type_cycle=type_cycle, nom=type_cycle.nom, ordre=1,
        )
        _creer_niveaux(cycle, 1, max(int(nombre_niveaux or 0), 0))
        return cycle

    if type_cycle and cycle.type_cycle_id != type_cycle.pk:
        ancien_nom = cycle.nom
        cycle.type_cycle = type_cycle
        cycle.nom = type_cycle.nom
        cycle.save(update_fields=["type_cycle", "nom", "updated_at"])
        renommer_niveaux(cycle, ancien_nom)

    if nombre_niveaux is not None:
        nombre = int(nombre_niveaux)
        if nombre < 1:
            raise ValidationError({"nombre_niveaux": "Il faut au moins un niveau."})
        niveaux = list(cycle.niveaux.order_by("ordre"))
        actuel = len(niveaux)
        if nombre > actuel:
            depart = (niveaux[-1].ordre if niveaux else 0) + 1
            _creer_niveaux(cycle, depart, depart + nombre - actuel - 1)
        elif nombre < actuel:
            en_trop = niveaux[nombre:]
            comptes = donnees_rattachees(None, niveaux=Niveau.objects.filter(pk__in=[n.pk for n in en_trop]))
            if comptes:
                noms = ", ".join(n.nom for n in en_trop)
                raise ValidationError({"nombre_niveaux": message_donnees(f"Impossible de retirer {noms} : ce niveau", comptes)})
            for niveau in en_trop:
                Classe.objects.filter(niveau=niveau).delete()
                niveau.delete()
    return cycle


@transaction.atomic
def mettre_a_jour_specialite(serializer, type_cycle_id=None, nombre_niveaux=None):
    """Enregistre la spécialité puis répercute nom, filière, type de cycle et nombre de niveaux."""
    specialite = serializer.instance
    ancienne_filiere_id = specialite.filiere_id
    a_renommer = classes_a_nom_automatique(Classe.objects.filter(specialite=specialite))

    nouvelle_filiere = serializer.validated_data.get("filiere")
    if nouvelle_filiere is not None and nouvelle_filiere.pk != ancienne_filiere_id:
        comptes = donnees_rattachees(specialite)
        if comptes:
            raise ValidationError({"filiere": message_donnees(
                "Impossible de changer de filière : la spécialité", comptes)})

    specialite = serializer.save()

    if specialite.filiere_id != ancienne_filiere_id:
        Cycle.objects.filter(specialite=specialite).update(filiere=specialite.filiere)
        Classe.objects.filter(specialite=specialite).update(filiere=specialite.filiere)
        from .models import CourseAssignment
        CourseAssignment.objects.filter(specialite=specialite).update(filiere=specialite.filiere)

    type_cycle = _type_cycle(type_cycle_id)
    configurer_cycle(specialite=specialite, type_cycle=type_cycle, nombre_niveaux=_entier(nombre_niveaux))
    renommer_classes(a_renommer + [
        pk for pk in classes_a_nom_automatique(Classe.objects.filter(specialite=specialite)) if pk not in a_renommer
    ])
    return specialite


@transaction.atomic
def mettre_a_jour_filiere(serializer):
    filiere = serializer.instance
    a_renommer = classes_a_nom_automatique(Classe.objects.filter(filiere=filiere, specialite__isnull=True))
    filiere = serializer.save()
    renommer_classes(a_renommer)
    return filiere


@transaction.atomic
def mettre_a_jour_type_cycle(serializer):
    """Renommer un type de cycle (Licence, BTS…) renomme les cycles, niveaux et classes générés."""
    type_cycle = serializer.instance
    ancien_nom = type_cycle.nom
    cycles = list(Cycle.objects.filter(type_cycle=type_cycle, nom=ancien_nom))
    a_renommer = classes_a_nom_automatique(Classe.objects.filter(cycle__in=cycles))
    type_cycle = serializer.save()
    if type_cycle.nom != ancien_nom:
        for cycle in cycles:
            cycle.nom = type_cycle.nom
            cycle.save(update_fields=["nom", "updated_at"])
            renommer_niveaux(cycle, ancien_nom)
        renommer_classes(a_renommer)
    return type_cycle


def _type_cycle(type_cycle_id):
    if type_cycle_id in (None, ""):
        return None
    try:
        return CycleGlobal.objects.get(pk=type_cycle_id)
    except (CycleGlobal.DoesNotExist, ValueError, TypeError):
        raise ValidationError({"type_cycle": "Type de cycle introuvable."})


def _entier(valeur):
    if valeur in (None, ""):
        return None
    try:
        return int(valeur)
    except (TypeError, ValueError):
        raise ValidationError({"nombre_niveaux": "Nombre de niveaux invalide."})
