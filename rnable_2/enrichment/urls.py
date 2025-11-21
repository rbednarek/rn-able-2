from django.urls import path
from . import views

app_name = "enrichment"

urlpatterns = [
    path("", views.index, name="enrich"),
    path(
        "api/session-de/<str:session_id>/",
        views.session_de_data,
        name="session_de_data",
    ),
]
