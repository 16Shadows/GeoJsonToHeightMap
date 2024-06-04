import geopandas
import pyproj
from typing import Tuple, cast, Final

MSK_48_CRS: Final[str] = '+proj=tmerc +lat_0=0 +lon_0=38.48333333333 +k=1 +x_0=1250000 +y_0=-5412900.566 +ellps=krass +towgs84=23.57,-140.95,-79.8,0,0.35,0.79,-0.22 +units=m +no_defs'

def load_geojson(path: str, left_bottom: Tuple[float, float] | None = None, right_top: Tuple[float, float] | None = None) -> geopandas.GeoDataFrame:
    if left_bottom and right_top:
        return geopandas.read_file(path, bbox=(*left_bottom, *right_top))
    else:
        return geopandas.read_file(path)

def validate_data(df: geopandas.GeoDataFrame):
    expected_columns = ['elevation', 'geometry']
    for column in expected_columns:
        if column not in df.columns:
            raise KeyError(f'Missing column `{column}` in the dataframe.')

    if df.isnull().any().any():
        raise ValueError('Detected missing values (NaNs) in the dataframe.')
    
    if len(df[df['geometry'].is_ring == False]) > 0:
        raise ValueError('Detected non-ring geometries in the dataframe.')
    
    df.set_geometry('geometry', inplace=True)

def project_geometry(df: geopandas.GeoDataFrame, crs: str) -> geopandas.GeoDataFrame:
    return cast(geopandas.GeoDataFrame, df.to_crs(crs))

def wgs84_point_to_crs(point: Tuple[float, float], crs: str) -> Tuple[float, float]:
    return cast(Tuple[float, float], pyproj.Transformer.from_crs('EPSG:4326', crs, always_xy=True).transform(*point, errcheck=True))
