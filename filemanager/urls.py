from django.urls import path
from .views import upload_file, file_list, map_view, dashboard, edit_profile

app_name = 'filemanager'

urlpatterns = [
    path('upload/', upload_file, name='file_upload'),
    path('files/', file_list, name='file_list'),
    path('map/<int:file_id>/', map_view, name='map_view'),
    path('dashboard/', dashboard, name='dashboard'),
    path('profile/', edit_profile, name='profile'),
]
