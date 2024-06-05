import plotly
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import FileUploadForm, UserProfileForm
from .models import UploadedFile
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
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
        fig = px.scatter_mapbox(lat=[],
                                lon=[],
                                color=[color for color in gdf['elevation']],
                                color_continuous_scale='Viridis')
        color_scale = px.colors.sequential.Viridis
        min_elevation = gdf['elevation'].min()
        max_elevation = gdf['elevation'].max()
        for line, elevation in zip(gdf.geometry, gdf['elevation']):
            normalized_value = (elevation - min_elevation) / (max_elevation - min_elevation)
            color = plotly.colors.sample_colorscale(color_scale, normalized_value)
            fig.add_trace(go.Scattermapbox(
                mode="lines",
                lon=[coord[0] for coord in line.coords],
                lat=[coord[1] for coord in line.coords],
                line=dict(color=color[0], width=2),
                customdata=[elevation] * len(line.coords),
                name="",
                hovertemplate=
                'Высота: %{customdata} м<br>' +
                'Шир: %{lat:.3f}°<br>' +
                'Долг: %{lon:.3f}°',
                showlegend=False
            ))
        center = gdf.geometry.iloc[0].coords[0]
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=10.5,
            mapbox_center={"lat": center[1], "lon": center[0]},
            height=700,
            coloraxis_colorbar=dict(title="Высота (м)"),
            margin={"t": 20, "l": 20, "b": 0},
            mapbox_bounds={"west": center[0] - 2.5,
                           "east": center[0] + 2,
                           "south": center[1] - 1,
                           "north": center[1] + 1}
        )
        return render(request, 'filemanager/map.html', {'plotly_data': fig.to_html(full_html=False)})
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
