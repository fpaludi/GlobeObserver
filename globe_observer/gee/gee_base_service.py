from typing import List, Tuple
from datetime import datetime
import json
import ee

import ee.mapclient
import geopandas as gpd
from geetools import batch
from pathlib import Path
from functools import partial
from google.oauth2.credentials import Credentials
from globe_observer.gdrive_service import GDriveService
from globe_observer.gee import gee_satellites


class GlobeObseverException(Exception):
    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        return self._msg


class BaseGeeService:
    _MASK_VALUE = -9999

    def __init__(
        self, satellite_name: str, polygon_file: Path, drive_service: GDriveService,
    ):
        self._satellite_name = satellite_name
        self._satellite = gee_satellites.SatelliteFactory.build_satellite(
            satellite_name
        )
        self._polygon = self._load_polygon(polygon_file)
        self._polygon_name = Path(polygon_file).name.split(".")[0]
        self._drive_client = drive_service
        try:
            tokens = json.load(open("gee_credentials.json"))
            refresh_token = tokens['refresh_token']
            credentials=Credentials(
                None,
                refresh_token=refresh_token,
                token_uri=ee.oauth.TOKEN_URI,
                client_id=ee.oauth.CLIENT_ID,
                client_secret=ee.oauth.CLIENT_SECRET,
                scopes=ee.oauth.SCOPES
            )
            ee.Initialize(credentials=credentials)
        except ee.EEException as e:
            print("The Earth Engine package failed to initialize!")

    @staticmethod
    def _load_polygon(polygon_file: Path):
        kwargs = {}
        extension = str(polygon_file).lower().split(".")[-1]
        if "kml" in extension.lower():
            kwargs["driver"] = "KML"

        gdf = gpd.read_file(polygon_file, **kwargs)
        polygon = gdf.loc[0, "geometry"]
        polygon.geo_interface = polygon.__geo_interface__.copy()

        if "kml" in extension:
            coordinates = polygon.geo_interface["coordinates"][0]
            polygon.geo_interface["coordinates"] = tuple(
                [tuple([(x[0], x[1]) for x in coordinates])]
            )
        return polygon

    def get_image_collection(
        self,
        start_date: datetime,
        end_date: datetime,
        cloud_coverage: int = 5,
        # bands: Tuple = ("rgb", "nri"),
        bands: Tuple = ("rgb",),
    ) -> ee.Collection:
        satellite_bands = self._get_satellite_bands(bands)
        collection = (
            ee.ImageCollection(self._satellite.gee_name)
            .filterDate(start_date.isoformat(), end_date.isoformat())
            .filterBounds(self._polygon.geo_interface)
            .select(satellite_bands)
        )
        if self._satellite.cloud_filter:
            cloud_filter = ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_coverage)
            collection = collection.filter(cloud_filter)

        try:
            collection = self._mask_image_collection(collection, len(satellite_bands))
        except (ee.ee_exception.EEException, IndexError):
            raise GlobeObseverException(
                f"Not images in the time window {start_date.date()} to {end_date.date()}, try another"
            )
        return collection

    def _mask_image_collection(self, collection: ee.Collection, n_bands: int) -> ee.Collection:

        polygon_coords = ee.Geometry.Polygon(
            [(x[0], x[1]) for x in self._polygon.exterior.coords]
        )

        def _mask_image(image):
            """ GEE has some limitations for custom map functions.
            In this way the necessary data is shared through the scope
            """
            mask_list = [BaseGeeService._MASK_VALUE] * n_bands
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
        list_ndvi = collection_list.map(ndvi_collection_func)
        ndvi_collection = ee.ImageCollection(list_ndvi)
        return ndvi_collection

    def _ndvi_collection(self, image: ee.Image) -> ee.Image:
        nri_band = self._satellite.nri_band
        red_band = self._satellite.rgb_bands[0]
        filter_image = image.select([nri_band, red_band])
        ndvi_image = filter_image.normalizedDifference([nri_band, red_band]).rename(
            "NDVI"
        )
        return ndvi_image

    def _get_satellite_bands(self, bands: Tuple) -> List[str]:
        result_bands = []
        if "rgb" in bands:
            result_bands.extend(list(self._satellite.rgb_bands))
        if "nri" in bands:
            result_bands.extend([self._satellite.nri_band])
        return result_bands

    def download_to_drive(
        self,
        collection: ee.Collection,
        folder: str = "GLOBE_OBSERVER_COLLECTIONS",
        scale: int = 10,
        verbose: bool = True,
    ):
        params = {
            "namePattern": "gee_image_{satellite_name}_{polygon_name}_{system_date}",
            "datePattern": "yyyy-MM-dd",
            "folder": folder,
            "region": self._polygon.bounds,
            "scale": scale,
            "fileFormat": "GeoTIFF",
            "maxPixels": 1e13,
            "extra": {
                "polygon_name": self._polygon_name,
                "satellite_name": self._satellite_name,
            },
            "verbose": verbose,
        }
        drive_tasks = batch.Export.imagecollection.toDrive(collection, **params)
        finsished_tasks = 0
        finish_states = [ee.batch.Task.State.COMPLETED, ee.batch.Task.State.FAILED]
        while finsished_tasks < len(drive_tasks):
            task_states = [task.status()["state"] for task in drive_tasks]
            finish_tasks = [state in finish_states for state in task_states]
            finsished_tasks = sum(finish_tasks)
            print(f"Image Processed: {finsished_tasks}/{len(drive_tasks)}")

    def download_to_local(
        self, collection: ee.Collection, download_path: str,
    ):
        tmp_folder_name = "TMP_GO_FOLDER"
        self.download_to_drive(
            collection, folder=tmp_folder_name,
        )
        print("Downloading to local disk...")
        last_path = self._drive_client.download_path
        self._drive_client.download_path = download_path
        self._drive_client.download_files_from_folder(tmp_folder_name)
        self._drive_client.remove_folder(tmp_folder_name)
        self._drive_client.download_path = last_path
