import geopandas
import pyproj
import shapely
from typing import cast, Final

MSK_48_CRS : Final[str] = '+proj=tmerc +lat_0=0 +lon_0=38.48333333333 +k=1 +x_0=1250000 +y_0=-5412900.566 +ellps=krass +towgs84=23.57,-140.95,-79.8,0,0.35,0.79,-0.22 +units=m +no_defs'

'''
    Загружает указанный путём geojson файл в GeoDataFrame
    Аргументы:
        path : str - строка, указывающая путь до загружаемого файла
        left_bottom : tuple[float, float] | None - левый нижний угол (в таком порядке компонентов) загружаемого региона.
                                                    Все фитчи полностью вне региона будут проигноированы при загрузке. 
                                                    Имеет эффект, только если right_top тоже не None.
        right_top : tuple[float, float] | None - правый верхний угол (в таком порядке компонентов) загружаемого региона.
                                                    Все фитчи полностью вне региона будут проигноированы при загрузке. 
                                                    Имеет эффект, только если left_bottom тоже не None.
    Возвращает:
        geopandas.GeoDataFrame - датафрейм содержащий фитчи, их геометрии и параметры.
'''
def load_geojson(path: str, left_bottom: tuple[float, float] | None = None, right_top: tuple[float, float] | None = None) -> geopandas.GeoDataFrame:
    if (left_bottom and right_top):
        return geopandas.read_file(path, bbox=(*left_bottom, *right_top))
    else:
        return geopandas.read_file(path)

'''
    Производит валидацию датафрейма на совместимость с модулем (для дальнейшей работы).
    Проверяет датафрейм на наличие столбцов geometry и elevation, на отсутствие nan-значений, на отсутствие некольцевых геометрий.
    Устаналивает активную геометрию на столбец geometry.
'''
def validate_data(df: geopandas.GeoDataFrame):
    expected_columns = ['elevation', 'geometry']
    for column in expected_columns:
        if not column in df.columns:
            raise KeyError(f'Missing column `{column}` the in dataframe.')

    if df.isnull().any().any():
        raise ValueError('Detected missing values (NaNs) in the dataframe.')
    
    if len(df[df['geometry'].is_ring == False]) > 0:
        raise ValueError('Detected non-ring geometries in the dataframe.')
    
    df.set_geometry('geometry', inplace=True)
    
'''
    Создаёт датафрем, в котором основная геометрия приведена к указанной CRS.
'''
def project_geometry(df: geopandas.GeoDataFrame, crs: str) -> geopandas.GeoDataFrame:
    return cast(geopandas.GeoDataFrame, df.to_crs(crs))

'''
    Проецирует точку из WGS84 в указанную CRS.
'''
def wgs84_point_to_crs(point: tuple[float, float], crs: str) -> tuple[float, float]:
    return cast(tuple[float, float], pyproj.Transformer.from_crs('EPSG:4326', crs, always_xy=True,).transform(*point, errcheck=True))

'''
    Создаёт сетку для сэмплирования высот с указанными параметрами в системе координат с осью x направленной вправо, осью y направленной вверх.
    Аргументы:
        leftTop : tuple[int, int] - левый верхний (в таком порядке компонентов) угол точки сэмплирования.
        stepSize : int - шаг сетки сэмплирования (расстояние между точками сэмплирования)
        columnCount: int - число столбцов в создаваемой сетке сэмплирования
        rowCount: int - число строк в создаваемой сетке сэмплирования
        crs: str - CRS, в которой координаты сгенерированной сетки будут представлены (вызывает set_crs(crs) на датафрейме сетки)
    Возвращает:
        GeoDataFrame - датафрейм с точками сетки сэмплирования, содержащий 2 столбца:
            'point' : shapely.Point - точка для сэмплирования высоты
            'leftDownIndex' : int - индекс точки сэмплирования в направлении слева-направо, сверху-вниз.
                                    Точка в левом верхнем углу имеет индекс 0, в конце первой строки columnCount - 1, в начале второй строки columnCount, в правом нижнем углу - rowCount*columnCount-1
'''
def generate_sampling_grid(leftTop: tuple[int, int], stepSize: int, columnCount: int, rowCount: int, crs: str) -> geopandas.GeoDataFrame:
    if columnCount < 1:
        raise ValueError('columnCount should be greater than 0')
    elif rowCount < 1:
        raise ValueError('rowCount should be greater than 0')
    elif stepSize < 1:
        raise ValueError('stepSize should be greater than 0')

    df = geopandas.GeoDataFrame({
        'leftDownIndex': [x for x in range(rowCount * columnCount)],
        'point': [shapely.Point(x, y) for y in range(leftTop[1] - stepSize//2, leftTop[1] - stepSize//2 - stepSize*rowCount, -stepSize) for x in range(leftTop[0] + stepSize//2, leftTop[0] + stepSize//2 + stepSize*columnCount, stepSize)]
    })
    df.set_geometry('point', inplace=True)
    df.set_crs(crs, inplace=True)
    return df

'''
    Задаёт каждой точке из sampling_grid значение высоты на основе геометрии фитч terrain.
    В случае конфликта (попадания на границу двух фитч) точке присваивается наибольшая высота.
'''
def generate_height_map(terrain: geopandas.GeoDataFrame, sampling_grid: geopandas.GeoDataFrame) -> geopandas.GeoDataFrame:
    terrain_internal = terrain.copy()
    #Необходимо немного расширить геометрии, чтобы границы геометрий лежали друг в друге, т.к. предикат within объединяет геометрии, только если одна полностью лежит в другой, не касаясь границ
    terrain_internal['geometry'] = cast(geopandas.GeoSeries, terrain['geometry']).buffer(1)
    #Пересечь точку с геометрией, использя предикат within.
    df_joined : geopandas.GeoDataFrame = sampling_grid.sjoin(terrain_internal, how='left', predicate = 'within')
    #Отсортировать по убыванию elevation, чтобы точки с большим elevation были раньше в датафрейме
    df_joined.sort_values('elevation', ascending=False, inplace=True)
    #Сгруппировать строки по точке, а затем выбрать первую строку (с наибольшей высотой), чтобы разрешить конфликты, когда точка попала в несколько фитч
    df_joined = cast(geopandas.GeoDataFrame, df_joined.groupby('point').head(1))
    #Отсортировать датафрейм обратно по индексу сэмплируемой точки, чтобы он был упорядоченным
    df_joined.sort_values('leftDownIndex', ascending=True, inplace=True)
    #Удалить индекс фрейма terrain, который прикрепляется как index_right после sjoin
    df_joined.drop(['index_right'], axis=1, inplace=True)
    return df_joined

'''
    Преобразовывает карту высот из GeoDataFrame в список списков, где индекс внешнего списка определяет строку, а внутреннего - столбец.
'''
def height_map_to_lists(heightMap: geopandas.GeoDataFrame) -> list[list[float]]:
    out = []
    curY = heightMap.iloc[0]['point'].y
    curList : list[float] = []
    for i, row in heightMap.iterrows():
        if row['point'].y != curY:
            out.append(curList)
            curList = []
            curY = row['point'].y
        curList.append(row['elevation'])
    out.append(curList)
    return out