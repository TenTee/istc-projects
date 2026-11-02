"""
Documents PDF des paiements : reçu de paiement et facture (relevé de scolarité) d'un étudiant.

Générés à la demande (rien n'est stocké) avec ReportLab, à partir de la configuration de
l'établissement (nom, logo, coordonnées, couleur, directeur).
"""
import io
import re
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from academique.models import ConfigurationEtablissement

from .finance import paiements_de_l_annee, situation_financiere

MOYENS = dict([
    ("cash", "Espèces"), ("mobile_money", "Mobile Money"), ("orange_money", "Orange Money"),
    ("virement", "Virement bancaire"), ("cheque", "Chèque"),
])
TYPES = {"FORMATION": "Frais de formation", "INSCRIPTION": "Frais d'inscription"}
STATUTS_TRANCHE = {"PAID": "Payée", "PARTIAL": "Partielle", "OVERDUE": "En retard", "PENDING": "En attente"}
GRIS = colors.HexColor("#64748B")
FOND = colors.HexColor("#F1F5F9")
BORDURE = colors.HexColor("#CBD5E1")


# --------------------------------------------------------------------------- montants

def fcfa(valeur):
    montant = Decimal(valeur or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if montant == montant.to_integral_value():
        texte = f"{int(montant):,}".replace(",", " ")
    else:
        texte = f"{montant:,.2f}".replace(",", " ").replace(".", ",")
    return f"{texte} FCFA"


_UNITES = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze",
           "douze", "treize", "quatorze", "quinze", "seize"]
_DIZAINES = {2: "vingt", 3: "trente", 4: "quarante", 5: "cinquante", 6: "soixante"}


def _moins_de_cent(n):
    if n <= 16:
        return _UNITES[n]
    if n < 20:
        return "dix-" + _UNITES[n - 10]
    d, u = divmod(n, 10)
    if d in (7, 9):  # soixante-dix…, quatre-vingt-dix…
        base = "soixante" if d == 7 else "quatre-vingt"
        reste = 10 + u
        lien = " et " if (d == 7 and u == 1) else "-"
        return base + lien + _moins_de_cent(reste)
    if d == 8:
        return "quatre-vingts" if u == 0 else "quatre-vingt-" + _UNITES[u]
    if u == 0:
        return _DIZAINES[d]
    if u == 1:
        return _DIZAINES[d] + " et un"
    return _DIZAINES[d] + "-" + _UNITES[u]


def _moins_de_mille(n):
    c, r = divmod(n, 100)
    if c == 0:
        return _moins_de_cent(r)
    centaines = "cent" if c == 1 else _UNITES[c] + " cent" + ("s" if r == 0 else "")
    return centaines if r == 0 else centaines + " " + _moins_de_cent(r)


def nombre_en_lettres(n):
    """Écriture d'un entier en toutes lettres (orthographe traditionnelle)."""
    n = int(n)
    if n == 0:
        return "zéro"
    if n < 0:
        return "moins " + nombre_en_lettres(-n)
    morceaux = []
    for valeur, singulier, pluriel in ((10**9, "milliard", "milliards"), (10**6, "million", "millions")):
        q, n = divmod(n, valeur)
        if q:
            morceaux.append(f"{nombre_en_lettres(q)} {singulier if q == 1 else pluriel}")
    q, n = divmod(n, 1000)
    if q:
        # « mille » est invariable ; « cents » et « quatre-vingts » perdent leur s devant lui.
        if q == 1:
            morceaux.append("mille")
        else:
            texte = _moins_de_mille(q)
            if texte.endswith("cents") or texte.endswith("vingts"):
                texte = texte[:-1]
            morceaux.append(texte + " mille")
    if n:
        morceaux.append(_moins_de_mille(n))
    return " ".join(morceaux)


def montant_en_lettres(valeur):
    entier = int(Decimal(valeur or 0).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    texte = nombre_en_lettres(entier)
    return texte[:1].upper() + texte[1:] + " francs CFA"


# --------------------------------------------------------------------------- mise en page

def _couleur(config):
    valeur = (getattr(config, "couleur_primaire", "") or "").strip()
    return colors.HexColor(valeur) if re.fullmatch(r"#[0-9A-Fa-f]{6}", valeur) else colors.HexColor("#193A7F")


def _styles(couleur):
    base = getSampleStyleSheet()
    return {
        "normal": ParagraphStyle("n", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, leading=13),
        "petit": ParagraphStyle("p", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10.5,
                                textColor=GRIS),
        "gras": ParagraphStyle("g", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=13),
        "etab": ParagraphStyle("e", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=14, leading=17,
                               textColor=couleur),
        "titre": ParagraphStyle("t", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=19,
                                textColor=couleur, alignment=TA_RIGHT),
        "titre_c": ParagraphStyle("tc", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=11,
                                  leading=14, textColor=couleur),
        "droite": ParagraphStyle("d", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, leading=13,
                                 alignment=TA_RIGHT),
        "centre": ParagraphStyle("c", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10.5,
                                 alignment=TA_CENTER, textColor=GRIS),
    }


def _echapper(texte):
    return (str(texte or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _image(champ, largeur_max, hauteur_max):
    try:
        if champ and champ.name and champ.storage.exists(champ.name):
            with champ.open("rb") as f:
                donnees = io.BytesIO(f.read())
            img = Image(donnees)
            ratio = min(largeur_max / img.imageWidth, hauteur_max / img.imageHeight)
            img.drawWidth, img.drawHeight = img.imageWidth * ratio, img.imageHeight * ratio
            return img
    except Exception:  # image illisible : le document reste générable
        return None
    return None


def _entete(config, styles, titre, sous_titre):
    coordonnees = " · ".join(_echapper(x) for x in [
        ", ".join(v for v in [config.adresse, config.ville] if v), config.telephone, config.email, config.site_web
    ] if x)
    bloc = [Paragraph(_echapper(config.nom or "SmartCampus"), styles["etab"])]
    if config.slogan:
        bloc.append(Paragraph(f"<i>{_echapper(config.slogan)}</i>", styles["petit"]))
    if coordonnees:
        bloc.append(Paragraph(coordonnees, styles["petit"]))
    logo = _image(config.logo_entete, 24 * mm, 20 * mm) or _image(config.logo, 24 * mm, 20 * mm)
    droite = [Paragraph(titre, styles["titre"]), Paragraph(sous_titre, styles["droite"])]
    colonnes = ([logo] if logo else []) + [bloc, droite]
    largeurs = ([27 * mm] if logo else []) + ([88 * mm, 67 * mm] if logo else [110 * mm, 72 * mm])
    t = Table([colonnes], colWidths=largeurs)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("LINEBELOW", (0, 0), (-1, 0), 1.2,
                                                                  _couleur(config))]))
    return t


def _tableau(lignes, largeurs, couleur, entete=True, total=False, aligner_droite=()):
    t = Table(lignes, colWidths=largeurs, repeatRows=1 if entete else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDURE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if entete:
        style += [("BACKGROUND", (0, 0), (-1, 0), couleur), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    if total:
        style += [("BACKGROUND", (0, -1), (-1, -1), FOND), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]
    for col in aligner_droite:
        style.append(("ALIGN", (col, 0), (col, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def _pied(canvas, doc, texte):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, texte)
    canvas.drawRightString(A4[0] - 14 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _construire(elements, titre_doc, texte_pied):
    tampon = io.BytesIO()
    doc = SimpleDocTemplate(tampon, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm,
                            bottomMargin=18 * mm, title=titre_doc, author="SmartCampus")
    doc.build(elements, onFirstPage=lambda c, d: _pied(c, d, texte_pied),
              onLaterPages=lambda c, d: _pied(c, d, texte_pied))
    return tampon.getvalue()


def _infos_etudiant(etudiant, classe, styles, annee_libelle=""):
    filiere = getattr(etudiant.filiere, "nom", "") if etudiant.filiere_id else ""
    lignes = [
        [Paragraph("<b>Étudiant</b>", styles["normal"]), Paragraph(_echapper(etudiant.nom), styles["normal"]),
         Paragraph("<b>Matricule</b>", styles["normal"]), Paragraph(_echapper(etudiant.matricule or "-"),
                                                                    styles["normal"])],
        [Paragraph("<b>Filière</b>", styles["normal"]), Paragraph(_echapper(filiere or "-"), styles["normal"]),
         Paragraph("<b>Classe</b>", styles["normal"]), Paragraph(_echapper(getattr(classe, "nom", "") or "-"),
                                                                 styles["normal"])],
    ]
    if annee_libelle or etudiant.contact:
        lignes.append([Paragraph("<b>Année</b>", styles["normal"]), Paragraph(_echapper(annee_libelle or "-"),
                                                                            styles["normal"]),
                       Paragraph("<b>Téléphone</b>", styles["normal"]),
                       Paragraph(_echapper(etudiant.contact or "-"), styles["normal"])])
    t = Table(lignes, colWidths=[24 * mm, 70 * mm, 24 * mm, 64 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), FOND), ("BOX", (0, 0), (-1, -1), 0.4, BORDURE),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def _signature(config, styles, gauche_titre, gauche_nom=""):
    signature = _image(config.signature_directeur, 40 * mm, 18 * mm)
    droite = [Paragraph(f"<b>{_echapper(config.titre_directeur or 'La Direction')}</b>", styles["normal"])]
    droite.append(signature if signature else Spacer(1, 16 * mm))
    if config.nom_directeur:
        droite.append(Paragraph(_echapper(config.nom_directeur), styles["normal"]))
    gauche = [Paragraph(f"<b>{_echapper(gauche_titre)}</b>", styles["normal"]), Spacer(1, 16 * mm)]
    if gauche_nom:
        gauche.append(Paragraph(_echapper(gauche_nom), styles["normal"]))
    t = Table([[gauche, droite]], colWidths=[91 * mm, 91 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return KeepTogether([Spacer(1, 6 * mm), t])


def _date_fr(valeur, heure=False):
    if not valeur:
        return "-"
    if hasattr(valeur, "tzinfo") and timezone.is_aware(valeur):
        valeur = timezone.localtime(valeur)
    return valeur.strftime("%d/%m/%Y à %H:%M" if heure else "%d/%m/%Y")


def _annee_du_paiement(paiement):
    if paiement.frais_id and paiement.frais.classe_id:
        return paiement.frais.classe.annee_academique_id
    inscription = paiement.etudiant.inscriptions.filter(
        annee_academique_ref__isnull=False).order_by("-date_inscription").first() if paiement.etudiant_id else None
    return getattr(inscription, "annee_academique_ref_id", None)


# --------------------------------------------------------------------------- reçu

def recu_pdf(paiement):
    config = ConfigurationEtablissement.get_config()
    couleur = _couleur(config)
    styles = _styles(couleur)
    etudiant = paiement.etudiant
    annee_id = _annee_du_paiement(paiement)
    sf = situation_financiere(etudiant, annee_id)
    classe = paiement.frais.classe if paiement.frais_id else sf["classe"]
    annee_libelle = getattr(getattr(classe, "annee_academique", None), "libelle", "") if classe else ""

    du = sf["du_inscription"] if paiement.paiement_type == "INSCRIPTION" else sf["du_formation"]
    precedents = paiements_de_l_annee(etudiant, annee_id).filter(paiement_type=paiement.paiement_type).filter(
        Q(date_paiement__lt=paiement.date_paiement) | Q(date_paiement=paiement.date_paiement, id__lte=paiement.id))
    cumul = sum((Decimal(p.montant_paye) for p in precedents), Decimal("0"))
    if paiement.id not in {p.id for p in precedents}:  # paiement hors de l'année calculée
        cumul += Decimal(paiement.montant_paye)

    numero = paiement.numero_recu or f"REC-{paiement.pk:06d}"
    objet = TYPES.get(paiement.paiement_type, paiement.paiement_type)
    if paiement.frais_id:
        objet += f" : {paiement.frais.libelle}"
    caissier = ""
    if paiement.enregistre_par_id:
        u = paiement.enregistre_par
        caissier = " ".join(p for p in [u.noms, u.prenoms] if p).strip() or u.username

    elements = [
        _entete(config, styles, "REÇU DE PAIEMENT", f"N° <b>{_echapper(numero)}</b><br/>"
                                                     f"Payé le {_date_fr(paiement.date_paiement, heure=True)}"),
        Spacer(1, 6 * mm),
        _infos_etudiant(etudiant, classe, styles, annee_libelle),
        Spacer(1, 6 * mm),
        _tableau(
            [["Objet", "Mode de paiement", "Montant reçu"],
             [Paragraph(_echapper(objet), styles["normal"]), MOYENS.get(paiement.moyen_paiement or "",
                                                                        paiement.moyen_paiement or "Espèces"),
              fcfa(paiement.montant_paye)]],
            [92 * mm, 45 * mm, 45 * mm], couleur, aligner_droite=(2,)),
        Spacer(1, 3 * mm),
        Paragraph(f"Arrêté le présent reçu à la somme de : <b>{_echapper(montant_en_lettres(paiement.montant_paye))}"
                  f"</b>.", styles["normal"]),
        Spacer(1, 6 * mm),
        Paragraph(f"Situation des {objet.split(' :')[0].lower()} après ce paiement", styles["titre_c"]),
        Spacer(1, 2 * mm),
        _tableau(
            [["Montant dû", "Total payé à ce jour", "Reste à payer"],
             [fcfa(du), fcfa(cumul), fcfa(max(du - cumul, Decimal("0")))]],
            [61 * mm, 61 * mm, 60 * mm], couleur, aligner_droite=(0, 1, 2)),
    ]
    if du and cumul > du:
        elements += [Spacer(1, 2 * mm), Paragraph(f"Trop-perçu : {fcfa(cumul - du)}.", styles["petit"])]
    elements.append(_signature(config, styles, "Le caissier / La caissière", caissier))
    elements += [Spacer(1, 6 * mm), Paragraph(
        "Ce reçu est la preuve de votre paiement : conservez-le. Toute correction d'un paiement est tracée "
        "par l'établissement.", styles["centre"])]
    pied = f"{config.nom or 'SmartCampus'} · Reçu {numero} · édité le {_date_fr(timezone.now(), heure=True)}"
    return _construire(elements, f"Reçu {numero}", pied)


# --------------------------------------------------------------------------- facture

def facture_pdf(etudiant, annee_id=None):
    from paiements.models import Frais
    from paiements.schedule_resolver import compute_student_retard

    config = ConfigurationEtablissement.get_config()
    couleur = _couleur(config)
    styles = _styles(couleur)
    sf = situation_financiere(etudiant, annee_id)
    classe = sf["classe"]
    annee = getattr(classe, "annee_academique", None) if classe else None
    annee_libelle = getattr(annee, "libelle", "") or ""
    numero = f"FAC-{(annee_libelle or str(timezone.localdate().year)).split('-')[0]}-" \
             f"{etudiant.matricule or etudiant.pk}"

    # Lignes facturées : frais de la classe, puis réduction / bourse éventuelle.
    lignes = [["Désignation", "Montant"]]
    brut = Decimal("0")
    if classe:
        for f in Frais.objects.filter(classe=classe).order_by("-libelle"):
            lignes.append([Paragraph(_echapper(f.libelle), styles["normal"]), fcfa(f.montant)])
            brut += Decimal(f.montant)
    net = sf["du_total"]
    if brut > net:
        reduction = sf["reduction"]
        libelle = "Réduction / bourse"
        if reduction is not None:
            libelle = reduction.get_type_reduction_display() if hasattr(reduction, "get_type_reduction_display") \
                else libelle
            if getattr(reduction, "bourse", None):
                libelle += f" ({reduction.bourse.code})"
        lignes.append([Paragraph(_echapper(libelle), styles["normal"]), "- " + fcfa(brut - net)])
    elif net > brut:
        lignes.append([Paragraph("Ajustement (échéancier personnalisé)", styles["normal"]), fcfa(net - brut)])
    lignes.append(["Net à payer", fcfa(net)])

    paye = sf["paye_total"]
    reste = net - paye

    elements = [
        _entete(config, styles, "FACTURE", f"N° <b>{_echapper(numero)}</b><br/>Éditée le "
                                           f"{_date_fr(timezone.localdate())}"),
        Spacer(1, 6 * mm),
        _infos_etudiant(etudiant, classe, styles, annee_libelle),
        Spacer(1, 6 * mm),
        Paragraph("Frais de scolarité", styles["titre_c"]), Spacer(1, 2 * mm),
        _tableau(lignes, [137 * mm, 45 * mm], couleur, total=True, aligner_droite=(1,)),
        Spacer(1, 4 * mm),
        _tableau([["Net à payer", "Déjà payé", "Reste à payer"],
                  [fcfa(net), fcfa(paye), fcfa(max(reste, Decimal("0")))]],
                 [61 * mm, 61 * mm, 60 * mm], couleur, aligner_droite=(0, 1, 2)),
    ]
    if reste > 0:
        elements += [Spacer(1, 2 * mm), Paragraph(
            f"Reste à payer : <b>{_echapper(montant_en_lettres(reste))}</b>.", styles["normal"])]
    else:
        elements += [Spacer(1, 2 * mm), Paragraph("<b>Scolarité soldée.</b>" + (
            f" Trop-perçu : {fcfa(-reste)}." if reste < 0 else ""), styles["normal"])]

    paiements = list(sf["paiements"].order_by("date_paiement", "id"))
    elements += [Spacer(1, 6 * mm), Paragraph("Paiements reçus", styles["titre_c"]), Spacer(1, 2 * mm)]
    if paiements:
        lignes_p = [["Date", "N° de reçu", "Objet", "Mode", "Montant"]]
        for p in paiements:
            lignes_p.append([_date_fr(p.date_paiement), p.numero_recu or "-",
                             Paragraph(_echapper(TYPES.get(p.paiement_type, p.paiement_type)), styles["normal"]),
                             MOYENS.get(p.moyen_paiement or "", p.moyen_paiement or "Espèces"), fcfa(p.montant_paye)])
        lignes_p.append(["", "", "", "Total", fcfa(paye)])
        elements.append(_tableau(lignes_p, [24 * mm, 36 * mm, 54 * mm, 32 * mm, 36 * mm], couleur, total=True,
                                 aligner_droite=(4,)))
    else:
        elements.append(Paragraph("Aucun paiement enregistré.", styles["normal"]))

    tranches = []
    if classe:
        tranches = compute_student_retard(etudiant, classe).get("installments", []) or []
    if not tranches:
        # Plan créé sans classe (API /paiements/plans/) : on affiche ses tranches.
        from paiements.models import StudentPaymentPlan
        plan = StudentPaymentPlan.objects.filter(etudiant=etudiant).exclude(
            status=StudentPaymentPlan.STATUS_CANCELLED).first()
        if plan:
            tranches = [{"label": t.label, "due_date": t.due_date, "amount_due": t.amount_due,
                         "amount_paid": t.amount_paid, "status": t.status}
                        for t in plan.installments.order_by("due_date", "order")]
    if tranches:
        lignes_t = [["Tranche", "Échéance", "Montant", "Payé", "Reste", "Statut"]]
        for t in tranches:
            du_t, paye_t = Decimal(t.get("amount_due") or 0), Decimal(t.get("amount_paid") or 0)
            lignes_t.append([Paragraph(_echapper(t.get("label")), styles["normal"]), _date_fr(t.get("due_date")),
                             fcfa(du_t), fcfa(paye_t), fcfa(max(du_t - paye_t, Decimal("0"))),
                             STATUTS_TRANCHE.get(t.get("status"), t.get("status") or "")])
        elements += [Spacer(1, 6 * mm), KeepTogether([
            Paragraph("Échéancier des frais de formation", styles["titre_c"]), Spacer(1, 2 * mm),
            _tableau(lignes_t, [40 * mm, 24 * mm, 31 * mm, 31 * mm, 31 * mm, 25 * mm], couleur,
                     aligner_droite=(2, 3, 4))])]

    elements.append(_signature(config, styles, "Le service financier"))
    pied = f"{config.nom or 'SmartCampus'} · Facture {numero} · éditée le {_date_fr(timezone.now(), heure=True)}"
    return _construire(elements, f"Facture {numero}", pied)
