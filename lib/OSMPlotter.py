import matplotlib.pyplot as plt
from OSMClient import OSMClient
import matplotlib.patches as patches
import matplotlib as mpl
import math
import fiona
import numpy as np

"""
    Globals
"""
PIXELS_PER_TILE = 256 # px
GRID_SIZE = 0.25 # degree

"""
    Class defintion
"""
class OSMPlotter:
    """
        Class to visualize data on top of a OSM base layer.
    """
    def __init__(self, zoom = 10, fontsize=16):
        self.figure = None
        self.zoom = zoom
        self.client = OSMClient()
        self.fontsize = fontsize

    def tileToPixel(self, tileNum):
        # since we converted the geographical coordinates to OSM tile numbers in a specific zoom
        # level we need to convert them further to pixels to be able to project our gridcells on top.
        # calculates the amount of pixels from the origin for a given tile
        return tileNum * PIXELS_PER_TILE

    def deg2px(self, lat_deg, lon_deg, zoom):
        # web mercator projection
        # https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon./lat._to_tile_numbers_2
        # epsg:4326 (WSG84) to epsg:3857
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        x = (lon_deg + 180.0) / 360.0 * n * PIXELS_PER_TILE
        y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * PIXELS_PER_TILE
        return (x - self.px_x0, y - self.px_y0)

    def calculatePixelRangeOfBaseMap(self):
        self.px_x0 = self.tileToPixel(self.tile_numbers[0])
        self.px_y0 = self.tileToPixel(self.tile_numbers[2])
        self.px_x1 = self.tileToPixel(self.tile_numbers[1]) + PIXELS_PER_TILE
        self.px_y1 = self.tileToPixel(self.tile_numbers[3]) + PIXELS_PER_TILE

    def plotBaseMap(self, region, figsize=(14,36)):
        with fiona.open(region, "r") as shapefile:
                for feature in shapefile:
                    coordinates = feature["geometry"]["coordinates"][0]

        self.lon0 = np.min([c[0] for c in coordinates])
        self.lon1 = np.max([c[0] for c in coordinates])
        delta_lon = self.lon1 - self.lon0

        self.lat0 = np.min([c[1] for c in coordinates])
        self.lat1 = np.max([c[1] for c in coordinates])
        delta_lat = self.lat1 - self.lat0

        # get image data
        self.map_image, self.tile_numbers = self.client.getImage(self.lat0, self.lon0, delta_lat, delta_lon, self.zoom)

        self.calculatePixelRangeOfBaseMap()

        self.figure = plt.figure(figsize=figsize)
        plt.imshow(self.map_image)

        plt.xlabel("LON [°]")
        plt.xticks(np.linspace(0,self.map_image.shape[1], num=12, endpoint=False).astype('int'),\
                   np.round(np.linspace(0,1,num=12,endpoint=False)*delta_lon + self.lon0,4), rotation=90)
        plt.ylabel("LAT [°]")
        plt.yticks(np.linspace(0,self.map_image.shape[0], num=12, endpoint=False).astype('int'),\
                   np.round(np.linspace(0,1,num=12,endpoint=False)*delta_lat + self.lat0,4))

    def plotRegion(self, region):
        with fiona.open(region, "r") as shapefile:
                for feature in shapefile:
                    coordinates = feature["geometry"]["coordinates"][0]
        x0, y0 = self.deg2px(self.lat0, self.lon0, self.zoom)
        x1, y1 = self.deg2px(self.lat1, self.lon1, self.zoom)
        dx = x1-x0
        dy = y1-y0
        bounding_box = patches.Rectangle(
                        (x0, y0), dx, dy,
                        linewidth=2, edgecolor='g', facecolor='none')
        plt.gca().add_patch(bounding_box)

    def plotDataAlignment(self, blob, color="r"):
        # create mesh for coordinates
        lats, lons = np.meshgrid(blob["lat"], blob["lon"])

        for i in range(len(blob["lat"])):
            for j in range(len(blob["lon"])):
                # calc box center
                lat = lats[j,i]
                lon = lons[j,i]
                cx, cy = self.deg2px(lat, lon, self.zoom)
                plt.plot(cx,cy,'o',color=color)

                # calc box size
                x0, y0 = self.deg2px(lat-GRID_SIZE/2, lon-GRID_SIZE/2, self.zoom)
                x1, y1 = self.deg2px(lat+GRID_SIZE/2, lon+GRID_SIZE/2, self.zoom)
                dx = x1-x0
                dy = y1-y0

                # add box
                rect = patches.Rectangle((x0, y0), dx, dy, linewidth=1, edgecolor=color, facecolor='none')
                plt.gca().add_patch(rect)

    def plotData(self, blob, var, colormap="Reds", alpha=1.0, compression_mode="sum", alpha_by_value=True, cmap_suffix=""):
        # create mesh for coordinates
        lats, lons = np.meshgrid(blob["lat"], blob["lon"])

        # sum over time
        if compression_mode == "mean":
            data = np.mean(blob[var], axis=0)
        elif compression_mode == "sum":
            data = np.sum(blob[var], axis=0)
        min_data = np.min(data)
        max_data = np.max(data)

        # create cmap
        cmap = plt.get_cmap(colormap, 100)

        # create norm
        norm = mpl.colors.Normalize(vmin=min_data,
                                    vmax=max_data)

        # creating ScalarMappable
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])

        for i in range(len(blob["lat"])):
            for j in range(len(blob["lon"])):
                # calc box center
                lat = lats[j,i]
                lon = lons[j,i]

                # calc box size
                x0, y0 = self.deg2px(lat-GRID_SIZE/2, lon-GRID_SIZE/2, self.zoom)
                x1, y1 = self.deg2px(lat+GRID_SIZE/2, lon+GRID_SIZE/2, self.zoom)
                dx = x1-x0
                dy = y1-y0

                # transparency
                if alpha_by_value:
                    alpha_ = np.clip(abs(float(data[i,j]/max_data))*alpha,0.1,1)
                else:
                    alpha_ = alpha

                # add box
                rect = patches.Rectangle((x0, y0), dx, dy,
                                            linewidth=1,
                                            edgecolor=cmap(norm(data[i,j])),
                                            facecolor=cmap(norm(data[i,j])),
                                            alpha=alpha_
                                            )
                plt.gca().add_patch(rect)

        # add colorbar
        plt.colorbar(sm, label=var+cmap_suffix, ticks=np.linspace(min_data, max_data, 10),fraction=0.060, pad=0.04)
