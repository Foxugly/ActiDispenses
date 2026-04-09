from django import forms
from django.core.exceptions import ValidationError

from .sql_guard import validate_allowed_query_sources

READ_ONLY_SQL_PREFIXES = ("select", "with")
COMMENT_TOKENS = ("--", "/*", "*/")
FORBIDDEN_PATTERNS = (
    " insert ",
    " update ",
    " delete ",
    " merge ",
    " alter ",
    " drop ",
    " truncate ",
    " create ",
    " grant ",
    " revoke ",
    " execute ",
    " commit ",
    " rollback ",
    " for update",
    " lock table ",
)
FORBIDDEN_WITH_PREFIXES = ("with function", "with procedure")


class QueryForm(forms.Form):
    query = forms.CharField(
        label="Requete SQL",
        required=True,
        widget=forms.Textarea(attrs={"rows": 8, "placeholder": "SELECT ..."}),
    )

    def clean_query(self) -> str:
        query = (self.cleaned_data["query"] or "").strip()
        normalized = query.rstrip(";").strip()
        lowered = normalized.lower()

        if not lowered.startswith(READ_ONLY_SQL_PREFIXES):
            raise ValidationError("Seules les requetes SELECT et WITH sont autorisees.")
        if ";" in normalized:
            raise ValidationError("Les requetes multiples ne sont pas autorisees.")
        if any(token in normalized for token in COMMENT_TOKENS):
            raise ValidationError("Les commentaires SQL ne sont pas autorises.")
        if lowered.startswith(FORBIDDEN_WITH_PREFIXES):
            raise ValidationError("Les blocs WITH FUNCTION/PROCEDURE ne sont pas autorises.")

        padded = f" {lowered} "
        if any(keyword in padded for keyword in FORBIDDEN_PATTERNS):
            raise ValidationError("La requete contient des mots-cles interdits.")

        validate_allowed_query_sources(normalized)
        return normalized
