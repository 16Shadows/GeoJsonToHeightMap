from django.urls import path
from .views import upload_file, file_list, map_line_view, dashboard, edit_profile, map_polygon_view

app_name = 'filemanager'

urlpatterns = [
    path('upload/', upload_file, name='file_upload'),
    path('files/', file_list, name='file_list'),
    path('map_line/<int:file_id>/', map_line_view, name='map_line_view'),
    path('map_polygon/<int:file_id>/', map_polygon_view, name='map_polygon_view'),
    path('dashboard/', dashboard, name='dashboard'),
    path('profile/', edit_profile, name='profile'),
]
