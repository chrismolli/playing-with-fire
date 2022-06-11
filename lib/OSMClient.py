# based on:
# https://stackoverflow.com/questions/28476117/easy-openstreetmap-tile-displaying-for-python

import matplotlib.pyplot as plt
import numpy as np

import math
import requests
import io
from PIL import Image

"""
    Class definition
"""
class OSMClient:
    """
        Class to fetch data from the OSM servers.
    """
    def __init__(self):
        pass

    def deg2num(self, lat_deg, lon_deg, zoom):
      # web mercator projection
      # https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon./lat._to_tile_numbers_2
      # epsg:4326 (WSG84) to epsg:3857
      lat_rad = math.radians(lat_deg)
      n = 2.0 ** zoom
      xtile = int((lon_deg + 180.0) / 360.0 * n)
      ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
      return (xtile, ytile)

    def getImage(self, lat_deg, lon_deg, delta_lat, delta_lon, zoom):
        smurl = r"http://a.tile.openstreetmap.org/{0}/{1}/{2}.png"

        xmin, ymax = self.deg2num(lat_deg, lon_deg, zoom)
        xmax, ymin = self.deg2num(lat_deg + delta_lat, lon_deg + delta_lon, zoom)

        Cluster = Image.new('RGB',((xmax-xmin+1)*256-1,(ymax-ymin+1)*256-1) )
        for xtile in range(xmin, xmax+1):
            for ytile in range(ymin,  ymax+1):
                imgurl=smurl.format(zoom, xtile, ytile)
                # print(imgurl)
                img_data = requests.get(imgurl).content
                tile = Image.open(io.BytesIO(img_data))
                Cluster.paste(tile, box=((xtile-xmin)*256 ,  (ytile-ymin)*255))

        return np.asarray(Cluster), (xmin, xmax, ymin, ymax)

if __name__ == '__main__':
    # test code
    client = OSMClient()
    a = client.getImage(38.5, -77.04, 0.02,  0.05, 13)
    fig = plt.figure()
    # fig.patch.set_facecolor('white')
    plt.imshow(np.asarray(a))
    plt.show()
