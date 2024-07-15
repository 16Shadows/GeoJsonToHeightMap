# Использование:
# 1. Задайте нужную область, изменив координаты `left_bottom` и `right_top`.
# 2. При необходимости, отрегулируйте шаг сэмплирования (`step_size`).
# 3. Запустите скрипт.
# 4. Результирующая карта высот будет сохранена в файл `heightmap_**.txt` в том же каталоге.

import geopandas as gpd
import matplotlib.pyplot as plt
from modules.contours import contours_to_polygons
from modules.processing import (
    load_geojson,
    validate_data,
    project_geometry,
    generate_sampling_grid,
    generate_height_map,
    MSK_48_CRS,
    wgs84_point_to_crs,
    height_map_to_lists,
)

if __name__ == "__main__":
    # Параметры
    right_top = (39.829939, 52.683001) #Координаты правого-верхнего угла
    left_bottom = (39.444032, 52.466341) #Координаты левого-нижнего угла
    geojson_file = "lipetsk_high.geojson"; #Путь до конвертируемого файла
    step_size = 200  # Шаг сэмплирования (в метрах) - расстояние между точками сетки
    column_count = 130  # Количество столбцов в сетке
    row_count = 101  # Количество строк в сетке
    target_crs = MSK_48_CRS # Координатная системая для семплирования
    visualize = True
    
    # Задаем координаты левого нижнего и правого верхнего углов области интереса
    left_bottom_projected = wgs84_point_to_crs(left_bottom, target_crs)
    right_top_projected = wgs84_point_to_crs(right_top, target_crs)

    # Загружаем и валидируем данные в заданной области
    df_culled = load_geojson(geojson_file, left_bottom, right_top)
    validate_data(df_culled)

    # Преобразуем контуры в полигоны и проецируем в целевую систему координат
    df_projected = project_geometry(df_culled, target_crs)
    df_polygons = contours_to_polygons(df_projected)

    # Генерируем сетку сэмплирования
    sampling_grid = generate_sampling_grid(
        leftBottom=(int(left_bottom_projected[0]), int(left_bottom_projected[1])),  # Координаты левого верхнего угла сетки
        stepSize=step_size,  # Шаг сэмплирования (расстояние между точками)
        columnCount=column_count,  # Количество столбцов в сетке
        rowCount=row_count,  # Количество строк в сетке
        crs=target_crs,  # Система координат сетки
    )

    # Присваиваем высоты точкам сетки
    heightmap = generate_height_map(df_polygons, sampling_grid)

    # Получаем карту высот в виде списка списков
    height_lists = height_map_to_lists(heightmap)

    # Открываем файл для записи
    with open(f'heightmap_{step_size}m_{column_count}c_{row_count}r.txt', 'w', encoding='utf-8') as file:
        # Записываем метаданные
        file.write(f"ncols {column_count}\n")
        file.write(f"nrows {row_count}\n")
        file.write(f"xllcorner {int(left_bottom_projected[0])}\n")
        file.write(f"yllcorner {int(left_bottom_projected[1])}\n")
        file.write(f"cellsize {step_size}\n")
        file.write("NODATA_value -99999     Unit μg/m3\n")

        # Записываем данные карты высот
        for row in height_lists:
            file.write(' '.join(map(str, row)) + '\n')

    # Визуализируем данные
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    if visualize:
        df_culled.plot(column="elevation", ax=axes[0], legend=True)
        axes[0].set_title("Исходные данные")

        df_polygons.plot(column="elevation", ax=axes[1], legend=True)
        axes[1].set_title("Полигоны из контуров")

        heightmap.plot(column="elevation", ax=axes[2], legend=True)
        sampling_grid.boundary.plot(ax=axes[2], color='red', linewidth=0.5)  # Визуализация границ сетки сэмплирования
        axes[2].set_title("Карта высот")

    plt.tight_layout()
    plt.show()
