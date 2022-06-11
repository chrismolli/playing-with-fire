import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon

# sahara
coordinates = [(-20.684469, 23.527673),
              ( 50.127792, 23.527673),
              ( 50.127792, -1.729684),
              (-20.684469, -1.729684)]

# sardinia
coordinates = [(8.067428, 41.203210),
               (9.993755, 41.203210),
               (9.993755, 38.818011),
               (8.067428, 38.818011)]


if __name__ == "__main__":
    polygon = Polygon(coordinates)
    # epsg:4326 == WGS84
    shapefile = gpd.GeoDataFrame(crs = {'init' :'epsg:4326'})
    shapefile.loc[0,'name'] = "Sardinia"
    shapefile.loc[0, 'geometry'] = polygon
    shapefile.to_file("../data/sardinia.shp")
