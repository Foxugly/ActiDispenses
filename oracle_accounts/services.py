from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import OracleCredential

SESSION_KEY = "oracle_cred_id"


def get_current_oracle_credential(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    cred_id = request.session.get(SESSION_KEY)
    qs = OracleCredential.objects.filter(user=request.user, enabled=True)

    if cred_id:
        cred = qs.filter(id=cred_id).first()
        if cred:
            return cred

    cred = qs.filter(current=True).first()
    if cred:
        request.session[SESSION_KEY] = cred.id
        return cred

    cred = qs.order_by("-updated_at", "-id").first()
    if not cred:
        raise PermissionDenied("No Oracle credential configured")

    request.session[SESSION_KEY] = cred.id
    return cred


def set_current_oracle_credential(request, cred: OracleCredential) -> None:
    with transaction.atomic():
        OracleCredential.objects.filter(user=request.user, current=True).exclude(pk=cred.pk).update(current=False)
        if not cred.current:
            cred.current = True
            cred.save(update_fields=["current", "updated_at"])

    request.session[SESSION_KEY] = cred.id
