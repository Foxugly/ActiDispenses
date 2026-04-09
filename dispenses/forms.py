import re

from django import forms
from django.core.exceptions import ValidationError

FIELD_PATTERNS = {
    "no_ibis": (
        re.compile(r"^[A-Za-z0-9]{1,20}$"),
        "Le NO_IBIS doit contenir uniquement des lettres et des chiffres.",
    ),
    "id_demandeur": (re.compile(r"^\d{1,20}$"), "L'ID_DEMANDEUR doit contenir uniquement des chiffres."),
    "niss": (re.compile(r"^\d{11}$"), "Le NISS doit contenir exactement 11 chiffres."),
    "id_dispense": (re.compile(r"^\d{1,20}$"), "L'ID dispense doit contenir uniquement des chiffres."),
    "no_dispense": (re.compile(r"^\d{1,20}$"), "Le numero de dispense doit contenir uniquement des chiffres."),
}


class DispenseSearchForm(forms.Form):
    no_ibis = forms.CharField(label="NO_IBIS", required=False, max_length=20)
    id_demandeur = forms.CharField(label="ID_DEMANDEUR", required=False, max_length=20)
    niss = forms.CharField(label="NISS", required=False, max_length=15)
    id_dispense = forms.CharField(required=False, label="ID dispense", max_length=20)
    no_dispense = forms.CharField(required=False, label="No dispense", max_length=20)

    def clean(self):
        cleaned = super().clean()
        no_ibis = (cleaned.get("no_ibis") or "").strip()
        id_demandeur = (cleaned.get("id_demandeur") or "").strip()
        niss = (cleaned.get("niss") or "").strip()
        id_dispense = (cleaned.get("id_dispense") or "").strip()
        no_dispense = (cleaned.get("no_dispense") or "").strip()

        provided = [
            (key, value)
            for key, value in [
                ("no_ibis", no_ibis),
                ("id_demandeur", id_demandeur),
                ("niss", niss),
                ("id_dispense", id_dispense),
                ("no_dispense", no_dispense),
            ]
            if value
        ]

        if len(provided) == 0:
            raise ValidationError("Tu dois completer exactement 1 champ.")
        if len(provided) > 1:
            raise ValidationError("Un seul champ doit etre complete.")

        field_name, field_value = provided[0]
        pattern, message = FIELD_PATTERNS[field_name]
        if not pattern.match(field_value):
            self.add_error(field_name, message)
            raise ValidationError("Le format du champ recherche est invalide.")

        cleaned["no_ibis"] = no_ibis
        cleaned["id_demandeur"] = id_demandeur
        cleaned["niss"] = niss
        cleaned["id_dispense"] = id_dispense
        cleaned["no_dispense"] = no_dispense
        cleaned["search_key"], cleaned["search_value"] = field_name, field_value
        return cleaned
