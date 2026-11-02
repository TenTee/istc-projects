"""
Correction et suppression des paiements.

Un paiement influence deux données calculées au moment de sa saisie :
- `montant_du` / `solde_restant` des paiements de son groupe (même frais, ou même type) ;
- `amount_paid` / `status` des tranches de l'échéancier de l'étudiant.
Après une correction ou une suppression, on recalcule tout pour l'étudiant concerné, puis on
écrit une ligne dans le journal (qui, quand, pourquoi, valeurs avant / après).
"""
from decimal import Decimal

from django.db.models import Q, Sum

from .models import JournalPaiement, Paiement, StudentPaymentInstallment, StudentPaymentPlan

ZERO = Decimal("0")
LONGUEUR_MIN_MOTIF = 5


def instantane(paiement):
    """Valeurs du paiement conservées dans le journal (lisibles sans la base)."""
    return {
        "numero_recu": paiement.numero_recu,
        "etudiant": paiement.etudiant_id,
        "paiement_type": paiement.paiement_type,
        "frais": paiement.frais_id,
        "frais_libelle": paiement.frais.libelle if paiement.frais_id else "",
        "montant_paye": str(paiement.montant_paye),
        "moyen_paiement": paiement.moyen_paiement or "",
        "date_paiement": paiement.date_paiement.isoformat() if paiement.date_paiement else None,
        "justificatif": paiement.justificatif.name if paiement.justificatif else "",
    }


def nom_utilisateur(user):
    if not user or not getattr(user, "is_authenticated", False):
        return ""
    nom = " ".join(p for p in [getattr(user, "noms", ""), getattr(user, "prenoms", "")] if p).strip()
    return nom or user.username


def journaliser(action, paiement, user, motif="", avant=None, apres=None, etudiant=None):
    etudiant = etudiant or paiement.etudiant
    return JournalPaiement.objects.create(
        paiement_id_origine=paiement.pk,
        numero_recu=paiement.numero_recu or "",
        etudiant=etudiant,
        etudiant_nom=getattr(etudiant, "nom", "") or "",
        action=action,
        motif=motif or "",
        utilisateur=user if getattr(user, "is_authenticated", False) else None,
        utilisateur_nom=nom_utilisateur(user),
        avant=avant,
        apres=apres,
    )


def verifier_motif(motif):
    """Message d'erreur si le motif est absent ou trop court, sinon None."""
    motif = (motif or "").strip()
    if len(motif) < LONGUEUR_MIN_MOTIF:
        return f"Indiquez le motif (au moins {LONGUEUR_MIN_MOTIF} caractères) : il est conservé dans le journal."
    return None


# --------------------------------------------------------------------------- recalculs

def recalculer_soldes(etudiant):
    """Recalcule montant_du et solde_restant de tous les paiements de l'étudiant, groupe par groupe."""
    paiements = list(
        Paiement.objects.filter(etudiant=etudiant).select_related("frais").order_by("date_paiement", "id")
    )
    deja_vus = set()
    for paiement in paiements:
        cle = ("frais", paiement.frais_id) if paiement.frais_id else ("type", paiement.paiement_type)
        if cle in deja_vus:
            continue
        deja_vus.add(cle)
        groupe = [p for p in paiements if (p.frais_id == paiement.frais_id if paiement.frais_id
                                            else p.paiement_type == paiement.paiement_type)]
        premier = groupe[0]
        reference = premier.montant_du if premier.montant_du is not None else premier.montant_reference()
        cumul = ZERO
        for index, p in enumerate(groupe):
            cumul += Decimal(p.montant_paye or 0)
            Paiement.objects.filter(pk=p.pk).update(
                montant_du=reference if index == 0 else None,
                solde_restant=reference - cumul,
            )


def _paiements_formation_du_plan(plan):
    qs = Paiement.objects.filter(etudiant=plan.etudiant, filiere=plan.filiere, paiement_type="FORMATION")
    annee_id = getattr(plan.classe, "annee_academique_id", None) if plan.classe_id else None
    if annee_id:
        qs = qs.filter(Q(frais__classe__annee_academique_id=annee_id) | Q(frais__isnull=True))
    return qs


def reconstruire_echeancier(etudiant):
    """Répartit de nouveau les paiements de formation sur les tranches (dans l'ordre des échéances)."""
    plans = StudentPaymentPlan.objects.filter(etudiant=etudiant).exclude(status=StudentPaymentPlan.STATUS_CANCELLED)
    for plan in plans:
        reste = _paiements_formation_du_plan(plan).aggregate(t=Sum("montant_paye"))["t"] or ZERO
        for tranche in plan.installments.order_by("due_date", "order"):
            applique = min(Decimal(tranche.amount_due or 0), reste) if reste > 0 else ZERO
            reste -= applique
            if tranche.amount_paid != applique:
                tranche.amount_paid = applique
                tranche.save(update_fields=["amount_paid", "status", "updated_at"])
            else:
                ancien = tranche.status
                tranche.refresh_status()
                if tranche.status != ancien:
                    tranche.save(update_fields=["status", "updated_at"])
        solde = plan.installments.exclude(status=StudentPaymentInstallment.STATUS_PAID).exists()
        statut = StudentPaymentPlan.STATUS_ACTIVE if solde else StudentPaymentPlan.STATUS_COMPLETED
        if plan.installments.exists() and plan.status != statut:
            plan.status = statut
            plan.save(update_fields=["status", "updated_at"])


def recalculer_etudiant(etudiant):
    if etudiant is None:
        return
    recalculer_soldes(etudiant)
    reconstruire_echeancier(etudiant)
