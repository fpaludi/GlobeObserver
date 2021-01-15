# GlobeObserver

This package allows you to download satellite images from
the Google Earth Engine (GEE) service

## Installation

In order to get this package function, you will need to run the following commands:

```bash
pip install poetry
poetry config virtualenvs.create true
poetry config virtualenvs.in-project true
sudo apt-get install python-tk
```

Then install package dependencies

```bash
poetry install
poetry update
```

## Basic Trial
You can use the **main.py** to see a basic example. Please make sure of using a correct path to download the images

### Load the Images
We recommend using [QGIS](https://www.qgis.org/es/site/) to see the downloaded images 

