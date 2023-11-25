import io
import csv
import typing
import sqlite3
import pathlib
import zipfile
import pprint
import datetime as dt

import httpx
from haversine.haversine import Unit
from haversine.haversine import haversine

from .ctatypes import DateLike

class Point(typing.NamedTuple):
    x: float
    y: float


OSM_BASE = "https://nominatim.openstreetmap.org/search?"
OSM_REVERSE_BASE = "https://nominatim.openstreetmap.org/reverse.php?"

pp = pprint.PrettyPrinter(sort_dicts=False, indent=2)

def _dateobj(date:DateLike):
    date = date or dt.date.today()
    if isinstance(date,(dt.date,dt.datetime)):
        if isinstance(date,dt.datetime):
            date = date.date()
    elif isinstance(date,str):
        if "-" in date:
            date = date.replace('-','')
        date = dt.datetime.strptime(date,r"%Y%m%d").date()
    return date

def _iso_to_datetime(dtstring:str):
    return dt.datetime.strptime(dtstring,r"%Y-%m-%dT%H:%M:%S")

def get_db_connection(db_name:str):
    db_name = db_name.replace(".db","")
    path_to_db = pathlib.Path(__file__).parent.joinpath("data",f"{db_name}.db")
    return sqlite3.connect(path_to_db)

TEXT = "TEXT"
BOOL = "INTEGER"
INTEGER = "INTEGER"
REAL = FLOAT = "REAL"

sql_data_types = {
    "routes": TEXT,
    "route_directions": {
        "route_id": TEXT,
        "Northbound": BOOL,
        "Southbound": BOOL,
        "Eastbound": BOOL,
        "Westbound": BOOL,
    },
    "stops": {
        "stop_id": TEXT,
        "stop_name": TEXT,
        "lat": REAL,
        "lon": REAL
    },
    "bus_route_patterns": {
        "route_id": TEXT,
        "pattern_id": INTEGER,
        "length": REAL,
        "direction": TEXT
    },
    "stop_data": {
        "stop_lat": REAL,
        "stop_lon": REAL,
        "location_type": INTEGER,
        "wheelchair_boarding": BOOL
    }
}

def create_table(db_name,*,name:str, data:typing.List[typing.Dict]):
    if not isinstance(data,list):
        data = [data]
    
    table_cols = [key for key in data[0].keys()]
    table_col_types = {}
    
    if isinstance(sql_data_types[name],str):
        for c in table_cols:
            table_col_types[c] = sql_data_types[name]
    else:
        for c in table_cols:
            table_col_types[c] = sql_data_types[name].get(c,TEXT)
    
    col_definitions = []
    for k,v in table_col_types.items():
        col_definitions.append("{} {}".format(k,v))
    
    col_definitions = ", ".join(col_definitions)
    
    insert_keys = [f":{c}" for c in table_cols]
    insert_keys = ", ".join(insert_keys)
    
    with get_db_connection(db_name) as conn:
        c = conn.cursor()

        c.execute(f"DROP TABLE IF EXISTS {name};")
        c.execute(f"""
                  CREATE TABLE {name} (
                      {col_definitions}
                  )
                  """)
        
        c.executemany(f"""
                      INSERT INTO {name} VALUES (
                          {insert_keys}
                      )
                      """,
                      data
                      )
        
        c.close()
        conn.commit()

def fetch_static_zipfile() -> zipfile.ZipFile:
    url = "https://www.transitchicago.com/downloads/sch_data/google_transit.zip"
    
    r = httpx.get(url,timeout=10)
    
    z = zipfile.ZipFile(io.BytesIO(r.read()))
    
    return z

def static_stop_data_db():
    with fetch_static_zipfile() as z:
        with z.open("stops.txt") as fp:
            io_string = io.TextIOWrapper(fp,encoding="utf-8")
            reader = csv.reader(io_string)
            
            cols = [c for c in next(reader)]
            colmap_reverse = {c_idx:c for c_idx, c in enumerate(cols)}
            
            data = []
            for row in reader:
                stop_data = {colmap_reverse[idx]:i for idx, i in enumerate(row)}
                stop_data["stop_lat"] = float(stop_data["stop_lat"])
                stop_data["stop_lon"] = float(stop_data["stop_lon"])
                stop_data.pop("stop_code")
                data.append(stop_data)
            
            create_table("cta",name="stop_data",data=data)

typing.overload
def geosearch():...
typing.overload
def geosearch():...
def geosearch(*args,**kwargs):
    if len(args) == 0:
        q = args[0]
    params = {"q": q, "format": "jsonv2", "addressdetails": "1"}
    
    r = httpx.get(OSM_BASE,params=params)
    
    data = []
    for item in r.json():
        lat = float(item["lat"])
        lon = float(item["lon"])
        data.append({
            "display_name": item["display_name"],
            "category": item["category"],
            "type": item["type"],
            "lat": lat,
            "lon": lon,
            "address": item.get("address",{}),
            "point": Point(lat, lon)
        })
    
    return data

@typing.overload
def distance(x1,y1,x2,y2):...
@typing.overload
def distance(point1,point2):...
def distance(*args):
    assert(len(args) >= 2)
    
    if len(args) == 2:
        point1 = args[0]
        point2 = args[1]
    elif len(args) == 4:
        point1 = Point(float(args[0]), float(args[1]))
        point2 = Point(float(args[2]), float(args[3]))
    else:
        raise ValueError("Function accepts 2 'Point' objects or 'x1', 'y1', 'x2', 'y2' values")        

    return haversine(point1,point2,unit=Unit.MILES)


