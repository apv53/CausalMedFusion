from django.urls import path
from .views import download_file

urlpatterns = [
    path("download/<int:file_id>/", download_file),
]
