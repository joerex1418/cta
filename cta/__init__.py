"""
# PyTransit-CTA
CTA Transit Wrapper for Python

AUTHOR: Joe Rechenmacher
GITHUB: joerex1418
"""

# from .cta.cta import BusRoute
# from .cta.cta import BusStop
# from .cta.cta import Bus
# from .cta.cta import TrainRoute
# from .cta.cta import TrainStation
# from .cta.cta import Train
# from .cta.cta import StaticFeed
# from .cta.cta import BusTracker
# from .cta.cta import TrainTracker
# from .cta.cta import CustomerAlerts
# from .cta.cta import TransitData
# from .cta.cta import RouteSketch

# from .cta.cta import cta_stops
# from .cta.cta import stop_search
# from .cta.cta import route_transfers
# from .cta.cta import bus_routes
# from .cta.cta import bus_locations
# from .cta.cta import bus_vehicles
# from .cta.cta import bus_directions
# from .cta.cta import bus_predictions
# from .cta.cta import bus_route_stops
# from .cta.cta import train_stations
# from .cta.cta import train_arrivals
# from .cta.cta import train_positions
# from .cta.cta import train_follow

# from .cta.cta import update_static_feed

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
from .cta import StopSearch
from .cta import TransitData
from .cta import RouteSketch

from .cta import cta_stops
from .cta import cta_trips
from .cta import stop_search
from .cta import route_transfers
from .cta import bus_routes
from .cta import bus_locations
from .cta import bus_vehicles
from .cta import bus_directions
from .cta import bus_predictions
from .cta import bus_route_stops
from .cta import bus_stop_times
from .cta import train_stations
from .cta import train_arrivals
from .cta import train_positions
from .cta import train_follow
from .cta import train_stop_times

from .cta import update_static_feed
from .cta import check_feed

# ALIAS Assignment =========================================
BusStation = BusStations = BusStops = BusStop

TrainStop = TrainStation

Lookup = StopSearch

train_stops = train_stations
# ==========================================================

