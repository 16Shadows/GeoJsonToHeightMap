import numpy as np
import plotly
from django.http import HttpResponse
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

#moduls/geojson_to_heightmap.py (author: https://github.com/16Shadows/GeoJsonToHeightMap/commits?author=KosmixGT)
@login_required
def download_heightmap_file(request, file_id):
    uploaded_file = UploadedFile.objects.get(id=file_id, user=request.user)
    uploaded_file_path = uploaded_file.file.path
    heightmap_file_name = uploaded_file.file.name + "heightmap.txt"

    left_bottom = (39.395158, 52.491465)
    left_bottom_projected = prc.wgs84_point_to_crs(left_bottom, prc.MSK_48_CRS)
    right_top = (39.829939, 52.683001)
    right_top_projected = prc.wgs84_point_to_crs(right_top, prc.MSK_48_CRS)

    # Загружаем и валидируем данные в заданной области
    df_culled = load_geojson(uploaded_file_path, left_bottom, right_top)
    validate_data(df_culled)

    # Преобразуем контуры в полигоны и проецируем в систему координат MSK-48
    df_projected = project_geometry(df_culled, prc.MSK_48_CRS)
    df_polygons = cnt.contours_to_polygons(df_projected)

    # Вычисляем размер сетки сэмплирования
    step_size = 10  # Шаг сэмплирования (в метрах) - расстояние между точками сетки
    column_count = 2000  # Количество столбцов в сетке
    row_count = 2000  # Количество строк в сетке

    # Генерируем сетку сэмплирования
    sampling_grid = prc.generate_sampling_grid(
        leftTop=(int(left_bottom_projected[0]), int(right_top_projected[1])),  # Координаты левого верхнего угла сетки
        stepSize=step_size,  # Шаг сэмплирования (расстояние между точками)
        columnCount=column_count,  # Количество столбцов в сетке
        rowCount=row_count,  # Количество строк в сетке
        crs=prc.MSK_48_CRS,  # Система координат сетки
    )

    # Присваиваем высоты точкам сетки
    heightmap = prc.generate_height_map(df_polygons, sampling_grid)

    # Получаем карту высот в виде списка списков
    height_lists = prc.height_map_to_lists(heightmap)

    # Запись полученных данных
    heightmap_file = ""
    heightmap_file += f"ncols {column_count}\n"
    heightmap_file += f"nrows {row_count}\n"
    heightmap_file += f"xllcorner {int(left_bottom_projected[0])}\n"
    heightmap_file += f"yllcorner {int(left_bottom_projected[1])}\n"
    heightmap_file += f"cellsize {step_size}\n"
    heightmap_file += "NODATA_value -99999     Unit μg/m3\n"

    for row in height_lists:
        heightmap_file += ' '.join(map(str, row)) + '\n'

    # Возвращаем файл в виде HttpResponse
    response = HttpResponse(heightmap_file, content_type="text/plain")
    response['Content-Disposition'] = f'attachment; filename="{heightmap_file_name}"'
    return response


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
        return render(request, 'filemanager/map_polygon.html', 
                      {'plotly_data': fig.to_html(full_html=False), 'file_id': file_id})
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
