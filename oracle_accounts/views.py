# oracle_accounts/views.py
from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from config.metrics import increment_metric
from dispenses.services.oracle import connect_with_credential

from .forms import OracleCredentialForm
from .models import OracleCredential
from .services import set_current_oracle_credential

logger = logging.getLogger(__name__)


class OwnerOrStaffQuerysetMixin:
    request: HttpRequest

    def get_queryset(self):
        qs = OracleCredential.objects.select_related("user")
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset or self.get_queryset())  # type: ignore[misc]
        if not self.request.user.is_staff and obj.user_id != self.request.user.id:
            raise PermissionDenied("Accès interdit.")
        return obj


class OracleCredentialListView(LoginRequiredMixin, ListView):
    model = OracleCredential
    template_name = "oracle_accounts/credential_list.html"
    context_object_name = "items"
    paginate_by = 25

    def get_queryset(self):
        qs = OracleCredential.objects.select_related("user").order_by("-updated_at", "-id")
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context["credential_stats"] = {
            "total": queryset.count(),
            "enabled": queryset.filter(enabled=True).count(),
            "current": queryset.filter(current=True).count(),
        }
        return context


class OracleCredentialDetailView(LoginRequiredMixin, OwnerOrStaffQuerysetMixin, DetailView):
    model = OracleCredential
    template_name = "oracle_accounts/credential_detail.html"
    context_object_name = "item"


class OracleCredentialCreateView(LoginRequiredMixin, CreateView):
    model = OracleCredential
    form_class = OracleCredentialForm
    template_name = "oracle_accounts/credential_form.html"
    success_url = reverse_lazy("oracle_accounts:list")

    def form_valid(self, form):
        obj = form.save(commit=False)
        if not self.request.user.is_staff or obj.user_id is None:
            obj.user = self.request.user
        obj.save()
        messages.success(self.request, "Identifiants Oracle créés.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("oracle_accounts:detail", kwargs={"pk": self.object.pk})


class OracleCredentialUpdateView(LoginRequiredMixin, OwnerOrStaffQuerysetMixin, UpdateView):
    model = OracleCredential
    form_class = OracleCredentialForm
    template_name = "oracle_accounts/credential_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Identifiants Oracle mis à jour.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("oracle_accounts:detail", kwargs={"pk": self.object.pk})


class OracleCredentialDeleteView(LoginRequiredMixin, OwnerOrStaffQuerysetMixin, DeleteView):
    model = OracleCredential
    template_name = "oracle_accounts/credential_confirm_delete.html"
    success_url = reverse_lazy("oracle_accounts:list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Identifiants Oracle supprimés.")
        return super().delete(request, *args, **kwargs)


def _can_access(request: HttpRequest, cred: OracleCredential) -> None:
    if request.user.is_staff:
        return
    if cred.user_id != request.user.id:
        raise PermissionDenied("Accès interdit.")


@login_required
def test_oracle_connection(request: HttpRequest, pk: int) -> HttpResponse:
    cred = get_object_or_404(OracleCredential, pk=pk)
    _can_access(request, cred)

    if not cred.enabled:
        return JsonResponse({"status": "error", "message": "Identifiant désactivé."}, status=400)

    try:
        increment_metric("oracle.credential_test.requests")
        logger.info("Testing Oracle connection for credential_id=%s user_id=%s", cred.pk, request.user.id)
        with connect_with_credential(cred) as con:
            with con.cursor() as cur:
                cur.execute("SELECT 1 FROM dual")
                cur.fetchone()
        return JsonResponse({"status": "success"})
    except Exception as exc:
        increment_metric("oracle.credential_test.failure")
        logger.exception("Oracle connection test failed for credential_id=%s", cred.pk)
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)


@login_required
@require_POST
def switch_oracle_credential(request: HttpRequest) -> HttpResponse:
    cred = get_object_or_404(OracleCredential, id=request.POST.get("cred_id"), user=request.user)
    if not cred.enabled:
        messages.error(request, "Cet identifiant est désactivé.")
        return redirect(request.META.get("HTTP_REFERER", "oracle_accounts:list"))

    set_current_oracle_credential(request, cred)
    messages.success(
        request,
        f"Identifiant Oracle actif : {cred.host}:{cred.port}/{cred.service_name} ({cred.username})",
    )
    return redirect(request.META.get("HTTP_REFERER", "oracle_accounts:list"))
