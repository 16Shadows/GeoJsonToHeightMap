import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union

# Функция для преобразования контуров в полигоны
def contours_to_polygons(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    polygons = []  # Список для хранения полигонов
    
    # Группировка по высоте и итерация по группам
    for elevation, group in df.groupby('elevation'):
        exterior_coords = []  # Координаты внешних контуров
        interior_coords = []  # Координаты внутренних контуров
        
        # Итерация по геометрии в каждой группе
        for geom in group.geometry:
            # Если геометрия является замкнутой линией (контуром)
            if isinstance(geom, LineString) and geom.is_ring:
                exterior_coords.append(geom.coords)
            # Если геометрия является полигоном
            elif isinstance(geom, Polygon):
                exterior_coords.append(geom.exterior.coords)
                # Добавление внутренних контуров, если они есть
                for interior in geom.interiors:
                    interior_coords.append(interior.coords)
        
        # Если есть внешние контуры
        if exterior_coords:
            # Создание полигонов из внешних контуров
            exterior_polygons = [Polygon(coords) for coords in exterior_coords]
            # Объединение полигонов в один
            unioned_polygon = unary_union(exterior_polygons)
            
            # Если объединенный полигон является одиночным полигоном
            if isinstance(unioned_polygon, Polygon):
                polygons.append({'elevation': elevation, 'geometry': unioned_polygon})
            # Если объединенный полигон является множеством полигонов
            elif isinstance(unioned_polygon, MultiPolygon):
                # Итерация по полигонам в множестве
                for polygon in unioned_polygon.geoms:                     
                    polygons.append({'elevation': elevation, 'geometry': polygon})
        
    # Создание GeoDataFrame из списка полигонов
    polygons_df = gpd.GeoDataFrame(polygons)
    return polygons_df

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import processing as prc
    
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

    # Сохранение результата

    # Преобразование данных обратно в WGS 84
    df_polygons_wgs84 = df_polygons.to_crs(epsg=4326)

    # Сохранение результата
    df_polygons_wgs84.to_file('result_polygons.geojson', driver='GeoJSON')

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

