import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union
import matplotlib.pyplot as plt
from modules import processing as prc

# Функция для преобразования контуров в полигоны
def contours_to_polygons(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Сортировка высот по убыванию
    elevations = sorted(df['elevation'].unique(), reverse=True)

    polygons = []
    # Итерация по каждой высоте
    for elevation in elevations:
        # Фильтрация данных по текущей высоте
        group = df[df['elevation'] == elevation]

        # Извлечение координат внешних и внутренних контуров
        exterior_coords = group.geometry[group.geometry.apply(lambda geom: isinstance(geom, LineString) and geom.is_ring)].apply(lambda line: line.coords)
        interior_coords = group.geometry[group.geometry.apply(lambda geom: isinstance(geom, Polygon))].apply(lambda poly: [interior.coords for interior in poly.interiors]).explode(index_parts=False)

        # Создание внешних полигонов
        exterior_polygons = list(map(Polygon, exterior_coords))
        unioned_polygon = unary_union(exterior_polygons)

        # Добавление объединенного полигона в список
        if isinstance(unioned_polygon, Polygon):
            polygons.append({'elevation': elevation, 'geometry': unioned_polygon})
        elif isinstance(unioned_polygon, MultiPolygon):
            polygons.extend([{'elevation': elevation, 'geometry': poly} for poly in unioned_polygon.geoms])

    # Создание GeoDataFrame из полигонов
    polygons_df = gpd.GeoDataFrame(polygons, crs=df.crs)

    # Обработка внутренних полигонов
    final_polygons = []
    for i, poly in polygons_df.iterrows():
        current_polygon = poly['geometry']

        # Поиск и вычитание внутренних полигонов
        for j, inner_poly in polygons_df[polygons_df['elevation'] < poly['elevation']].iterrows():
            inner_geom = inner_poly['geometry']
            
            # Проверка типов текущего и внутреннего полигонов
            if isinstance(inner_geom, Polygon) and isinstance(current_polygon, Polygon) and current_polygon.contains(inner_geom):
                current_polygon = current_polygon.difference(inner_geom)
            elif isinstance(inner_geom, MultiPolygon):
                # Проверка типов текущего полигона и вычитаемого полигона
                if isinstance(current_polygon, Polygon):
                    # Если текущий полигон - Polygon, итерация по всем внутренним полигонам в MultiPolygon
                    for sub_poly in inner_geom.geoms:
                        # Проверка содержания внутреннего полигона в текущем полигоне
                        if current_polygon.contains(sub_poly):
                            current_polygon = current_polygon.difference(sub_poly)
                elif isinstance(current_polygon, MultiPolygon):
                    # Если текущий полигон - MultiPolygon, итерация по всем его составляющим
                    new_geoms = [geom.difference(inner_geom) if geom.intersects(inner_geom) else geom for geom in current_polygon.geoms]
                    current_polygon = MultiPolygon(new_geoms)

        final_polygons.append({'elevation': poly['elevation'], 'geometry': current_polygon})

    # Объединение полигонов на одной высоте
    final_df = gpd.GeoDataFrame(final_polygons, crs=df.crs)
    grouped_polygons = [{'elevation': elevation, 'geometry': unary_union(group.geometry)} for elevation, group in final_df.groupby('elevation')]

    return gpd.GeoDataFrame(grouped_polygons, crs=df.crs)

if __name__ == '__main__':
    # Загрузка и валидация данных
    left_bottom = (39.395158, 52.491465)
    left_bottom_projected = prc.wgs84_point_to_crs(left_bottom, prc.MSK_48_CRS)
    right_top = (39.829939, 52.683001)
    right_top_projected = prc.wgs84_point_to_crs(right_top, prc.MSK_48_CRS)
    
    # Загрузка и фильтрация GeoJSON данных
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

    # Сохранение результата в файл GeoJSON
    df_polygons_wgs84.to_file('result.geojson', driver='GeoJSON')

    # Визуализация данных
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Исходные данные
    df_culled.plot(column='elevation', ax=axes[0], legend=True)
    axes[0].set_title('Исходные данные')

    # Данные в проекции МСК-48
    df_projected.plot(column='elevation', ax=axes[1], legend=True)
    axes[1].set_title('Проекция данных в МСК-48')

    # Полигоны из контуров
    df_polygons.plot(column='elevation', ax=axes[2], legend=True)
    axes[2].set_title('Полигоны из контуров')

    plt.tight_layout()
    plt.show()

# Функция тестирования на карте
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

    # Сохранение карты в HTML файл
    m.save('map.html')
