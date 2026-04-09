from __future__ import annotations

from .models import OracleCredential
from .services import SESSION_KEY


def oracle_credentials_nav(request):
    """
    Injecté partout dans les templates :
    - ORACLE_CREDS: liste des creds disponibles pour l'utilisateur courant
    - ORACLE_CURRENT_CRED: cred courant (selon session) ou fallback (1er enabled)
    """
    if not request.user.is_authenticated:
        return {"ORACLE_CREDS": [], "ORACLE_CURRENT_CRED": None}

    qs = OracleCredential.objects.filter(user=request.user).order_by("-enabled", "-updated_at", "-id")
    creds = list(qs)

    current_id = request.session.get(SESSION_KEY)
    current = next((c for c in creds if c.id == current_id), None)

    if current is None:
        # fallback : premier enabled, sinon premier tout court
        current = next((c for c in creds if c.enabled), None) or (creds[0] if creds else None)
        if current:
            request.session[SESSION_KEY] = current.id

    return {"ORACLE_CREDS": creds, "ORACLE_CURRENT_CRED": current}
