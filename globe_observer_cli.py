from time import time
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import typer
import numpy as np
from skimage import exposure
import rasterio as rio
from rasterio import plot
from globe_observer.gee import SatelliteFactory, BaseGeeService
from globe_observer.gdrive_service import GDriveFactory

app = typer.Typer()


@app.command()
def available_satellites() -> List[str]:
    return SatelliteFactory.list_satellites()


@app.command()
def download_images(
    satellite_name: str,
    polygon: Path,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    bands: Optional[str] = "rgb"
):
    if not polygon.exists():
        raise FileExistsError(
            f"File {polygon} doesn't exists"
        )
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(weeks=4)

    gee_service = BaseGeeService(
        satellite_name=satellite_name,
        polygon_file=polygon,
        drive_service=GDriveFactory.build()
    )
    images_collection = gee_service.get_image_collection(
        start_date=start_date,
        end_date=end_date,
    )
    gee_service.download_to_local(
        images_collection,
        "results/",
    )

@app.command()
def show_rgb_image(
    file: Path,
):
    if not file.exists():
        raise FileExistsError(
            f"File {file} doesn't exists"
        )

    with rio.open(file) as raster:
        red = min_max_norm(raster.read(1))
        green = min_max_norm(raster.read(2))
        blue = min_max_norm(raster.read(3))
        img = np.nan_to_num(np.array([red, green, blue]), -1)
        p2, p98 = np.percentile(img, (2, 98))
        img_rescale = exposure.rescale_intensity(img, in_range=(p2, p98))
        plot.show(img_rescale)


def min_max_norm(image: np.ndarray):
    min_value = np.nanmin(image)
    max_value = np.nanmax(image)
    result = (image - min_value) / (max_value - min_value)
    return result


if __name__ == "__main__":
    app()
