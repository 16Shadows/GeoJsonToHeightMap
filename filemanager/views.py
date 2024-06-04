from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import FileUploadForm, UserProfileForm
from .models import UploadedFile
import geopandas as gpd
from .utils import load_geojson, validate_data, project_geometry

@login_required
def upload_file(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.user = request.user
            uploaded_file.save()
            return redirect('filemanager:file_list')
    else:
        form = FileUploadForm()
    return render(request, 'filemanager/upload_file.html', {'form': form})

@login_required
def file_list(request):
    files = UploadedFile.objects.filter(user=request.user)
    return render(request, 'filemanager/file_list.html', {'files': files})

@login_required
def map_view(request, file_id):
    uploaded_file = UploadedFile.objects.get(id=file_id, user=request.user)
    path = uploaded_file.file.path
    try:
        gdf = gpd.read_file(path)
        geojson_data = gdf.to_json()
        return render(request, 'filemanager/map.html', {'geojson_data': geojson_data})
    except Exception as e:
        return render(request, 'filemanager/map.html', {'error': str(e)})

@login_required
def dashboard(request):
    context = {}
    return render(request, 'filemanager/dashboard.html', context)

@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('filemanager:profile')
    else:
        form = UserProfileForm(instance=user)
    return render(request, 'filemanager/profile.html', {'form': form})
