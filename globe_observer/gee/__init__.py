import fiona
from globe_observer.gee.gee_base_service import BaseGeeService
from globe_observer.gee.gee_satellites import SatelliteFactory

fiona.drvsupport.supported_drivers["libkml"] = "rw"
fiona.drvsupport.supported_drivers["LIBKML"] = "rw"
fiona.drvsupport.supported_drivers["kml"] = "rw"
fiona.drvsupport.supported_drivers["KML"] = "rw"

__all__ = [
    "BaseGeeService",
    "SatelliteFactory",
]
