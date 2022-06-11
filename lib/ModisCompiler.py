from GenericCompiler import GenericCompiler
from glob import glob
from copy import deepcopy
from datetime import datetime
import fiona
import rasterio
import rasterio.mask
import numpy as np

"""
    Globals
"""
DATASET_DESCRIPTOR = "satellite-fire-burned-area"
ARCHIVE_NAME = "tmp.tar.gz"
WORKING_DIR = "tmp"
MAX_YEAR = 2019
MIN_YEAR = 2001
SECONDS_PER_DAY = 24*60*60

"""
    Class definition
"""
class ModisCompiler(GenericCompiler):
    """
        Class to fetch NetCDF files from the Modis mission in the Copernicus
        Data Store and compile the data in to a easy-to-use format.
    """
    def __init__(self, api_key=None):
        super().__init__(api_key)

    def compose_download_descriptor_(self, year):
        return {
            'format': 'tgz',
            'origin': 'esa_cci',
            'sensor': 'modis',
            'variable': 'grid_variables',
            'version': '5_1_1cds',
            'month': [
                '01', '02', '03',
                '04', '05', '06',
                '07', '08', '09',
                '10', '11', '12',
            ],
            'year': str(np.clip(year, MIN_YEAR, MAX_YEAR)),
            'nominal_day': '01',
            'anon_user_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def download_(self, timeframe):
        self.client.retrieve(
            DATASET_DESCRIPTOR,
            self.compose_download_descriptor_(timeframe),
            WORKING_DIR + "/" + ARCHIVE_NAME
        )

    def get_crop_indices_(self, file):
        if hasattr(self, 'lat_bounds') and hasattr(self, 'lon_bounds'):
            lon = rasterio.open(f"netcdf:{file}:lon").read().squeeze()
            lat = rasterio.open(f"netcdf:{file}:lat").read().squeeze()

            self.lat_idxs = (
                np.argmin(np.abs(deepcopy(lat)-self.lat_bounds[0])),
                np.argmin(np.abs(deepcopy(lat)-self.lat_bounds[1]))
            )

            self.lon_idxs = (
                np.argmin(np.abs(deepcopy(lon)-self.lon_bounds[0])),
                np.argmin(np.abs(deepcopy(lon)-self.lon_bounds[1]))
            )

    def aggregate_blob_(self, vars, region=None):
        self.blob = {}

        # get all unpacked files
        files = glob(WORKING_DIR+"/*.nc")

        if region:
            # get bounding box of region if given
            self.get_region_bounds_(region)

            # open first file to access crop indices
            self.get_crop_indices_(files[0])

        # add lon lat data
        self.blob["lon"] = rasterio.open(f"netcdf:{files[0]}:lon").read().squeeze()
        self.blob["lat"] = rasterio.open(f"netcdf:{files[0]}:lat").read().squeeze()
        if region:
            # crop if region
            self.blob["lon"] = self.blob["lon"][self.lon_idxs[0]:self.lon_idxs[1]+1]
            self.blob["lat"] = self.blob["lat"][self.lat_idxs[0]:self.lat_idxs[1]+1]

        # add geo2d data
        for var in vars:
            data = []
            for file in files:
                print(f"Stacking {file}")
                array = rasterio.open(f"netcdf:{file}:{var}").read().squeeze()
                if region:
                    # crop if region
                    array = array[self.lat_idxs[0]:self.lat_idxs[1]+1,\
                                  self.lon_idxs[0]:self.lon_idxs[1]+1]
                data.append(array)
            data = np.stack(data, axis=0)
            self.blob[var] = data

        # add other data
        unixtime = []
        year = []
        month = []
        idx = []
        for file in files:
            unixtime.append(int(rasterio.open(f"netcdf:{file}:time").read())\
                                              *SECONDS_PER_DAY)
            date = datetime.fromtimestamp(unixtime[-1])
            year.append(date.year)
            month.append(date.month)
            idx.append(int(f"{date.year}{date.month:02d}"))

        self.blob["unixtime"] = np.array(unixtime)
        self.blob["year"] = np.array(year)
        self.blob["month"] = np.array(month)
        self.blob["idx"] = np.array(idx)

    def sort_(self, vars):
        if hasattr(self, 'blob'):
            sorted_index = sorted(range(len(self.blob["unixtime"])),
                                  key=lambda k: self.blob["unixtime"][k])
            for key in self.blob.keys():
                if key in vars:
                    self.blob[key] = self.blob[key][sorted_index, :, :]
                elif key not in ["lon", "lat"]:
                    self.blob[key] = self.blob[key][sorted_index]

    def compile(self, output_path: str, vars: list, timeframe: tuple, region=None):
        """Compiles a pickle data blob from the given parameters.

            Args:
                output_path:
                    A string of where to put the output data.
                vars:
                    A list of strings denoting the wanted variables
                    to compile.
                timeframe:
                    A tuple of 2 integers of the start and end year of the
                    wanted data.
                region:
                    (Optional) A string of the shapefile to the wanted region.

            Returns:
                None, except for the data blob on disk.
        """
        self.create_working_dir_(WORKING_DIR)

        timeframe = np.clip(timeframe, MIN_YEAR, MAX_YEAR)
        for year in range(timeframe[0], timeframe[1]+1):
            self.download_(year)
            self.extract_(WORKING_DIR+"/"+ARCHIVE_NAME, WORKING_DIR)

        self.aggregate_blob_(vars, region)

        self.sort_(vars)

        self.dump_(output_path)

        self.delete_working_dir_(WORKING_DIR)

"""
    Testing area
"""
if __name__ == "__main__":
    # test code
    compiler = ModisCompiler("yourkeygoeshere")
    compiler.compile(output_path = "burned.pkl",
                     vars = ["burned_area", "number_of_patches"],
                     timeframe = (2019, 2019),
                     region = "../data/Sardinia.shp")
