from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class BaseSatellite:
    gee_name: str
    rgb_bands: Tuple[str, str, str]
    cloud_filter: bool
    nri_band: Optional[str]


@dataclass
class Sentinell2(BaseSatellite):
    gee_name: str = "COPERNICUS/S2"
    rgb_bands: Tuple[str, str, str] = ("B4", "B3", "B2")
    cloud_filter: bool = True
    nri_band: str = "B8"


@dataclass
class Landsat8(BaseSatellite):
    gee_name: str = "LANDSAT/LC08/C02/T1_L2"
    rgb_bands: Tuple[str, str, str] = ("SR_B4", "SR_B3", "SR_B2")
    cloud_filter: bool = False
    nri_band: str = "SR_B5"


class SatelliteFactory:
    _SATELLITE_COLLECTION = {
        "Sentinell2": Sentinell2,
        "Landsat8": Landsat8,
    }

    @classmethod
    def build_satellite(cls, name: str) -> BaseSatellite:
        try:
            satellite = cls._SATELLITE_COLLECTION[name]
        except KeyError:
            raise KeyError(
                f"Missing satellite. Available satellites are: {cls._SATELLITE_COLLECTION.keys()}"
            )
        else:
            return satellite

    @classmethod
    def list_satellites(cls) -> List[str]:
        return list(cls._SATELLITE_COLLECTION.keys())
