"""
NAME: CTA Transit Wrapper for Python

AUTHOR: Joe Rechenmacher
GITHUB: joerex1418
"""

from .cta import BusRoute
from .cta import BusStop
from .cta import Bus
from .cta import TrainRoute
from .cta import TrainStation
from .cta import Train
from .cta import StaticFeed
from .cta import BusTracker
from .cta import TrainTracker
from .cta import CustomerAlerts
from .cta import TransitData
from .cta import RouteSketch

from .cta import cta_stops
from .cta import stop_search
from .cta import route_transfers
from .cta import bus_routes
from .cta import bus_locations
from .cta import bus_vehicles
from .cta import bus_directions
from .cta import bus_predictions
from .cta import bus_route_stops
from .cta import train_stations
from .cta import train_arrivals
from .cta import train_positions
from .cta import train_follow

from .cta import update_static_feed


# ALIAS Assignment =========================================
BusStation = BusStop

TrainStop = TrainStation

train_stops = train_stations
# ==========================================================

