# etudiants/serializers.py
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from .models import Etudiant, EtudiantDocument, Inscription, SanctionDisciplinaire
from academique.models import Filiere, Cycle, Niveau, Classe, AnneeAcademique
from academique.serializers import FiliereSerializer

# --- Documents liés aux étudiants ---
class EtudiantDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtudiantDocument
        fields = ["id", "type_document", "fichier", "date_upload"]


class SanctionDisciplinaireSerializer(serializers.ModelSerializer):
    """Version imbriquée dans la fiche étudiant et le portail (lecture seule)."""
    etat = serializers.CharField(read_only=True)

    class Meta:
        model = SanctionDisciplinaire
        fields = ["id", "type_sanction", "motif", "date_sanction", "date_fin", "duree", "active", "etat",
                  "date_levee", "motif_levee"]


def _nom_compte(user):
    if not user:
        return ""
    return " ".join(p for p in [user.noms, user.prenoms] if p).strip() or user.username


class SanctionGestionSerializer(serializers.ModelSerializer):
    """Gestion des sanctions par la scolarité (droit Étudiants en écriture)."""
    etat = serializers.CharField(read_only=True)
    etudiant_nom = serializers.CharField(source="etudiant.nom", read_only=True)
    etudiant_matricule = serializers.CharField(source="etudiant.matricule", read_only=True)
    etudiant_contact = serializers.CharField(source="etudiant.contact", read_only=True)
    nom_parent = serializers.CharField(source="etudiant.nom_parent", read_only=True)
    whatsapp_parent = serializers.CharField(source="etudiant.whatsapp_parent", read_only=True)
    classe_nom = serializers.SerializerMethodField()
    enregistree_par_nom = serializers.SerializerMethodField()
    levee_par_nom = serializers.SerializerMethodField()

    class Meta:
        model = SanctionDisciplinaire
        fields = ["id", "etudiant", "etudiant_nom", "etudiant_matricule", "etudiant_contact", "nom_parent",
                  "whatsapp_parent", "classe_nom", "type_sanction", "motif", "date_sanction", "date_fin", "duree",
                  "active", "etat", "date_levee", "motif_levee", "levee_par_nom", "enregistree_par_nom",
                  "created_at", "updated_at"]
        read_only_fields = ["active", "date_levee", "motif_levee", "created_at", "updated_at"]

    def get_classe_nom(self, obj):
        inscription = obj.etudiant.inscriptions.select_related("classe").order_by("-date_inscription").first()
        return getattr(getattr(inscription, "classe", None), "nom", "") or ""

    def get_enregistree_par_nom(self, obj):
        return _nom_compte(obj.enregistree_par)

    def get_levee_par_nom(self, obj):
        return _nom_compte(obj.levee_par)

    def validate_motif(self, value):
        if len((value or "").strip()) < 5:
            raise serializers.ValidationError("Décrivez le motif (au moins 5 caractères).")
        return value.strip()

    def validate_date_sanction(self, value):
        from django.utils import timezone
        if value and value > timezone.localdate():
            raise serializers.ValidationError("La date de la sanction ne peut pas être dans le futur.")
        return value

    def validate(self, attrs):
        instance = self.instance
        if instance is not None and "etudiant" in attrs and attrs["etudiant"] != instance.etudiant:
            raise serializers.ValidationError({"etudiant": "Une sanction ne change pas d'étudiant."})
        type_sanction = attrs.get("type_sanction", getattr(instance, "type_sanction", None))
        date_sanction = attrs.get("date_sanction", getattr(instance, "date_sanction", None))
        date_fin = attrs.get("date_fin", getattr(instance, "date_fin", None))
        if type_sanction == SanctionDisciplinaire.EXCLUSION_TEMPORAIRE:
            if not date_fin:
                raise serializers.ValidationError({"date_fin": "Indiquez le dernier jour de l'exclusion."})
            if date_sanction and date_fin < date_sanction:
                raise serializers.ValidationError({"date_fin": "La fin doit être après le début de l'exclusion."})
            jours = (date_fin - date_sanction).days + 1 if date_sanction else None
            if jours:
                attrs["duree"] = f"{jours} jour{'s' if jours > 1 else ''}"
        else:
            attrs["date_fin"] = None
            attrs["duree"] = None
        return attrs


# --- Inscriptions ---
class InscriptionSerializer(serializers.ModelSerializer):
    classe_nom = serializers.CharField(source='classe.nom', read_only=True)
    niveau_nom = serializers.CharField(source='niveau.nom', read_only=True)
    filiere_nom = serializers.CharField(source='niveau.cycle.filiere.nom', read_only=True)
    cycle_id = serializers.IntegerField(source="niveau.cycle_id", read_only=True)
    cycle_nom = serializers.CharField(source="niveau.cycle.nom", read_only=True)
    annee_academique_ref_libelle = serializers.CharField(source='annee_academique_ref.libelle', read_only=True)

    class Meta:
        model = Inscription
        fields = [
            'id',
            'etudiant',
            'classe',
            'classe_nom',
            'niveau',
            'niveau_nom',
            'filiere_nom',
            'cycle_id',
            'cycle_nom',
            'annee_academique',
            'annee_academique_ref',
            'annee_academique_ref_libelle',
            'date_inscription',
        ]


# --- Étudiant ---
class EtudiantSerializer(serializers.ModelSerializer):
    # Lecture
    filiere_details = FiliereSerializer(source="filiere", read_only=True)
    
    # Écriture
    filiere_id = serializers.PrimaryKeyRelatedField(
        queryset=Filiere.objects.all(),
        source="filiere",
        write_only=True
    )
    cycle_id = serializers.PrimaryKeyRelatedField(
        queryset=Cycle.objects.all(),
        write_only=True,
        required=False,
    )
    niveau_id = serializers.IntegerField(write_only=True, required=False)
    classe_id = serializers.IntegerField(write_only=True, required=False)
    annee_academique_ref_id = serializers.IntegerField(write_only=True, required=False)

    # Lecture seule
    documents = EtudiantDocumentSerializer(many=True, read_only=True)
    inscriptions = InscriptionSerializer(many=True, read_only=True)
    sanctions = SanctionDisciplinaireSerializer(many=True, read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Etudiant
        fields = [
            "id",
            "matricule",
            "nom",
            "date_naissance",
            "contact",
            "email",
            "nom_parent",
            "whatsapp_parent",
            "filiere_details",
            "filiere_id",
            "cycle_id",
            "niveau_id",
            "classe_id",
            "annee_academique_ref_id",
            "statut",
            "documents",
            "inscriptions",
            "sanctions",
            "username",
            "initial_password",
        ]
        # Généré automatiquement à la création du compte : jamais modifiable via l'API.
        read_only_fields = ["matricule", "initial_password"]

    def create(self, validated_data):
        try:
            return self._create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(getattr(exc, "message_dict", None) or {"non_field_errors": exc.messages})

    def update(self, instance, validated_data):
        try:
            return self._update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(getattr(exc, "message_dict", None) or {"non_field_errors": exc.messages})

    @transaction.atomic
    def _create(self, validated_data):
        validated_data.pop('cycle_id', None)
        niveau_id = validated_data.pop('niveau_id', None)
        classe_id = validated_data.pop('classe_id', None)
        annee_academique_ref_id = validated_data.pop('annee_academique_ref_id', None)

        etudiant = super().create(validated_data)

        if classe_id:
            try:
                classe = Classe.objects.get(pk=classe_id)
                annee = classe.annee_academique
                if annee_academique_ref_id:
                    annee = AnneeAcademique.objects.get(pk=annee_academique_ref_id)
                Inscription.objects.create(
                    etudiant=etudiant,
                    classe=classe,
                    niveau=classe.niveau,
                    annee_academique=annee.libelle,
                    annee_academique_ref=annee,
                )
            except (Classe.DoesNotExist, AnneeAcademique.DoesNotExist):
                pass
        elif niveau_id:
            try:
                niveau = Niveau.objects.get(pk=niveau_id)
                annee = AnneeAcademique.objects.filter(est_active=True).first()
                if annee is None:
                    raise serializers.ValidationError({"niveau_id": "Aucune année académique active n'est configurée."})
                Inscription.objects.create(
                    etudiant=etudiant,
                    niveau=niveau,
                    annee_academique=annee.libelle,
                    annee_academique_ref=annee
                )
            except Niveau.DoesNotExist:
                pass

        return etudiant

    @transaction.atomic
    def _update(self, instance, validated_data):
        validated_data.pop('cycle_id', None)
        validated_data.pop('niveau_id', None)
        classe_id = validated_data.pop('classe_id', None)
        annee_academique_ref_id = validated_data.pop('annee_academique_ref_id', None)

        instance = super().update(instance, validated_data)

        if classe_id:
            try:
                classe = Classe.objects.get(pk=classe_id)
                annee = classe.annee_academique
                if annee_academique_ref_id:
                    annee = AnneeAcademique.objects.get(pk=annee_academique_ref_id)
                inscription = instance.inscriptions.filter(annee_academique_ref=annee).first()
                if inscription:
                    # save() (et non update()) : recalcule niveau/année et déclenche la
                    # création des notes des modules de la nouvelle classe.
                    inscription.classe = classe
                    inscription.niveau = classe.niveau
                    inscription.save()
                else:
                    Inscription.objects.create(
                        etudiant=instance,
                        classe=classe,
                        niveau=classe.niveau,
                        annee_academique=annee.libelle,
                        annee_academique_ref=annee,
                    )
            except (Classe.DoesNotExist, AnneeAcademique.DoesNotExist):
                pass

        return instance
