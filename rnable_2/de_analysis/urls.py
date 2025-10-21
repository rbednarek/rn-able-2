from django.urls import path
from . import views

app_name = "de_analysis"

urlpatterns = [
    path("", views.analysis_page, name="de-analysis"),
    # API endpoints
    path("api/upload/", views.upload_data, name="upload_data"),
    path("api/run-pca/", views.run_pca_analysis, name="run_pca"),
    path("api/save-groups/", views.save_groups, name="save_groups"),
    path("api/run-de/", views.run_de_analysis_api, name="run_de"),
    path(
        "api/download/<int:result_id>/", views.download_results, name="download_results"
    ),
]
