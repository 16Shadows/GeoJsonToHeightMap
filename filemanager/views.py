import numpy as np
import plotly
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from matplotlib import pyplot as plt
import contextily as ctx
from .forms import FileUploadForm, UserProfileForm
from .models import UploadedFile
import geopandas as gpd
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import plotly.express as px
import plotly.graph_objects as go
from modules import processing as prc, contours as cnt
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
def map_line_view(request, file_id):
    uploaded_file = UploadedFile.objects.get(id=file_id, user=request.user)
    print(uploaded_file)
    path = uploaded_file.file.path
    try:
        gdf = gpd.read_file(path)

        prc.validate_data(gdf)

        df_projected = prc.project_geometry(gdf, prc.MSK_48_CRS)

        fig_m, ax_m = plt.subplots(figsize=(6.5, 6.5))

        ax_m.set_xlim(4390000, 4420000)

        ax_m.set_ylim(6890000, 6920000)

        df_projected.to_crs(epsg=3857).plot(ax=ax_m, color='blue')

        ctx.add_basemap(ax_m, source=ctx.providers.CartoDB.Voyager)

        plt.title('EPSG:3857 из МСК-48')

        plt.savefig('static/images/map_m.png')

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
            height=650,
            coloraxis_colorbar=dict(title="Высота (м)"),
            margin={"t": 20, "l": 20, "b": 0},
            mapbox_bounds={"west": center[0] - 2.5,
                           "east": center[0] + 2,
                           "south": center[1] - 1,
                           "north": center[1] + 1}
        )

        return render(request, 'filemanager/map_line.html',
                      {'plotly_data': fig.to_html(full_html=False), 'file_id': file_id})
    except Exception as e:
        return render(request, 'filemanager/map_line.html', {'error': str(e)})


@login_required
def map_polygon_view(request, file_id):
    uploaded_file = UploadedFile.objects.get(id=file_id, user=request.user)
    path = uploaded_file.file.path
    try:
        gdf = gpd.read_file(path)
        prc.validate_data(gdf)
        df_projected = prc.project_geometry(gdf, prc.MSK_48_CRS)
        df_polygons = cnt.contours_to_polygons(df_projected)
        df_polygons.set_crs(prc.MSK_48_CRS, inplace=True)
        df_polygons_wgs84 = df_polygons.to_crs(epsg=4326)
        opacity = 0.5
        cmap = cm.viridis  # выбираем цветовую карту
        norm = plt.Normalize(vmin=df_polygons_wgs84['elevation'].min(),
                             vmax=df_polygons_wgs84['elevation'].max())  # нормализуем данные
        colors = [mcolors.rgb2hex(cmap(norm(x))[:-1]) for x in
                  np.linspace(df_polygons_wgs84['elevation'].min(), df_polygons_wgs84['elevation'].max(), 10)]
        # Преобразуем каждый цвет в строку с прозрачностью
        colors_with_opacity = [f'rgba{mcolors.to_rgba(color, alpha=opacity)}' for color in colors]
        fig = px.choropleth_mapbox(df_polygons_wgs84,
                                   geojson=df_polygons_wgs84['geometry'],
                                   color_continuous_scale=colors_with_opacity,
                                   locations=df_polygons_wgs84.index,
                                   opacity=0.5,
                                   color="elevation",
                                   center={"lat": df_polygons_wgs84.geometry.iloc[0].centroid.y,
                                           "lon": df_polygons_wgs84.geometry.iloc[0].centroid.x},
                                   mapbox_style="carto-positron",
                                   zoom=10,
                                   hover_name=df_polygons_wgs84['elevation'],
                                   # hover_data={}
                                   )
        fig.update_traces(hovertemplate='Высота: %{z} м')
        fig.update_layout(height=650,  # Устанавливаем высоту графика
                          margin={"t": 0, "l": 0, "b": 0})
        return render(request, 'filemanager/map_polygon.html', {'plotly_data': fig.to_html(full_html=False)})
    except Exception as e:
        return render(request, 'filemanager/map_polygon.html', {'error': str(e)})


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
