from rest_framework import serializers
from .models import EmploiDuTemps, Salle, EmploiDuTempsDocument
from academique.models import Filiere, Niveau

class SalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Salle
        fields = "__all__"

class EmploiDuTempsSerializer(serializers.ModelSerializer):
    filiere_nom = serializers.CharField(source="filiere.nom", read_only=True)
    niveau_nom = serializers.CharField(source="niveau.nom", read_only=True)
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)
    module_nom = serializers.CharField(source="module.nom", read_only=True)
    formateur_nom = serializers.CharField(source="formateur.nom", read_only=True)
    salle_nom = serializers.CharField(source="salle.nom", read_only=True)

    filiere = serializers.PrimaryKeyRelatedField(queryset=Filiere.objects.all(), required=False, allow_null=True)
    niveau = serializers.PrimaryKeyRelatedField(queryset=Niveau.objects.all(), required=False, allow_null=True)
    salle = serializers.PrimaryKeyRelatedField(queryset=Salle.objects.all())

    class Meta:
        model = EmploiDuTemps
        fields = "__all__"

    def validate(self, data):
        """
        Règles métier (pause, horaires du cycle, conflits salle / classe / formateur).

        Elles sont définies une seule fois dans `EmploiDuTemps.clean()` : le serializer
        construit une instance candidate et délègue la validation au modèle, puis convertit
        l'erreur en réponse 400. (Avant, les mêmes règles étaient recopiées ici et avaient
        divergé : les conflits n'étaient pas limités à l'année académique.)
        """
        from django.core.exceptions import ValidationError as DjangoValidationError

        valeurs = {}
        if self.instance is not None:
            valeurs = {f.name: getattr(self.instance, f.name) for f in EmploiDuTemps._meta.concrete_fields}
        valeurs.update(data)
        candidat = EmploiDuTemps(**valeurs)
        if candidat.classe_id:
            candidat.niveau = candidat.classe.niveau
            candidat.filiere = candidat.classe.filiere
        try:
            candidat.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"non_field_errors": exc.messages})
        return data


class EmploiDuTempsDocumentSerializer(serializers.ModelSerializer):
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)
    filiere_nom = serializers.CharField(source="classe.filiere.nom", read_only=True, default="")
    niveau_nom = serializers.CharField(source="classe.niveau.nom", read_only=True, default="")
    annee_academique_libelle = serializers.CharField(source="classe.annee_academique.libelle", read_only=True, default="")
    extension = serializers.ReadOnlyField()
    is_pdf = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()

    class Meta:
        model = EmploiDuTempsDocument
        fields = [
            "id",
            "titre",
            "classe",
            "classe_nom",
            "filiere_nom",
            "niveau_nom",
            "annee_academique_libelle",
            "fichier",
            "description",
            "date_effective",
            "est_actif",
            "extension",
            "is_pdf",
            "is_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 Mo

    def validate_fichier(self, value):
        import os
        ext = os.path.splitext(value.name)[1].lower().lstrip(".")
        if ext not in self.ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                "Format non autorisé. Formats acceptés : PDF, PNG, JPG, JPEG, WEBP."
            )
        if value.size > self.MAX_FILE_SIZE:
            raise serializers.ValidationError("Le fichier dépasse la taille maximale de 10 Mo.")
        return value

