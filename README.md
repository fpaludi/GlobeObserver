# GlobeObserver

This package allows you to download satellite images in .tif format from
the Google Earth Engine (GEE) service

## Installation

In order to get this package function, you will need to run the following commands:

```bash
sudo apt-get install python3-tk
make start_project
```

This creates a virtual environment with all you need to download
images from GEE.

## Basic Trial
The project provides a simple CLI in order to download satellite images.

You can access de CLI help by running:
```bash
python3 globe_observer_cli.py --help
```

### Examples
To download some satellite images you can run:

```bash
python3 globe_observer_cli.py download-images Sentinell2 data/loma_bajo.kml
```

or providing the dates of interest by running
```bash
python3 globe_observer_cli.py download-images Sentinell2 data/NReserve/NaturalReserve_Polygon.shp --start-date 2021-06-14 --end-date 2021-06-15
```

then you can visualize the results by running something like:
```bash
python3 globe_observer_cli.py show-rgb-image results/gee_image_Sentinell2_NaturalReserve_Polygon_2021-06-14.tif
```

![Alt text](docs/show_reserve.png?raw=true "Title")


### Load the Images
An interesting software to see downloaded data is [QGIS](https://www.qgis.org/es/site/)
