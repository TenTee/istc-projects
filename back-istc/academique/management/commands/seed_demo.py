"""
Remplit une base de DÉMONSTRATION avec des données entièrement fictives.

Sert aux captures d'écran du guide d'utilisation et aux formations.
    DATABASE_URL=sqlite:////chemin/demo.sqlite3 python manage.py seed_demo

Par sécurité, la commande refuse de tourner si la base n'est pas un fichier SQLite dont
le nom contient « demo » (pour ne jamais toucher la base de production).

Comptes créés (mot de passe commun : Demo2026!) :
    admin.demo      administrateur
    formateur.demo  formateur permanent, coordonnateur de la filière Génie Informatique
    etudiant.demo   étudiant de Développement Web - Licence 1
"""
import io
import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management import BaseCommand, CommandError, call_command
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

MOT_DE_PASSE = "Demo2026!"

PRENOMS = ["Alice", "Brice", "Carine", "Didier", "Estelle", "Franck", "Grâce", "Hervé", "Inès", "Joël",
           "Karelle", "Landry", "Mireille", "Nadège", "Olivier", "Patricia", "Quentin", "Rosine", "Serge",
           "Tatiana", "Ulrich", "Vanessa", "William", "Yannick", "Zita", "Armel", "Blanche", "Cédric"]
NOMS = ["NGONO", "MBARGA", "EBODÉ", "FOTSO", "KAMGA", "NJOYA", "ATANGANA", "BELLA", "ESSOMBA", "TCHOUA",
        "MANGA", "NANA", "OWONA", "DJOUMESSI", "ELLA", "MOUKOKO", "TALLA", "ZANG", "NKOULOU", "ABENA"]


def pdf_factice(titre):
    """Petit PDF valide (une page) contenant un titre."""
    contenu = f"BT /F1 20 Tf 72 720 Td ({titre}) Tj ET".encode("latin-1", "replace")
    objets = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(contenu) + contenu + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objets, 1):
        offs.append(out.tell())
        out.write(b"%d 0 obj\n" % i + o + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1))
    for o in offs:
        out.write(b"%010d 00000 n \n" % o)
    out.write(b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objets) + 1, xref))
    return out.getvalue()


def image_logo(texte="SC", fond=(31, 56, 100)):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((10, 10, 390, 390), fill=fond)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 110)
    except OSError:
        font = ImageFont.load_default()
    w = d.textlength(texte, font=font)
    d.text(((400 - w) / 2, 135), texte, fill=(255, 255, 255), font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


class Command(BaseCommand):
    help = "Remplit une base de démonstration avec des données fictives (captures d'écran, formations)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Ne pas vérifier le nom de la base.")

    # ------------------------------------------------------------------
    def handle(self, *args, **opts):
        db = settings.DATABASES["default"]
        if not opts["force"] and ("sqlite" not in db["ENGINE"] or "demo" not in str(db["NAME"]).lower()):
            raise CommandError("Refus : la base n'est pas une base SQLite « demo ». Utilisez une base dédiée.")
        call_command("flush", interactive=False, verbosity=0)
        random.seed(2026)
        self.aujourdhui = timezone.localdate()
        self._etablissement()
        self._comptes()
        self._structure()
        self._enseignants()
        self._etudiants()
        self._emploi_du_temps()
        self._finances()
        self._notes_et_assiduite()
        self._vacations()
        self._rh_et_paie()
        self._logistique()
        self._preinscriptions()
        self._documents()
        self.stdout.write(self.style.SUCCESS("Base de démonstration prête. Comptes : admin.demo / formateur.demo / "
                                             f"etudiant.demo — mot de passe {MOT_DE_PASSE}"))

    # ------------------------------------------------------------------
    def api(self, user):
        c = APIClient(SERVER_NAME="localhost")
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
        return c

    def ok(self, res, *codes):
        if res.status_code not in (codes or (200, 201)):
            raise CommandError(f"{res.status_code} {getattr(res, 'data', res.content)!r}")
        return res

    def personne(self, i):
        return f"{NOMS[i % len(NOMS)]} {PRENOMS[(i * 7) % len(PRENOMS)]}"

    # ------------------------------------------------------------------
    def _etablissement(self):
        from academique.models import ConfigurationEtablissement, CycleGlobal, ParametresGlobaux
        conf = ConfigurationEtablissement.objects.first() or ConfigurationEtablissement()
        conf.nom = "Établissement de démonstration"
        conf.adresse, conf.ville = "Rue des Écoles, Bonamoussadi", "Douala"
        conf.telephone, conf.email = "+237 6 00 00 00 00", "contact@istc-demo.cm"
        conf.site_web, conf.slogan = "www.istc-demo.cm", "Former pour réussir"
        conf.nom_directeur, conf.titre_directeur = "Dr Jean DUPONT", "Directeur Général"
        conf.couleur_primaire, conf.couleur_secondaire = "#1F3864", "#F5A623"
        logo = image_logo()
        if logo:
            conf.logo.save("logo_demo.png", ContentFile(logo), save=False)
            conf.logo_entete.save("logo_entete_demo.png", ContentFile(logo), save=False)
        conf.save()
        ParametresGlobaux.get_parametres()
        self.lic = CycleGlobal.objects.create(nom="Licence", code="LIC")
        self.bts = CycleGlobal.objects.create(nom="BTS", code="BTS")

    def _comptes(self):
        from users.models import CustomUser, Role
        Role.objects.create(code="admin", libelle="Administrateur", **{f"can_manage_{d}": "ecriture" for d in
                                                                       ("rh", "pedagogie", "logistique", "finance", "etudiants")})
        Role.objects.create(code="secretaire", libelle="Secrétaire", can_manage_etudiants="ecriture",
                            can_manage_pedagogie="lecture", can_manage_finance="lecture")
        Role.objects.create(code="comptable", libelle="Comptable", can_manage_finance="ecriture",
                            can_manage_etudiants="lecture", can_manage_rh="lecture")
        self.admin = self.compte("admin.demo", "DEMO", "Administrateur", "admin@istc-demo.cm", "admin", superuser=True)
        self.compte(None, "ESSOMBA", "Laure", "secretariat@istc-demo.cm", "secretaire")
        self.compte(None, "KAMGA", "Paul", "comptabilite@istc-demo.cm", "comptable")
        self.client = self.api(self.admin)
        assert CustomUser.objects.filter(username="admin.demo").exists()

    def compte(self, username, noms, prenoms, email, role, superuser=False):
        from users.models import CustomUser
        u = CustomUser(noms=noms, prenoms=prenoms, email=email, role=role, is_superuser=superuser, is_staff=superuser)
        if username:
            u.username = username
        u.set_password(MOT_DE_PASSE)
        u.save()
        return u

    def _structure(self):
        from academique.models import (AnneeAcademique, Classe, Cycle, Departement, Filiere, Niveau, Semestre,
                                       Specialite, UniversiteTutelle)
        from emploidutemps.models import Salle
        debut = date(self.aujourdhui.year if self.aujourdhui.month >= 9 else self.aujourdhui.year - 1, 9, 1)
        self.annee_prec = AnneeAcademique.objects.create(libelle=f"{debut.year - 1}-{debut.year}",
                                                         date_debut=debut.replace(year=debut.year - 1),
                                                         date_fin=date(debut.year, 7, 31))
        self.annee = AnneeAcademique.objects.create(libelle=f"{debut.year}-{debut.year + 1}", est_active=True,
                                                    date_debut=debut, date_fin=date(debut.year + 1, 7, 31))
        for a in (self.annee_prec, self.annee):
            Semestre.objects.create(annee_academique=a, nom="Semestre 1", ordre=1)
            Semestre.objects.create(annee_academique=a, nom="Semestre 2", ordre=2)
        univ = UniversiteTutelle.objects.create(nom="Université partenaire", code="UP")
        d1 = Departement.objects.create(nom="Sciences et Technologies", universite_tutelle=univ, code="ST")
        d2 = Departement.objects.create(nom="Commerce et Gestion", universite_tutelle=univ, code="CG")
        self.gi = Filiere.objects.create(nom="Génie Informatique", departement=d1, code="GI", responsable_nom="Dr ATANGANA")
        self.gest = Filiere.objects.create(nom="Gestion des Entreprises", departement=d2, code="GE", responsable_nom="Mme NJOYA")
        self.classes = {}
        for filiere, spec, cycle_g, n in [(self.gi, "Développement Web", self.lic, 3), (self.gi, "Réseaux et Télécoms", self.bts, 2),
                                          (self.gest, "Comptabilité et Finance", self.lic, 3)]:
            sp = Specialite.objects.create(filiere=filiere, nom=spec)
            cy = Cycle.objects.create(type_cycle=cycle_g, filiere=filiere, specialite=sp, nom=cycle_g.nom)
            for i in range(1, n + 1):
                niv = Niveau.objects.create(cycle=cy, nom=f"{cycle_g.nom} {i}", ordre=i)
                self.classes[(spec, i)] = Classe.objects.get(niveau=niv, annee_academique=self.annee)
        self.salles = [Salle.objects.create(nom=n, capacite=c) for n, c in
                       [("Salle A1", 40), ("Salle A2", 40), ("Labo Informatique", 30), ("Amphi 1", 120), ("Salle B3", 35)]]

    def _enseignants(self):
        from formateurs.models import Formateur
        from modules.models import Module
        cours = {
            ("Développement Web", 1): [("Algorithmique", 3), ("HTML / CSS", 2), ("Mathématiques discrètes", 2),
                                       ("Anglais technique", 1), ("Systèmes d'exploitation", 2)],
            ("Développement Web", 2): [("JavaScript avancé", 3), ("Bases de données", 3), ("Génie logiciel", 2)],
            ("Développement Web", 3): [("Frameworks web", 3), ("Projet tutoré", 4)],
            ("Réseaux et Télécoms", 1): [("Réseaux locaux", 3), ("Électronique", 2), ("Anglais technique RT", 1)],
            ("Réseaux et Télécoms", 2): [("Sécurité des réseaux", 3), ("Téléphonie IP", 2)],
            ("Comptabilité et Finance", 1): [("Comptabilité générale", 3), ("Droit des affaires", 2),
                                             ("Économie générale", 2), ("Bureautique", 1)],
            ("Comptabilité et Finance", 2): [("Fiscalité", 3), ("Contrôle de gestion", 2)],
            ("Comptabilité et Finance", 3): [("Audit", 3), ("Finance d'entreprise", 3)],
        }
        self.modules = {}
        for cle, liste in cours.items():
            for nom, coef in liste:
                m = Module.objects.create(nom=nom, coefficient=coef, semestre="Semestre 1", duree=40 * coef,
                                          code_ue=nom[:3].upper())
                self.classes[cle].modules.add(m)
                self.modules.setdefault(cle, []).append(m)
        profils = [("ESSOMBA Martin", "permanent", 350000, 0), ("TCHOUA Brigitte", "vacataire", 0, 6000),
                   ("MANGA Thierry", "vacataire", 0, 5000), ("BELLA Josiane", "permanent", 300000, 0),
                   ("NANA Roger", "vacataire", 0, 5500), ("OWONA Sylvie", "vacataire", 0, 4500)]
        self.formateurs = []
        for i, (nom, typ, sal, taux) in enumerate(profils):
            nm, pr = nom.split(" ", 1)
            user = self.compte("formateur.demo" if i == 0 else None, nm, pr,
                               f"{pr.lower()}.{nm.lower()}@istc-demo.cm", "formateur")
            f = Formateur.objects.create(user=user, nom=nom, email=user.email, contact=f"6 77 0{i} 12 34",
                                         type_formateur=typ, salaire=Decimal(sal), taux_horaire=Decimal(taux))
            self.formateurs.append(f)
        self.coordo = self.formateurs[0]
        from vacations.models import Coordination
        Coordination.objects.create(formateur=self.coordo, filiere=self.gi, date_debut=self.annee.date_debut)
        # spécialités (modules enseignables)
        tous = [m for ms in self.modules.values() for m in ms]
        for k, f in enumerate(self.formateurs):
            f.specialites.set(tous[k::len(self.formateurs)])

    def _etudiants(self):
        from etudiants.models import Etudiant, Inscription, SanctionDisciplinaire
        self.etudiants = {}
        n = 0
        repartition = {("Développement Web", 1): 9, ("Développement Web", 2): 5, ("Développement Web", 3): 3,
                       ("Réseaux et Télécoms", 1): 4, ("Réseaux et Télécoms", 2): 2,
                       ("Comptabilité et Finance", 1): 6, ("Comptabilité et Finance", 2): 3, ("Comptabilité et Finance", 3): 2}
        for cle, nb in repartition.items():
            classe = self.classes[cle]
            for _ in range(nb):
                nom = self.personne(n)
                e = Etudiant.objects.create(
                    nom=nom, contact=f"6 9{n % 10} {10 + n:02d} {20 + n:02d} {30 + n:02d}",
                    email=f"etudiant{n + 1}@demo.cm", filiere=classe.filiere, statut="Inscrit",
                    date_naissance=date(2004 + n % 4, 1 + n % 12, 1 + n % 27),
                    nom_parent=f"{nom.split()[0]} {PRENOMS[(n * 3) % len(PRENOMS)]}",
                    whatsapp_parent=f"+237 6 7{n % 10} {40 + n:02d} {50 + n:02d} 00")
                e.refresh_from_db()
                Inscription.objects.create(etudiant=e, classe=classe, niveau=classe.niveau,
                                           annee_academique=self.annee.libelle, annee_academique_ref=self.annee)
                self.etudiants.setdefault(cle, []).append(e)
                n += 1
        self.demo = self.etudiants[("Développement Web", 1)][0]
        u = self.demo.user
        u.username = "etudiant.demo"
        u.set_password(MOT_DE_PASSE)
        u.save()
        self.demo.initial_password = MOT_DE_PASSE
        self.demo.save(update_fields=["initial_password"])
        SanctionDisciplinaire.objects.create(etudiant=self.etudiants[("Développement Web", 1)][3],
                                             type_sanction="Avertissement", motif="Retards répétés",
                                             date_sanction=self.aujourdhui - timedelta(days=12), active=True)

    def _emploi_du_temps(self):
        from emploidutemps.models import EmploiDuTemps
        plages = [(time(8, 0), time(10, 0)), (time(10, 15), time(12, 0)), (time(13, 30), time(15, 30)),
                  (time(15, 45), time(17, 45))]
        jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
        self.seances = []
        ens_par_module = {}
        for k, (cle, mods) in enumerate(self.modules.items()):
            classe = self.classes[cle]
            prof = self.formateurs
            for j, m in enumerate(mods):
                f = ens_par_module.setdefault(m.id, prof[(k + j) % len(prof)])
                for rep in range(2 if m.coefficient >= 3 else 1):
                    jour = jours[(k + j + rep * 2) % 5]
                    debut, fin = plages[(j + rep) % 4]
                    salle = self.salles[(k + j + rep) % len(self.salles)]
                    s = EmploiDuTemps(classe=classe, module=m, formateur=f, salle=salle, jour=jour,
                                      heure_debut=debut, heure_fin=fin)
                    try:
                        s.full_clean()
                    except Exception:
                        continue
                    s.save()
                    self.seances.append(s)

    def _finances(self):
        from paiements.models import Bourse, ClassePaymentInstallment, ClassePaymentSchedule, Frais
        base = {"Développement Web": 450000, "Réseaux et Télécoms": 400000, "Comptabilité et Finance": 380000}
        rentree = self.annee.date_debut
        for (spec, i), classe in self.classes.items():
            total = Decimal(base[spec] + 25000 * (i - 1))
            Frais.objects.create(classe=classe, libelle="Frais d'inscription", montant=Decimal(30000), obligatoire=True)
            sch = ClassePaymentSchedule.objects.create(classe=classe, total_amount=total)
            tranche = (total / 4).quantize(Decimal("1"))
            for t in range(4):
                due = rentree + timedelta(days=30 + 60 * t)
                montant = tranche if t < 3 else total - 3 * tranche
                Frais.objects.create(classe=classe, libelle=f"Tranche {t + 1}", montant=montant, date_echeance=due)
                ClassePaymentInstallment.objects.create(schedule=sch, order=t + 1, label=f"Tranche {t + 1}",
                                                        due_date=due, amount_due=montant)
        Bourse.objects.create(code="EXCELLENCE-2026", description="Bourse d'excellence (major de promotion)",
                              montant=Decimal(100000))
        Bourse.objects.create(code="SOCIALE-01", description="Bourse sociale", montant=Decimal(75000))
        moyens = ["cash", "orange_money", "mobile_money", "virement", "cheque"]
        for k, etus in enumerate(self.etudiants.values()):
            for j, e in enumerate(etus):
                self.payer(e, "INSCRIPTION", 30000, moyens[j % 5])
                profil = (j + k) % 4  # 0 : soldé partiel élevé ; 3 : rien payé en formation
                montant = [250000, 150000, 100000, 0][profil]
                if e == self.demo:
                    montant = 150000
                if montant:
                    self.payer(e, "FORMATION", montant, moyens[(j + 1) % 5])

    def payer(self, etudiant, type_, montant, moyen):
        from paiements.models import Frais
        classe = etudiant.inscriptions.first().classe
        frais = Frais.objects.filter(classe=classe, libelle__icontains="inscription").first() if type_ == "INSCRIPTION" \
            else Frais.objects.filter(classe=classe, libelle="Tranche 1").first()
        data = {"etudiant": etudiant.id, "paiement_type": type_, "montant_paye": str(montant),
                "moyen_paiement": moyen, "frais": frais.id,
                "justificatif": ContentFile(pdf_factice(f"Recu {etudiant.matricule}"), name="recu.pdf")}
        self.ok(self.client.post("/api/paiements/", data, format="multipart"))

    def _notes_et_assiduite(self):
        from assiduite.models import AssiduiteRecord
        from notes.models import Note
        for cle, etus in self.etudiants.items():
            mods = self.modules[cle]
            for j, m in enumerate(mods):
                for k, e in enumerate(etus):
                    cc = Decimal(random.randint(9, 28))
                    sn = Decimal(random.randint(22, 66))
                    if (k + j) % 7 == 3:
                        sn = Decimal(random.randint(15, 25))  # quelques rattrapages
                    # La note (vide) a été créée par l'inscription : on la complète.
                    Note.objects.update_or_create(
                        etudiant=e, module=m, classe=self.classes[cle], session="Semestre 1", evaluation=None,
                        defaults=dict(annee_academique=self.annee.libelle, annee_academique_ref=self.annee,
                                      note_cc=cc, note_sn=sn, validee=(j != len(mods) - 1)))
        etus = self.etudiants[("Développement Web", 1)]
        mods = self.modules[("Développement Web", 1)]
        for k in range(10):
            r = AssiduiteRecord(etudiant=etus[k % len(etus)], module=mods[k % len(mods)],
                                date=self.aujourdhui - timedelta(days=2 + k * 2),
                                type="RETARD" if k % 3 == 0 else "ABSENCE",
                                minutes_retard=15 if k % 3 == 0 else 0, justifie=(k % 4 == 1))
            if r.justifie:
                r.justificatif.save(f"justificatif_{k}.pdf", ContentFile(pdf_factice("Certificat medical")), save=False)
            r.save()

    def _vacations(self):
        """Pointages : mois précédent (clôturé, en partie validé) et mois en cours (en cours de saisie)."""
        from vacations.models import PointageEnseignant, RecapMensuel
        jours = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi"}
        debut_mois = self.aujourdhui.replace(day=1)
        mois_prec_fin = debut_mois - timedelta(days=1)
        mois_prec_debut = mois_prec_fin.replace(day=1)
        seances_gi = [s for s in self.seances if s.classe.filiere_id == self.gi.id]
        j = max(mois_prec_debut, self.annee.date_debut)
        idx = 0
        while j < self.aujourdhui:
            if j.weekday() < 5:
                for s in seances_gi:
                    if s.jour != jours[j.weekday()]:
                        continue
                    idx += 1
                    absent = idx % 17 == 0
                    retard = [0, 5, 10, 0, 15][idx % 5]
                    arrivee = (timezone.datetime.combine(j, s.heure_debut) + timedelta(minutes=retard)).time()
                    fin = (timezone.datetime.combine(j, s.heure_fin) - timedelta(minutes=[0, 5, 0, 10][idx % 4])).time()
                    if j >= self.aujourdhui - timedelta(days=1) and idx % 2:
                        continue  # séances récentes pas encore pointées
                    PointageEnseignant.objects.create(
                        formateur=s.formateur, filiere=self.gi, classe=s.classe, module=s.module, seance=s, date=j,
                        heure_debut_prevue=s.heure_debut, heure_fin_prevue=s.heure_fin,
                        heure_arrivee=None if absent else arrivee, heure_fin=None if absent else fin,
                        statut="absent" if absent else "present", saisi_par=self.coordo.user,
                        commentaire="Absent, cours à reprogrammer" if absent else "")
            j += timedelta(days=1)
        coord_client = self.api(self.coordo.user)
        m, a = mois_prec_debut.month, mois_prec_debut.year
        recaps = coord_client.get("/api/vacations/coordonnateur/recaps/", {"mois": m, "annee": a, "filiere": self.gi.id})
        self.ok(recaps)
        self.ok(coord_client.post(f"/api/vacations/coordonnateur/recaps/cloturer-tout/?mois={m}&annee={a}&filiere={self.gi.id}",
                                  {"mois": m, "annee": a, "filiere": self.gi.id}, format="json"))
        vac = [r for r in RecapMensuel.objects.filter(mois=m, annee=a, statut="cloture")
               if r.formateur.type_formateur == "vacataire"]
        for r in vac[:2]:
            self.ok(self.client.post(f"/api/vacations/recaps/{r.id}/valider/", {}, format="json"))
        self.mois_prec = (m, a)

    def _rh_et_paie(self):
        from conges.models import Conge
        from paie.models import AvanceSalaire, Prime, Retenue
        from personnels.models import Personnel
        agents = [("NJOYA Clarisse", "responsableRh", 320000, 2018), ("FOTSO Bernard", "responsablePedagogique", 380000, 2016),
                  ("ELLA Marthe", "responsableLogistique", 250000, 2020), ("ZANG Pierre", "responsableMarketing", 280000, 2021),
                  ("ABENA Rose", "femmeMenage", 90000, 2019), ("MOUKOKO Eric", "stagiaire", 60000, self.aujourdhui.year)]
        self.agents = []
        for i, (nom, fct, sal, an) in enumerate(agents):
            self.agents.append(Personnel.objects.create(nom=nom, contact=f"6 55 0{i} 11 22", fonction=fct,
                                                        salaire=Decimal(sal), date_embauche=date(an, 2, 1),
                                                        solde_conges_initial=18))
        ct = ContentType.objects.get_for_model(Personnel)
        Prime.objects.create(beneficiaire_content_type=ct, beneficiaire_object_id=self.agents[0].id, type_prime="transport",
                             montant=Decimal(25000))
        Prime.objects.create(beneficiaire_content_type=ct, beneficiaire_object_id=self.agents[1].id,
                             type_prime="responsabilite", montant=Decimal(40000))
        for a in self.agents[:5]:
            Retenue.objects.create(beneficiaire_content_type=ct, beneficiaire_object_id=a.id, type_retenue="cnps",
                                   montant=(a.salaire * Decimal("0.042")).quantize(Decimal("1")))
        AvanceSalaire.objects.create(beneficiaire_content_type=ct, beneficiaire_object_id=self.agents[2].id,
                                     montant_total=Decimal(90000), nombre_echeances=3, motif="Frais médicaux")
        lundi = self.aujourdhui + timedelta(days=(7 - self.aujourdhui.weekday()) % 7 + 7)
        Conge.objects.create(personnel=self.agents[0], date_debut=lundi, date_fin=lundi + timedelta(days=4),
                             type_conge="Annuel", raison="Congé annuel", statut="accepte")
        Conge.objects.create(personnel=self.agents[3], date_debut=lundi + timedelta(days=14),
                             date_fin=lundi + timedelta(days=16), type_conge="Annuel", statut="en_attente")
        m, a = self.mois_prec
        res = self.ok(self.client.post("/api/paie/campagnes/generer/",
                                       {"mois": m, "annee": a, "type_beneficiaire": "personnel"}, format="json"))
        cid = res.data["id"]
        self.ok(self.client.post(f"/api/paie/campagnes/{cid}/valider/"))
        self.ok(self.client.post(f"/api/paie/campagnes/{cid}/payer/"))
        self.ok(self.client.post("/api/paie/campagnes/generer/",
                                 {"mois": m, "annee": a, "type_beneficiaire": "formateur"}, format="json"))
        from revenus.models import Revenu
        Revenu.objects.create(libelle="Location de l'amphi (séminaire)", montant=Decimal(150000), categorie="Location",
                              date_entree=self.aujourdhui - timedelta(days=20), statut="Validé", responsable="Direction")
        Revenu.objects.create(libelle="Subvention partenaire", montant=Decimal(1000000), categorie="Subvention",
                              date_entree=self.aujourdhui - timedelta(days=35), statut="Validé", responsable="Direction")

    def _logistique(self):
        from formateurs.models import Formateur
        c = self.client
        arts = [("Vidéoprojecteur Epson", "Électronique", 4, 350000), ("Ordinateur portable HP", "Informatique", 12, 420000),
                ("Chaise étudiant", "Mobilier", 120, 15000), ("Rame de papier A4", "Papeterie", 40, 3500),
                ("Switch réseau 24 ports", "Informatique", 3, 180000)]
        ids = []
        for nom, cat, q, prix in arts:
            r = self.ok(c.post("/api/inventaires/articles/", {"nom": nom, "categorie": cat, "quantite_initiale": q,
                                                              "prix_unitaire": prix, "seuil_alerte": 2,
                                                              "fournisseur": "Fournisseur Démo SARL"}, format="json"))
            ids.append(r.data["id"])
        ct = ContentType.objects.get_for_model(Formateur).id
        for k, (objet, art, q, etapes) in enumerate([("Cours de réseaux", 4, 1, ("soumettre", "approuver", "livrer")),
                                                      ("Soutenances de projet", 0, 1, ("soumettre",)),
                                                      ("Atelier bureautique", 1, 3, ())]):
            self.ok(c.post("/api/demandes/", {"objet": objet, "priorite": "normale", "motif": "Besoin pédagogique",
                                              "demandeur_content_type": ct,
                                              "demandeur_object_id": self.formateurs[k].id,
                                              "lignes": [{"article": ids[art], "quantite_demandee": q}]}, format="json"))
            did = c.get("/api/demandes/").data[0]["id"]
            for e in etapes:
                self.ok(c.post(f"/api/demandes/{did}/{e}/", {}, format="json"))
        from depenses.models import Depense
        from personnels.models import Personnel
        pct = ContentType.objects.get_for_model(Personnel)
        for lib, mt, cat in [("Entretien climatiseurs", 85000, "Entretien"), ("Achat de marqueurs", 25000, "Materiel"),
                             ("Transport sortie pédagogique", 120000, "Activites")]:
            Depense.objects.create(libelle=lib, montant=Decimal(mt), categorie=cat, statut="Validée",
                                   date_depense=self.aujourdhui - timedelta(days=random.randint(3, 25)),
                                   responsable_content_type=pct, responsable_object_id=self.agents[2].id)

    def _preinscriptions(self):
        from academique.models import PreInscription
        cands = [("ONANA", "Bertrand", ("Développement Web", 1)), ("MBIDA", "Carole", ("Comptabilité et Finance", 1)),
                 ("NKENG", "Daniel", ("Réseaux et Télécoms", 1)), ("EYENGA", "Flore", ("Développement Web", 1))]
        for i, (nom, prenom, cle) in enumerate(cands):
            cl = self.classes[cle]
            PreInscription.objects.create(
                nom_candidat=nom, prenom_candidat=prenom, email=f"{prenom.lower()}.{nom.lower()}@candidat.cm",
                telephone=f"6 98 0{i} 45 67", date_naissance=date(2006, 3 + i, 10), filiere_souhaitee=cl.filiere,
                specialite_souhaitee=cl.specialite, cycle_souhaite=cl.cycle, niveau_souhaite=cl.niveau,
                classe_souhaitee=cl, annee_academique=self.annee, nom_parent=f"{nom} Jean",
                whatsapp_parent=f"+237 6 99 0{i} 00 11", relation_parent1="Père")

    def _documents(self):
        from academique.models import Epreuve, Semestre
        from formateurs.models import CoursDocument
        cle = ("Développement Web", 1)
        sem = Semestre.objects.get(annee_academique=self.annee, nom="Semestre 1")
        for k, m in enumerate(self.modules[cle][:3]):
            e = Epreuve(nom=f"Examen de {m.nom} — session 1", filiere=self.gi, niveau=self.classes[cle].niveau, module=m,
                        annee_academique=self.annee, semestre=sem, type_epreuve="EXAMEN",
                        auteur=self.formateurs[k].nom, est_partage=True)
            e.fichier.save(f"sujet_{k}.pdf", ContentFile(pdf_factice(f"Sujet {m.nom}")), save=False)
            e.corrige.save(f"corrige_{k}.pdf", ContentFile(pdf_factice(f"Corrige {m.nom}")), save=False)
            e.save()
            doc = CoursDocument(formateur=self.coordo, module=m, titre=f"Support de cours — {m.nom}",
                                description="Chapitres 1 à 3", est_visible_etudiants=True)
            doc.fichier.save(f"cours_{k}.pdf", ContentFile(pdf_factice(f"Cours {m.nom}")), save=False)
            doc.save()
