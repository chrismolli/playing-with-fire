import os
import cdsapi
import shutil
import tarfile
import pickle
import fiona
import numpy as np

API_ENDPOINT = "https://cds.climate.copernicus.eu/api/v2"

class GenericCompiler:
    """
        Abstract class for CDS dataset acquisition.
    """
    def __init__(self, api_key=None):
        if api_key is None:
            raise ValueError("Missing CDS authentication key!")
        self.client = cdsapi.Client(API_ENDPOINT, api_key)

    def delete_working_dir_(self, dir):
        try:
            shutil.rmtree(dir)
        except:
            pass

    def create_working_dir_(self, dir):
        self.delete_working_dir_(dir)
        os.mkdir(dir)

    def get_region_bounds_(self, region):
        with fiona.open(region, "r") as shapefile:
            for feature in shapefile:
                coordinates = feature["geometry"]["coordinates"][0]
            self.lat_bounds = (
                np.max([c[1] for c in coordinates]),
                np.min([c[1] for c in coordinates])
            )
            self.lon_bounds = (
                np.min([c[0] for c in coordinates]),
                np.max([c[0] for c in coordinates])
            )

    def extract_(self, fname, path):
        shutil.unpack_archive(fname, path)

    def dump_(self, output_path):
        if hasattr(self, 'blob'):
            with open(output_path, "wb") as blobfile:
                pickle.dump(self.blob, blobfile)
        else:
            print("Nothing to dump.")
