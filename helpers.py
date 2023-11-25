import typing
import datetime as dt

from cta import constants
from cta.constants import COLOR_LABEL_LIST

from cta.static import get_db_connection
from cta.static import _dict_factory

_StopList = typing.List[typing.Dict]

TRAIN_LINE_COLORS = dict([("red","Red"),("brown","Brown"),("blue","Blue"),("green","Green"),("orange","Orange"),("purple","Purple"),("purple_exp","Purple"),("pink","Pink"),("yellow","Yellow")])

def _serviced_routes(stop_id):
    stop_id = str(stop_id).strip()
    conn = get_db_connection("cta.db")
    conn.row_factory = _dict_factory
    c = conn.cursor()
    
    c.execute(f"SELECT trip_id FROM stop_times WHERE stop_id={stop_id}")
    all_trip_ids = [st["trip_id"] for st in c.fetchall()]
    all_trip_ids = list(set(all_trip_ids))
    print(all_trip_ids)
    all_routes = []
    for trip_id in (_trip_id for _trip_id in all_trip_ids):
        c.execute("SELECT route_id FROM trips WHERE trip_id=?", [trip_id])
        all_routes.append(c.fetchone()["route_id"])
        
    # all_routes = [trip["route_id"] for trip in c.fetchall()]
    all_routes = list(set(all_routes))
    
    conn.close()
    
    return all_routes

def add_supplementary_keys(stoplist:_StopList) -> _StopList:
    conn = get_db_connection("train.db")
    conn.row_factory = _dict_factory
    c = conn.cursor()
    for s in stoplist:
        s["is_parent"] = False
        if s["stop_id"] >= 30000:
            s["stop_type"] = "train"
            if s["stop_id"] >= 40000:
                s["is_parent"] = True
            
            c.execute("SELECT * FROM stops WHERE stop_id=?",[s["stop_id"]])
            train_stop_data = c.fetchone()
            line_list = [(key, val) for key, val in TRAIN_LINE_COLORS.items() if train_stop_data[key] == True]
            s["route_list"] = line_list
            s["stop_desc"] = train_stop_data["stop_name"]
            s["direction_id"] = train_stop_data["direction_id"]
            s["direction"] = constants.DIRECTIONS.get(s["direction_id"],"")
        
        else:
            s["stop_type"] = "bus"
            stop_desc = s["stop_desc"].lower()
            # s["route_list"] = _serviced_routes(s["stop_id"])
            if "northbound" in stop_desc:
                s["direction_id"] = "N"
                s["direction"] = "Northbound"
            elif "southbound" in stop_desc:
                s["direction_id"] = "S"
                s["direction"] = "Southbound"
            elif "eastbound" in stop_desc:
                s["direction_id"] = "E"
                s["direction"] = "Eastbound"
            elif "westbound" in stop_desc:
                s["direction_id"] = "N"
                s["direction"] = "Westbound"
    
    conn.close()
    
    return stoplist

    