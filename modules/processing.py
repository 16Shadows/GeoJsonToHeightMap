import geopandas as gpd
import pyproj
from typing import Tuple, cast, Final

MSK_48_CRS : Final[str] = '+proj=tmerc +lat_0=0 +lon_0=38.48333333333 +k=1 +x_0=1250000 +y_0=-5412900.566 +ellps=krass +towgs84=23.57,-140.95,-79.8,0,0.35,0.79,-0.22 +units=m +no_defs'

def load_geojson(path: str, left_bottom: Tuple[float, float] | None = None, right_top: Tuple[float, float] | None = None) -> gpd.GeoDataFrame:
    if (left_bottom and right_top):
        return gpd.read_file(path, bbox=(*left_bottom, *right_top))
    else:
        return gpd.read_file(path)
    
def validate_data(df: gpd.GeoDataFrame):
    expected_columns = ['elevation', 'geometry']
    for column in expected_columns:
        if not column in df.columns:
            raise KeyError(f'Missing column `{column}` the in dataframe.')

    if df.isnull().any().any():
        raise ValueError('Detected missing values (NaNs) in the dataframe.')
    
    # Удаляем строки с незамкнутыми геометриями
    df = df[df['geometry'].is_ring]
    
    df.set_geometry('geometry', inplace=True)

def project_geometry(df: gpd.GeoDataFrame, crs: str) -> gpd.GeoDataFrame:
    return cast(gpd.GeoDataFrame, df.to_crs(crs))

def wgs84_point_to_crs(point: Tuple[float, float], crs: str) -> Tuple[float, float]:
    return cast(Tuple[float, float], pyproj.Transformer.from_crs('EPSG:4326', crs, always_xy=True,).transform(*point, errcheck=True))