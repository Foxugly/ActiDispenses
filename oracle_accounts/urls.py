from django.urls import path

from . import views
from .views import switch_oracle_credential

app_name = "oracle_accounts"

urlpatterns = [
    path("", views.OracleCredentialListView.as_view(), name="list"),
    path("new/", views.OracleCredentialCreateView.as_view(), name="create"),
    path("<int:pk>/", views.OracleCredentialDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.OracleCredentialUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.OracleCredentialDeleteView.as_view(), name="delete"),
    path("<int:pk>/test/", views.test_oracle_connection, name="test"),
    path("switch/", switch_oracle_credential, name="switch"),
]
