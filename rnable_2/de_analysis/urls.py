from django.urls import path
from . import views

app_name = "de_analysis"

urlpatterns = [
    path("", views.index, name="de-analysis"),
]
