from GenericCompiler import GenericCompiler
import rasterio
import rasterio.mask
import fiona
import numpy as np
from glob import glob
from copy import deepcopy
from datetime import datetime, timedelta

"""
    Globals
"""
DATASET_DESCRIPTOR = "reanalysis-era5-single-levels-monthly-means"
WORKING_DIR = "tmp"
MAX_YEAR = 2022
MIN_YEAR = 1978

"""
    Class defintion
"""
class Era5Compiler(GenericCompiler):
    def __init__(self, api_key):
        super().__init__(api_key)
        self.download_counter_ = 0

    def compose_download_descriptor_(self, year, region):
        if region:
            area = [self.lat_bounds[0], self.lon_bounds[0], \
                    self.lat_bounds[1], self.lon_bounds[1]]
        else:
            area = [90, -180, -90, 180]
        return {
            'format': 'netcdf',
            'product_type': 'monthly_averaged_reanalysis',
            'variable': [
                '10m_u_component_of_wind', '10m_v_component_of_wind', '2m_temperature',
                'high_vegetation_cover', 'low_vegetation_cover', 'skin_temperature',
                'surface_net_solar_radiation', 'total_precipitation', 'type_of_high_vegetation',
                'type_of_low_vegetation', 'volumetric_soil_water_layer_1'
            ],
            'year': str(np.clip(year, MIN_YEAR, MAX_YEAR)),
            'month': [
                '01', '02', '03',
                '04', '05', '06',
                '07', '08', '09',
                '10', '11', '12',
            ],
            'time': '00:00',
            'area': area
        }

    def get_crop_indices_(self, file):
        if hasattr(self, 'lat_bounds') and hasattr(self, 'lon_bounds'):
            lon = rasterio.open(f"netcdf:{file}:longitude").read().squeeze()
            lat = rasterio.open(f"netcdf:{file}:latitude").read().squeeze()

            self.lat_idxs = (
                np.argmin(np.abs(deepcopy(lat)-self.lat_bounds[0])),
                np.argmin(np.abs(deepcopy(lat)-self.lat_bounds[1]))
            )

            self.lon_idxs = (
                np.argmin(np.abs(deepcopy(lon)-self.lon_bounds[0])),
                np.argmin(np.abs(deepcopy(lon)-self.lon_bounds[1]))
            )

    def download_(self, timeframe, region):
        self.client.retrieve(
            DATASET_DESCRIPTOR,
            self.compose_download_descriptor_(timeframe, region),
            WORKING_DIR + f"/{self.download_counter_}.nc"
        )
        self.download_counter_ += 1

    def aggregate_blob_(self, vars, region=None):
        self.blob = {}

        # get all unpacked files
        files = glob(WORKING_DIR+"/*.nc")

        if region:
            # open first file to access crop indices
            self.get_crop_indices_(files[0])

        # add lon lat data
        self.blob["lon"] = rasterio.open(f"netcdf:{files[0]}:longitude").read().squeeze()
        self.blob["lat"] = rasterio.open(f"netcdf:{files[0]}:latitude").read().squeeze()
        if region:
            # crop if region
            self.blob["lon"] = self.blob["lon"][self.lon_idxs[0]:self.lon_idxs[1]+1]
            self.blob["lat"] = self.blob["lat"][self.lat_idxs[0]:self.lat_idxs[1]+1]

        # add geo2d data
        for var in vars:
            data = []
            for file in files:
                print(f"Stacking {file}")
                dataset = rasterio.open(f"netcdf:{file}:{var}")
                array = dataset.read().squeeze()
                if region:
                    # crop if region
                    array = array[:,self.lat_idxs[0]:self.lat_idxs[1]+1,\
                                  self.lon_idxs[0]:self.lon_idxs[1]+1]
                if hasattr(dataset, 'scales') and hasattr(dataset, 'offsets'):
                    array = dataset.scales[0] * array + dataset.offsets[0]
                data.append(array)
            data = np.concatenate(data, axis=0)
            self.blob[var] = data

        # add other data
        year = []
        month = []
        idx = []

        for file in files:
            for time in rasterio.open(f"netcdf:{file}:time").read()[0][0]:
                # gregorian calender, hours since 1900/1/1
                date = datetime(1900, 1, 1, 0, 0, 0) + timedelta(hours=int(time));
                year.append(date.year)
                month.append(date.month)
                idx.append(int(f"{date.year}{date.month:02d}"))

        self.blob["year"] = np.array(year)
        self.blob["month"] = np.array(month)
        self.blob["idx"] = np.array(idx)

    def sort_(self, vars):
        if hasattr(self, 'blob'):
            sorted_index = sorted(range(len(self.blob["idx"])),
                                  key=lambda k: self.blob["idx"][k])
            for key in self.blob.keys():
                if key in vars:
                    self.blob[key] = self.blob[key][sorted_index, :, :]
                elif key not in ["lon", "lat"]:
                    self.blob[key] = self.blob[key][sorted_index]

    def compile(self, output_path, vars, timeframe, region):
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

        if region:
            # get bounding box of region if given
            self.get_region_bounds_(region)

        timeframe = np.clip(timeframe, MIN_YEAR, MAX_YEAR)
        for year in range(timeframe[0], timeframe[1]+1):
            self.download_(year, region)

        self.aggregate_blob_(vars, region)

        self.sort_(vars)

        self.dump_(output_path)

        self.delete_working_dir_(WORKING_DIR)

"""
    Testing area
"""
if __name__ == "__main__":
    #  test code
    compiler = Era5Compiler("yourkeygoeshere")
    compiler.compile(output_path = "tmp.pkl",
                     vars = ["tp"],
                     timeframe = (2018, 2019),
                     region = "../data/Sardinia.shp")
