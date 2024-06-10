# Использование:
# 1. Задайте нужную область, изменив координаты `left_bottom` и `right_top`.
# 2. При необходимости, отрегулируйте шаг сэмплирования (`step_size`).
# 3. Запустите скрипт.
# 4. Результирующая карта высот будет сохранена в файл `heightmap.geojson` в том же каталоге.

import geopandas as gpd
import matplotlib.pyplot as plt
from contours import contours_to_polygons
from processing import (
    load_geojson,
    validate_data,
    project_geometry,
    generate_sampling_grid,
    generate_height_map,
    MSK_48_CRS,
    wgs84_point_to_crs,
)

def save_heightmap(heightmap, filename):
    heightmap.to_file(filename, driver='GeoJSON')

if __name__ == "__main__":
    # Задаем координаты левого нижнего и правого верхнего углов области интереса
    left_bottom = (39.395158, 52.491465)
    left_bottom_projected = wgs84_point_to_crs(left_bottom, MSK_48_CRS)
    right_top = (39.829939, 52.683001)
    right_top_projected = wgs84_point_to_crs(right_top, MSK_48_CRS)

    # Загружаем и валидируем данные в заданной области
    df_culled = load_geojson("lipetsk_high.geojson", left_bottom, right_top)
    validate_data(df_culled)

    # Преобразуем контуры в полигоны и проецируем в систему координат MSK-48
    df_projected = project_geometry(df_culled, MSK_48_CRS)
    df_polygons = contours_to_polygons(df_projected)

    # Вычисляем размер сетки сэмплирования
    step_size = 50  # Шаг сэмплирования (в метрах) - расстояние между точками сетки
    column_count = int((right_top_projected[0] - left_bottom_projected[0]) // step_size) + 1 # Количество столбцов в сетке
    row_count = int((right_top_projected[1] - left_bottom_projected[1]) // step_size) + 1 # Количество строк в сетке

    # Генерируем сетку сэмплирования
    sampling_grid = generate_sampling_grid(
        leftTop=(int(left_bottom_projected[0]), int(right_top_projected[1])),  # Координаты левого верхнего угла сетки
        stepSize=step_size, # Шаг сэмплирования (расстояние между точками)
        columnCount=column_count, #583 Количество столбцов в сетке
        rowCount=row_count, #436 Количество строк в сетке
        crs=MSK_48_CRS, # Система координат сетки
    )

    # Присваиваем высоты точкам сетки
    heightmap = generate_height_map(df_polygons, sampling_grid)
    heightmapCrs = heightmap.to_crs(epsg=4326)

    # Сохраняем карту высот в файл
    save_heightmap(heightmapCrs, 'heightmap.geojson')

    # Визуализируем данные
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    df_culled.plot(column="elevation", ax=axes[0], legend=True)
    axes[0].set_title("Исходные данные")

    df_polygons.plot(column="elevation", ax=axes[1], legend=True)
    axes[1].set_title("Полигоны из контуров")

    heightmap.plot(column="elevation", ax=axes[2], legend=True)
    sampling_grid.boundary.plot(ax=axes[2], color='red', linewidth=0.5)  # Визуализация границ сетки сэмплирования
    axes[2].set_title("Карта высот")

    plt.tight_layout()
    plt.show()
