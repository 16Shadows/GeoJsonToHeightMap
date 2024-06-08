import geopandas
import pyproj
import shapely
from typing import cast, Final

MSK_48_CRS : Final[str] = '+proj=tmerc +lat_0=0 +lon_0=38.48333333333 +k=1 +x_0=1250000 +y_0=-5412900.566 +ellps=krass +towgs84=23.57,-140.95,-79.8,0,0.35,0.79,-0.22 +units=m +no_defs'

def load_geojson(path: str, left_bottom: tuple[float, float] | None = None, right_top: tuple[float, float] | None = None) -> geopandas.GeoDataFrame:
    if (left_bottom and right_top):
        return geopandas.read_file(path, bbox=(*left_bottom, *right_top))
    else:
        return geopandas.read_file(path)
    
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
    
def project_geometry(df: geopandas.GeoDataFrame, crs: str) -> geopandas.GeoDataFrame:
    return cast(geopandas.GeoDataFrame, df.to_crs(crs))

def wgs84_point_to_crs(point: tuple[float, float], crs: str) -> tuple[float, float]:
    return cast(tuple[float, float], pyproj.Transformer.from_crs('EPSG:4326', crs, always_xy=True,).transform(*point, errcheck=True))

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

def generate_height_map(terrain: geopandas.GeoDataFrame, sampling_grid: geopandas.GeoDataFrame) -> geopandas.GeoDataFrame:
    terrain_internal = terrain.copy()
    terrain_internal['geometry'] = cast(geopandas.GeoSeries, terrain['geometry']).buffer(1)
    df_joined : geopandas.GeoDataFrame = sampling_grid.sjoin(terrain_internal, how='left', predicate = 'within')
    df_joined.sort_values('elevation', ascending=False, inplace=True)
    df_joined = cast(geopandas.GeoDataFrame, df_joined.groupby('point').head(1))
    df_joined.sort_values('leftDownIndex', ascending=True, inplace=True)
    return df_joined

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