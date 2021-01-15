import glob
import numpy as np
import numpy as np
import matplotlib.pyplot as plt
import rasterio as rio
from rasterio import plot
from globe_observer.gdrive_service import GDriveService
from globe_observer.gee.gee_base_service import BaseGee
 
def main():
    download_path = "results/"
    drive_service = GDriveService(
        "credentials.json",
        download_path
    )
    
    # path = "data/loma_bajo.kml"
    path = "data/NReserve/NaturalReserve_Polygon.shp"
    gee = BaseGee(
        path,
        drive_service
    )

    collections = gee.get_collection()
    print("COLLECTION", collections.size().getInfo())
    collections = gee.mask_collection(collections)
    gee.download_to_local(collections, download_path)
    
    files = glob.glob(download_path + "*.tif")
    print(files)
    for file in files:
        with rio.open(file) as raster:
            plot.show(raster.read(), adjust=None)


if __name__ == "__main__":
    main()
