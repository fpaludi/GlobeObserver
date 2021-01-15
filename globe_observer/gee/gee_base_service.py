from typing import List, Tuple
import time
import shapely
import fiona
import ee
import ee.mapclient
import geopandas as gpd
from geetools import batch
from pathlib import Path
from functools import partial
from globe_observer.gdrive_service import GDriveService

class BaseGee:
    _MASK_VALUE = -9999

    def __init__(
        self,
        polygon_file: str,
        drive_service: GDriveService,
    ):
        self._polygon = self._load_polygon(polygon_file)
        self._polygon_name = Path(polygon_file).name.split(".")[0]
        self._drive_client = drive_service
        try:
            ee.Initialize()
        except ee.EEException as e:
            print('The Earth Engine package failed to initialize!')

    @staticmethod
    def _load_polygon(polygon_file: Path):
        kwargs = {}
        extension = str(polygon_file).lower().split(".")[-1]
        if "kml" in extension:
            kwargs["driver"] = "KML"

        gdf = gpd.read_file(polygon_file, **kwargs)
        polygon = gdf.loc[0, 'geometry']
        polygon.geo_interface = polygon.__geo_interface__.copy()

        if "kml" in extension:
            coordinates = polygon.geo_interface['coordinates'][0]
            polygon.geo_interface['coordinates'] = tuple(
                [tuple([(x[0], x[1]) for x in coordinates])]
            )
        return polygon
    
    def get_collection(
        self,
        start_date: str ='2019-02-10', 
        end_date: str ='2019-02-28',
        cloud_coverage: int = 5,
        bands: Tuple = ('B4', 'B3', 'B2', 'B8')
    ) -> ee.Collection:
        cloud_filter = ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_coverage)
        collection = ee.ImageCollection('COPERNICUS/S2')\
                       .filterDate(start_date, end_date)\
                       .filter(cloud_filter)\
                       .filterBounds(self._polygon.geo_interface)\
                       .select(bands)
        return collection

    def mask_collection(
        self,
        collection: ee.Collection
    ) -> ee.Collection:
        polygon_coords = ee.Geometry.Polygon(
            [(x[0], x[1]) for x in self._polygon.exterior.coords]
        )
        n_bands = len(collection.getInfo()["features"][0]["bands"])
        def _mask_image(image):
            """ GEE has some limitations for custom map functions.
            In this way the necessary data is shared through the scope
            """
            mask_list = [BaseGee._MASK_VALUE] * n_bands
            mask = ee.Image.constant(mask_list).clip(polygon_coords).mask()
            mask_image = ee.Image(image).updateMask(mask)
            return mask_image
        
        collection_list = collection.toList(collection.size())
        list_masked = collection_list.map(_mask_image)
        masked_collection = ee.ImageCollection(list_masked)
        return masked_collection
        
    def get_ndvi(self, collection: ee.Collection) -> ee.Collection:
        ndvi_collection_func = partial(self._ndvi_collection, polygon=self._polygon)
        collection_list = collection.toList(collection.size())
        list_ndvi     = collection_list.map(ndvi_collection_func)
        ndvi_collection   = ee.ImageCollection(list_ndvi)
        return ndvi_collection 

    @staticmethod
    def _ndvi_collection(image: ee.Image) -> ee.Image:
        filter_image = image.select(['B8', 'B4'])
        ndvi_image = filter_image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return ndvi_image

    def download_to_drive(
        self,
        collection: ee.Collection,
        folder: str = "GLOBE_OBSERVER_COLLECTIONS",
        scale: int = 10,
        verbose: bool = True
    ):
        params = {
            # 'fileNamePrefix': name_prefix,
            "namePattern": 'go_image_{polygon_name}_{system_date}',
            "datePattern": 'yyyy-MM-dd',
            'folder': folder,
            'region': self._polygon.bounds,
            'scale': scale,
            'fileFormat': 'GeoTIFF',
            'maxPixels': 1e13,
            'extra': {"polygon_name": self._polygon_name},
            'verbose': verbose,
        }
        drive_tasks = batch.Export.imagecollection.toDrive(collection, **params)
        finsished_tasks = 0
        finish_states = [ee.batch.Task.State.COMPLETED, ee.batch.Task.State.FAILED]
        while finsished_tasks < len(drive_tasks):
            task_states = [task.status()["state"] for task in drive_tasks]
            finish_tasks = [
                state in finish_states
                for state in task_states
            ]
            finsished_tasks = sum(finish_tasks)
            print(f"Finished {finsished_tasks}/{len(drive_tasks)}: {task_states}")

    def download_to_local(
        self,
        collection: ee.Collection,
        download_path: str,
    ):
        tmp_folder_name = "TMP_GO_FOLDER"
        self.download_to_drive(
            collection,
            folder=tmp_folder_name,
        )
        last_path = self._drive_client.download_path
        self._drive_client.download_path = download_path
        self._drive_client.download_files_from_folder(tmp_folder_name)
        #self._drive_client.remove_folder(tmp_folder_name)
        self._drive_client.download_path = last_path
