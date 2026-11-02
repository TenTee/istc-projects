"""Identifiants des comptes : génération et contrôle des mots de passe et des noms d'utilisateur."""
import re
import secrets

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.utils import translation

# Sans caractères faciles à confondre à l'oral ou à la lecture (0/O, 1/l/I) : le mot de passe
# provisoire est dicté ou recopié depuis un message.
ALPHABET_MOT_DE_PASSE = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
LONGUEUR_MOT_DE_PASSE = 10

USERNAME_REGEX = re.compile(r"^[A-Za-z0-9.@+_-]{3,150}$")


def generer_mot_de_passe(longueur=LONGUEUR_MOT_DE_PASSE):
    """Mot de passe provisoire aléatoire (module secrets) avec au moins une lettre et un chiffre."""
    while True:
        mdp = "".join(secrets.choice(ALPHABET_MOT_DE_PASSE) for _ in range(longueur))
        if any(c.isdigit() for c in mdp) and any(c.isalpha() for c in mdp):
            return mdp


def erreurs_mot_de_passe(mot_de_passe, user=None):
    """Liste des problèmes du mot de passe (validateurs Django, messages en français) ; vide = valide."""
    with translation.override("fr"):
        try:
            password_validation.validate_password(mot_de_passe, user=user)
        except ValidationError as exc:
            return [str(m) for m in exc.messages]
    return []


def erreur_nom_utilisateur(username, user=None):
    """Message d'erreur pour un nom d'utilisateur, ou None s'il est valide et libre."""
    from users.models import CustomUser

    if not username or not USERNAME_REGEX.match(username):
        return ("3 à 150 caractères : lettres sans accent, chiffres et les signes . @ + - _ uniquement "
                "(pas d'espace).")
    deja_pris = CustomUser.objects.filter(username__iexact=username)
    if user is not None:
        deja_pris = deja_pris.exclude(pk=user.pk)
    if deja_pris.exists():
        return "Ce nom d'utilisateur est déjà utilisé."
    return None


def reinitialiser_mot_de_passe(user):
    """Donne un nouveau mot de passe provisoire au compte et le renvoie en clair (une seule fois)."""
    mdp = generer_mot_de_passe()
    user.set_password(mdp)
    user._raw_password = mdp
    user.save()
    # Étudiant : le mot de passe provisoire reste consultable dans sa fiche jusqu'à ce qu'il le change.
    etudiant = _etudiant_du_compte(user)
    if etudiant is not None:
        etudiant.initial_password = mdp
        etudiant.save(update_fields=["initial_password"])
    return mdp


def _etudiant_du_compte(user):
    from etudiants.models import Etudiant
    return Etudiant.objects.filter(user=user).first()


def identifiants(user, mot_de_passe, nom=None, telephone=None):
    """Réponse commune des API qui créent ou réinitialisent un compte (affichée et copiée par l'interface)."""
    return {
        "username": user.username,
        "password": mot_de_passe,
        "nom": nom or " ".join(p for p in [user.noms, user.prenoms] if p).strip() or user.username,
        "email": user.email or "",
        "telephone": telephone or "",
    }
