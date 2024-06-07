import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import processing as prc

# Функция для преобразования контуров в полигоны

def contours_to_polygons(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    polygons = []  # Список для хранения полигонов
    
    # Сортировка уровней высоты по возрастанию
    elevations = sorted(df['elevation'].unique())
    
    for elevation in elevations:
        group = df[df['elevation'] == elevation]
        exterior_coords = []  # Координаты внешних контуров
        interior_coords = []  # Координаты внутренних контуров
        
        # Итерация по геометрии в каждой группе
        for geom in group.geometry:
            if isinstance(geom, LineString) and geom.is_ring:
                exterior_coords.append(geom.coords)
            elif isinstance(geom, Polygon):
                exterior_coords.append(geom.exterior.coords)
                for interior in geom.interiors:
                    interior_coords.append(interior.coords)
        
        if exterior_coords:
            exterior_polygons = [Polygon(coords) for coords in exterior_coords]
            unioned_polygon = unary_union(exterior_polygons)
            
            if isinstance(unioned_polygon, Polygon):
                polygons.append({'elevation': elevation, 'geometry': unioned_polygon})
            elif isinstance(unioned_polygon, MultiPolygon):
                polygons.append({'elevation': elevation, 'geometry': unioned_polygon})

    # Создание GeoDataFrame из списка полигонов
    polygons_df = gpd.GeoDataFrame(polygons)
    
    # Обработка вырезания внутренних контуров
    final_polygons = []
    for i, poly in polygons_df.iterrows():
        current_polygon = poly['geometry']
        for j, inner_poly in polygons_df.iterrows():
            if inner_poly['elevation'] > poly['elevation']:
                if isinstance(inner_poly['geometry'], Polygon):
                    if isinstance(current_polygon, Polygon) and current_polygon.contains(inner_poly['geometry']):
                        current_polygon = current_polygon.difference(inner_poly['geometry'])
                    elif isinstance(current_polygon, MultiPolygon):
                        new_geoms = []
                        for geom in current_polygon.geoms:
                            if geom.contains(inner_poly['geometry']):
                                geom = geom.difference(inner_poly['geometry'])
                            new_geoms.append(geom)
                        current_polygon = MultiPolygon(new_geoms)
                elif isinstance(inner_poly['geometry'], MultiPolygon):
                    for sub_poly in inner_poly['geometry'].geoms:
                        if isinstance(current_polygon, Polygon) and current_polygon.contains(sub_poly):
                            current_polygon = current_polygon.difference(sub_poly)
                        elif isinstance(current_polygon, MultiPolygon):
                            new_geoms = []
                            for geom in current_polygon.geoms:
                                if geom.contains(sub_poly):
                                    geom = geom.difference(sub_poly)
                                new_geoms.append(geom)
                            current_polygon = MultiPolygon(new_geoms)
        final_polygons.append({'elevation': poly['elevation'], 'geometry': current_polygon})

    
    # Объединение полигонов на одной высоте в MultiPolygon
    final_df = gpd.GeoDataFrame(final_polygons)
    grouped_polygons = []
    for elevation, group in final_df.groupby('elevation'):
        multi_poly = unary_union(group.geometry)
        grouped_polygons.append({'elevation': elevation, 'geometry': multi_poly})
    
    return gpd.GeoDataFrame(grouped_polygons)

if __name__ == '__main__':
    # Загрузка и валидация данных
    left_bottom = (39.395158, 52.491465)
    left_bottom_projected = prc.wgs84_point_to_crs(left_bottom, prc.MSK_48_CRS)
    right_top = (39.829939, 52.683001)
    right_top_projected = prc.wgs84_point_to_crs(right_top, prc.MSK_48_CRS)
    df_culled = prc.load_geojson('lipetsk_high.geojson', left_bottom, right_top)
    prc.validate_data(df_culled)
    
    # Проекция данных в МСК-48
    df_projected = prc.project_geometry(df_culled, prc.MSK_48_CRS)

    # Преобразование контуров в полигоны
    df_polygons = contours_to_polygons(df_projected)

    # Установка CRS для df_polygons
    df_polygons.set_crs(prc.MSK_48_CRS, inplace=True)

    # Преобразование данных обратно в WGS 84
    df_polygons_wgs84 = df_polygons.to_crs(epsg=4326)

    # Сохранение результата
    df_polygons_wgs84.to_file('result.geojson', driver='GeoJSON')

    # Визуализация
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    df_culled.plot(column='elevation', ax=axes[0], legend=True)
    axes[0].set_title('Исходные данные')

    df_projected.plot(column='elevation', ax=axes[1], legend=True)
    axes[1].set_title('Проекция данных в МСК-48')

    df_polygons.plot(column='elevation', ax=axes[2], legend=True)
    axes[2].set_title('Полигоны из контуров')

    plt.tight_layout()
    plt.show()   

#тест: проверка result_polygons.geojson на карте, после прогона метода появится map.html, можно открыть его в браузере
def test_map():
    import folium
    import geopandas as gpd

    # Загрузка GeoDataFrame из файла GeoJSON
    gdf = gpd.read_file('result.geojson')

    # Создание карты folium
    m = folium.Map(location=[52.491465, 39.395158], zoom_start=12)

    # Добавление геометрии из GeoDataFrame на карту
    for _, row in gdf.iterrows():
        # Преобразование геометрии в GeoJSON
        geojson = folium.GeoJson(data=row['geometry'].__geo_interface__)
        # Добавление GeoJSON на карту
        geojson.add_to(m)

    # Отображение карты
    m.save('map.html')

