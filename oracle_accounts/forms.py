# oracle_accounts/forms.py
from django import forms
from django.core.exceptions import ValidationError

from .models import OracleCredential


class OracleCredentialForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Laisser vide pour conserver le mot de passe actuel.",
    )

    class Meta:
        model = OracleCredential
        fields = ["label", "host", "port", "service_name", "username", "password", "enabled", "current"]
        widgets = {
            "enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "current": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["password"].help_text = "Mot de passe Oracle requis."

    def clean_password(self) -> str:
        password = (self.cleaned_data.get("password") or "").strip()
        if not password and not self.instance.pk:
            raise ValidationError("Le mot de passe Oracle est requis.")
        return password

    def save(self, commit=True):
        obj = super().save(commit=False)
        password = self.cleaned_data.get("password")

        if password:
            obj.set_password(password)

        if commit:
            obj.save()
        return obj
