import typing
import datetime as dt

import httpx

from . import utils
from .auth import auth
from .fetch import fetch_all
from .constants import BUS_BASE
from .constants import ROUTE_COLS
from .constants import VEHICLE_COLS
from .constants import PREDICTION_COLS

class BusURL(typing.NamedTuple):
    STOPS: str = BUS_BASE + "/getstops"
    ROUTES: str = BUS_BASE + "/getroutes"
    VEHICLES: str = BUS_BASE + "/getvehicles"
    PATTERNS: str = BUS_BASE + "/getpatterns"
    DIRECTIONS: str = BUS_BASE + "/getdirections"
    PREDICTIONS: str = BUS_BASE + "/getpredictions"

urls = BusURL()
DEFAULT_PARAMS = {"key": auth.bus, "format": "json"}

# ---------------------------------- #
# Response parsing functions
# ---------------------------------- #
def _parse_stops_response(r:httpx.Response):
    _json = r.json()
    
    data = []
    for stop in _json.get("bustime-response",{}).get("stops",[]):
        data.append({
            "stop_id": stop["stpid"],
            "stop_name": stop["stpnm"],
            "lat": stop["lat"],
            "lon": stop["lon"],
        })
    
    return data

def _parse_vehicles_response(r:httpx.Response):
    _json = r.json()
    
    data = []
    for vehicle in _json.get("bustime-response",{}).get("vehicle",[]):
        vehicle_data = {}
        for key,val in vehicle.items():
            new_key = VEHICLE_COLS.get(key)
            if new_key:
                if new_key == "timestamp":
                    val = dt.datetime.strptime(val,r"%Y%m%d %H:%M")
                    val = val.isoformat()
                vehicle_data[new_key] = val
        
        data.append(vehicle_data)
    
    return data

def _parse_predictions_response(r:httpx.Response):
    _json = r.json()
    
    data = []
    for prediction in _json.get("bustime-response",{}).get("prd",[]):
        prediction_data = {}
        for key,val in prediction.items():
            new_key = PREDICTION_COLS.get(key)
            if new_key:
                if new_key in ("timestamp","predicted_time"):
                    val = dt.datetime.strptime(val,r"%Y%m%d %H:%M")
                    val = val.isoformat()
                prediction_data[new_key] = val
        
        data.append(prediction_data)
    
    return data
            
# ---------------------------------- #
# Bus API functions
# ---------------------------------- #
def get_all_route_directions():
    urllist = [get_directions(route["route_id"], return_url=True) 
               for route in get_routes()]
    
    responses: typing.List[httpx.Response] = fetch_all(urllist)
    
    data = []
    for r in responses:
        data_item = {
            "route_id": r.url.params["rt"],
            "Northbound": False,
            "Southbound": False,
            "Westbound": False,
            "Eastbound": False,
        }
    
        bustime_response = r.json()["bustime-response"]
        directions = [x["dir"] for x in bustime_response.get("directions")]
        
        for d in ("Northbound", "Southbound", "Westbound", "Eastbound"):
            if d in directions:
                data_item[d] = True
        
        data.append(data_item)
    
    return data

def get_all_route_patterns():
    urllist = []
    with utils.get_db_connection("bus") as conn:
        c = conn.cursor()
        
        c.execute("SELECT route_id FROM routes;")
        results = c.fetchall()
        
        for r in results:
            urllist.append(get_patterns(r[0],return_url=True))
    
    data = []
    responses: typing.List[httpx.Response] = fetch_all(urllist)
    
    for r in responses:
        route_id = r.url.params["rt"]
        
        bustime_response = r.json()["bustime-response"]
        for pattern in bustime_response.get("ptr"):
            data.append({
                "route_id": route_id,
                "pattern_id": pattern["pid"],
                "length": pattern["ln"],
                "direction": pattern["rtdir"]
            })
    
    return data

def get_stops(route_id:str,direction:str,/,**kwargs):
    params = {"key": auth.bus, "format": "json",
              "rt": route_id, "dir": direction}
    
    r = httpx.get(urls.STOPS, params=params)
    print(str(r.url))
    return r.json()
    
def get_routes():
    params = DEFAULT_PARAMS

    r = httpx.get(urls.ROUTES, params=params)
    
    data = []
    
    route: dict
    for route in r.json().get("bustime-response",{}).get("routes",[]):
        new_route_data = {}
        for key, val in route.items():
            new_key = ROUTE_COLS.get(key)
            if new_key:
                new_route_data[new_key] = val
        
        data.append(new_route_data)

    return data

def get_vehicles(route_id:str,/):
    
    params = {"key": auth.bus, "rt": route_id, "format": "json"}
    
    r = httpx.get(urls.VEHICLES, params=params)
    
    data = []
    
    vehicle: dict
    for vehicle in r.json().get("bustime-response",{}).get("vehicle",[]):
        new_vehicle_data = {}
        for key, val in vehicle.items():
            new_key = VEHICLE_COLS.get(key)
            if new_key:
                new_vehicle_data[new_key] = val
                
        data.append(new_vehicle_data)
    
    return data

def get_directions(route_id:str,/,**kwargs):
    
    params = {"key": auth.bus, "format": "json"}
    
    params["rt"] = route_id

    if kwargs.get("return_url") == True:
        return str(httpx.Request("GET",urls.DIRECTIONS,params=params).url)

    r = httpx.get(urls.DIRECTIONS,params=params)
    
    data = {
        "Northbound": None,
        "Southbound": None,
        "Westbound": None,
        "Eastbound": None,
    }
    
    bustime_response = r.json()["bustime-response"]
    directions = [x["dir"] for x in bustime_response.get("directions")]
    
    for d in ("Northbound", "Southbound", "Westbound", "Eastbound"):
        if d in directions:
            data[d] = True
        else:
            data[d] = False
    
    return data

def get_patterns(route_id:str=None,pattern_id:typing.Union[str,typing.List[str]]=None,**kwargs):
    params = DEFAULT_PARAMS.copy()
    if route_id:
        params["rt"] = route_id
    elif pattern_id:
        params["pid"] = pattern_id
    
    if kwargs.get("return_url") == True:
        return str(httpx.Request("GET",urls.PATTERNS,params=params).url)
        
    r = httpx.get(urls.PATTERNS,params=params)
    
    return r.json()


# ---------------------------------- #
# Classes (for easy interfacing)
# ---------------------------------- #
class Route:
    __slots__ = ("_data",)
    def __init__(self,route_id:str):
        with utils.get_db_connection("bus") as conn:
            c = conn.cursor()
            
            # Get PATTERNS from 'bus.db'
            patterns = []
            c.execute("""
                      SELECT pattern_id, length, direction 
                      FROM bus_route_patterns WHERE route_id=?;
                      """,[route_id])
            
            for row in c.fetchall():
                patterns.append({
                    "pattern_id": row[0],
                    "length": row[1],
                    "direction": row[2],
                })
        
            # Get DIRECTIONS from 'bus.db'
            directions = []
            c.execute("""
                      SELECT * 
                      FROM bus_route_patterns WHERE route_id=?;
                      """,[route_id])
            
            row = c.fetchone()
            for idx, direction in enumerate(("Northbound", "Southbound", "Westbound", "Eastbound")):
                if row[idx] is True:
                    directions.append(direction)
            
        
        self._data = {
            "route_id": str(route_id).strip(),
            "patterns": patterns,
            "directions": directions
        }
    
    @property
    def route_id(self) -> str:
        return self._data["route_id"]
    
    @property
    def patterns(self) -> typing.List[typing.Dict]:
        return self._data["patterns"]

    @property
    def directions(self) -> typing.List:
        return self._data["directions"]
    
    def get_stops(self,direction:str):
        params = DEFAULT_PARAMS.copy()
        params["rt"] = self.route_id
        params["dir"] = direction
        
        r = httpx.get(urls.STOPS,params=params)
        data = _parse_stops_response(r)
        return data
        
    def get_vehicles(self,vehicle_id:str=None):
        params = DEFAULT_PARAMS.copy()
        if vehicle_id != None:
            params["vid"] = vehicle_id
        else:
            params["rt"] = self.route_id
        
        r = httpx.get(urls.VEHICLES,params=params)
        data = _parse_vehicles_response(r)
        return data
    
    def get_predictions(self,stop_id:str=None,vehicle_id:str=None):
        params = DEFAULT_PARAMS.copy()
        if vehicle_id is not None:
            params["vid"] = vehicle_id
        elif stop_id is not None:
            params["stpid"] = stop_id
            params["rt"] = self.route_id
        
        r = httpx.get(urls.PREDICTIONS,params=params)
        data = _parse_predictions_response(r)
        return data
        
    
    id=route_id
    

class Stop:
    __slots__ = ("_data",)
    def __init__(self,stop_id:str):
        pass
