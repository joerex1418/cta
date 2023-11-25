import typing
import datetime as dt

import httpx

from . import utils
from .auth import auth
from .constants import TRAIN_BASE

class TrainURL(typing.NamedTuple):
    ARRIVALS: str = TRAIN_BASE + "/ttarrivals.aspx"
    PREDICTIONS: str = TRAIN_BASE + "/ttarrivals.aspx"
    FOLLOW: str = TRAIN_BASE + "/ttfollow.aspx"
    POSITIONS: str = TRAIN_BASE + "/ttpositions.aspx"
    LOCATIONS: str = TRAIN_BASE + "/ttpositions.aspx"

urls = TrainURL()
DEFAULT_PARAMS = {"key": auth.train, "outputType": "JSON"}
_now = dt.datetime.today()
# ---------------------------------- #
# Response parsing functions
# ---------------------------------- #
def _parse_arrivals_response(r:httpx.Response):
    _json: dict = r.json()
    
    data = []
    for d in _json.get("ctatt",{}).get("eta",[]):
        lat = d.get("latitude")
        lon = d.get("longitude")
        heading = d.get("heading")
        if lat:
            lat = float(lat)
        if lon:
            lon = float(lon)
        if heading:
            heading = int(heading)
            
        eta = d.get("arrT")
        due_in = None
        if eta:
            eta_obj = utils._iso_to_datetime(eta)
            due_in = round((eta_obj - _now).seconds / 60)
        
        data.append({
            "stop_id": int(d.get("stpId")),
            "parent_station": int(d.get("staId")),
            "station_name": d.get("staNm"),
            "stop_description": d.get("stpDe"),
            "run_number": d.get("rn"),
            "route_id": d.get("rt"),
            "dest_stop_id": d.get("destSt"),
            "dest_stop_name": d.get("destNm"),
            "direction_code": d.get("trDr"),
            "time_of_prediction": d.get("prdt"),
            "eta": eta,
            "due_in": due_in,
            "is_approaching": bool(int(d.get("isApp",0))),
            "is_scheduled": bool(int(d.get("isSch",0))),
            "is_delayed": bool(int(d.get("isDly",0))),
            "has_fault": bool(int(d.get("isFlt",0))),
            "latitude": lat,
            "longitude": lon,
            "heading": heading,
        })
    
    return data

def _parse_follow_response(r:httpx.Response):
    _json: dict = r.json()

    pos = _json.get("ctatt",{}).get("position",{})
    lat, lon = pos.get("lat"), pos.get("lon")
    
    if lat:
        lat = float(lat)
    if lon:
        lon = float(lon)
    
    data = []
    for d in _json.get("ctatt",{}).get("eta",[]):
        
        eta = d.get("arrT")
        due_in = None
        if eta:
            eta_obj = utils._iso_to_datetime(eta)
            due_in = round((eta_obj - _now).seconds / 60)
        
        data.append({
            "stop_id": int(d.get("stpId")),
            "parent_station": int(d.get("staId")),
            "station_name": d.get("staNm"),
            "stop_description": d.get("stpDe"),
            "run_number": d.get("rn"),
            "route_id": d.get("rt"),
            "dest_stop_id": d.get("destSt"),
            "dest_stop_name": d.get("destNm"),
            "direction_code": d.get("trDr"),
            "time_of_prediction": d.get("prdt"),
            "eta": eta,
            "due_in": due_in,
            "is_approaching": bool(int(d.get("isApp",0))),
            "is_scheduled": bool(int(d.get("isSch",0))),
            "is_delayed": bool(int(d.get("isDly",0))),
            "has_fault": bool(int(d.get("isFlt",0))),
            "flags": d.get("flags"),
            "latitude": lat,
            "longitude": lon,
        })
    
    return data

# ---------------------------------- #
# Train API functions
# ---------------------------------- #
def get_arrivals(stop_id:int,*,route_id=None,maxresults:int=None) -> typing.List[typing.Dict]:
    params = DEFAULT_PARAMS.copy()
    
    stop_id = int(stop_id)
    if stop_id >= 40000:
        params["mapid"] = stop_id
    else:
        params["stpid"] = stop_id
    
    if route_id:
        params["rt"] = route_id

    if maxresults:
        params["max"] = maxresults
    
    
    r = httpx.get(urls.ARRIVALS,params=params)
    
    data = _parse_arrivals_response(r)
    
    return data

def follow(run_number,/) -> typing.List[typing.Dict]:
    """
    Retrieves a list of arrival predictions for a given train at all upcoming stops 
    (up to 20 minutes in the future or to the end of its trip)
    
    run_number
        Train number/vehicle id for a specific train
    """
    params = DEFAULT_PARAMS.copy()
    params["runnumber"] = str(run_number).strip()
    
    r = httpx.get(urls.FOLLOW,params=params)
    
    data = _parse_follow_response(r)
    
    return data
    
    

