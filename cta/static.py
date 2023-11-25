import io
import csv
import enum
import typing
import datetime as dt

import httpx

from . import utils
from .utils import get_db_connection
from .constants import XFER_COLS
from .constants import DIRECTIONS
from .constants import STATIC_FILES
from .ctatypes import DateLike

class Direction(enum.Enum):
    NORTH = "North"
    SOUTH = "South"
    EAST = "East"
    WEST = "West"
    
class StopType(enum.Enum):
    BUS = "Bus"
    TRAIN = "Train"
    
def _dict_factory(cursor, row):
    colnames = [c[0] for c in cursor.description]
    return {k:v for k,v in zip(colnames, row)}

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

def get_stop_transfers():
    url = "https://www.transitchicago.com/downloads/sch_data/CTA_STOP_XFERS.txt"
    
    csvdata = None
    
    with httpx.Client() as session:
        r = session.get(url)
        
        csvdata = r.text
    
    assert(csvdata)
    
    reader = csv.reader(io.StringIO(csvdata))
    
    data = []
    
    for row in reader:
        data.append({key: row[idx] for idx,key in enumerate(XFER_COLS)})
        
    return data
    
def save_stop_transfers():
    data = get_stop_transfers()
    
    for d in data:
        stop_id = int(d["stop_id"])
        d["stop_id"] = stop_id
        
        d["is_train_station"] = False
        d["is_parent_station"] = False

        if stop_id >= 40_000:
            d["is_train_station"] = True
            d["is_parent_station"] = True
        elif stop_id >= 30_000:
            d["is_train_station"] = True
            
        d['lat'] = float(d['lat'])
        d['lon'] = float(d['lon'])
        
    cols = XFER_COLS.copy()
    cols.extend(["is_train_station","is_parent_station"])

    data.sort(key=lambda x: x["stop_id"])

    with get_db_connection("cta") as conn:
        c = conn.cursor()
        
        c.execute("DROP TABLE IF EXISTS STOP_XFERS;")
        c.execute("CREATE TABLE IF NOT EXISTS STOP_XFERS ({})".format(
            ", ".join(cols)
        ))
        
        sqlkeys = ", ".join([f":{k}" for k in cols])
        
        c.executemany(
            "INSERT INTO STOP_XFERS VALUES ({});".format(sqlkeys),
            data
            )
        
        c.close()
    
def stop_data():
    data = []
    with get_db_connection("cta") as conn:
        c = conn.cursor()
        
        c.execute("SELECT * FROM stop_data;")
        
        cols = [c[0] for c in c.description]
        
        for row in c.fetchall():
            data.append({col: row[idx] for idx, col in enumerate(cols)})
        
        c.close()
    
    return data

def update_static_db(name:str):
    """
    Update static db files from directly from https://www.transitchicago.com/downloads/sch_data/
    
    (This data may be updated a couple times per month)
    
    File names:
    -----------
    - trips
    - stops
    - stop_times
    - shapes
    - routes
    - frequencies
    - calendar_dates
    - transfers
    - agency
    - calendar
    
    """
    
    name = name.replace(".txt","").strip()
    
    with utils.fetch_static_zipfile() as z:
        with z.open(f"{name}.txt") as fp:
            io_string = io.TextIOWrapper(fp,encoding="utf-8")
            reader = csv.reader(io_string)
            
            cols = [x for x in next(reader)]
            
            with get_db_connection("cta") as conn:
                c = conn.cursor()
                
                c.execute(f"DROP TABLE IF EXISTS {name};")
                c.execute(f"CREATE TABLE IF NOT EXISTS {name} ({', '.join(cols)})")
                
                sql_vars = ['?' for _ in cols]
                sql_vars = ', '.join(sql_vars)
                
                c.executemany(f"INSERT INTO {name} VALUES ({sql_vars})",reader)
                

                if name == "stop_times":
                    c.executescript(
                        """
                        CREATE TABLE stop_times_temp 
                        AS SELECT trip_id, arrival_time, stop_id, stop_sequence, stop_headsign, pickup_type 
                        FROM "stop_times";
                        
                        DROP TABLE stop_times;
                        ALTER TABLE stop_times_temp RENAME TO stop_times;
                        
                        UPDATE stop_times
                        SET 
                            stop_id = CAST(stop_id as INTEGER),
                            pickup_type = CAST(pickup_type as INTEGER), 
                            stop_sequence = CAST(stop_sequence as INTEGER)
                        """
                    )
                elif name == "routes":
                    c.executescript(
                        """
                        CREATE TABLE routes_temp
                        AS SELECT route_id, route_long_name, route_type, route_color, route_text_color 
                        FROM routes;
                        
                        DROP TABLE routes;
                        ALTER TABLE routes_temp RENAME TO routes;
                        
                        UPDATE routes
                        SET 
                            route_type = CAST(route_type as INTEGER)
                        """
                    )
                elif name == "trips":
                    c.executescript(
                        """
                        UPDATE trips
                        SET
                            direction_id = CAST(direction_id as INTEGER),
                            block_id = CAST(block_id as INTEGER),
                            wheelchair_accessible = CAST(wheelchair_accessible as INTEGER)
                        """
                    )
                elif name == "calendar":
                    c.executescript(
                        """
                        UPDATE calendar
                        SET
                            service_id = CAST(service_id as INTEGER),
                            monday = CAST(monday as INTEGER),
                            tuesday = CAST(tuesday as INTEGER),
                            wednesday = CAST(wednesday as INTEGER),
                            thursday = CAST(thursday as INTEGER),
                            friday = CAST(friday as INTEGER),
                            saturday = CAST(saturday as INTEGER),
                            sunday = CAST(sunday as INTEGER)
                        """
                    )
                elif name == "stops":
                    c.executescript(
                        """
                        CREATE TABLE stops_temp
                        AS SELECT 
                            stop_id, stop_name, stop_desc, stop_lat, stop_lon, 
                            location_type, parent_station, wheelchair_boarding FROM stops;
                        DROP TABLE stops;
                        ALTER TABLE stops_temp RENAME TO stops;
                        
                        UPDATE stops
                        SET
                            stop_id = CAST(stop_id as INTEGER),
                            stop_lat = CAST(stop_lat as REAL),
                            stop_lon = CAST(stop_lon as REAL),
                            location_type = CAST(location_type as INTEGER),
                            parent_station = CAST(parent_station as INTEGER),
                            wheelchair_boarding = CAST(wheelchair_boarding as INTEGER)
                        """
                    )

def current_service_ids(date:DateLike=None):
    date = _dateobj(date)
    
    day_of_week = date.strftime(r"%A").lower()
    
    data = []
    with get_db_connection("cta") as conn:
        c = conn.cursor()
        c.execute(f"""
                  SELECT service_id, start_date, end_date 
                  FROM calendar
                  WHERE {day_of_week} = 1;
                  """)
        
        for row in c.fetchall():
            start_date = dt.datetime.strptime(row[1],r"%Y%m%d").date()
            end_date = dt.datetime.strptime(row[2],r"%Y%m%d").date()
            if start_date <= date <= end_date:
                data.append(row[0])

    return data

def current_trip_ids(date:DateLike=None):
    service_ids = [str(_id) for _id in current_service_ids(date)]
    
    data = []
    with get_db_connection("cta") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM trips;")
        cols = [c[0] for c in c.description]
        
        for row in c.fetchall():
            row_data = {col:row[idx] for idx,col in enumerate(cols)}
            if row_data["service_id"] in service_ids:
                data.append(row_data)
    
    return data
    

class CTAdb:
    def __init__(self):
        pass
    
    def stops(
        self,*,
        stop_id:int=None,
        stop_name:str=None,
        stop_desc:str=None,
        location_type:int=None,
        parent_station:int=None,
        wheelchair_boarding=None,
        stop_type:StopType=None,
        **kwargs
        ) -> typing.List[typing.Dict]:

        wheelchair_boarding = kwargs.get("wheelchair_accessible",wheelchair_boarding)
        
        data = []
        with get_db_connection("cta") as conn:
            if kwargs.get("dict_factory") == True:
                conn.row_factory = _dict_factory
            c = conn.cursor()
            
            querylist = []
            values = []
            if stop_id:
                querylist.append("stop_id=?")
                values.append(int(stop_id))
            if stop_name:
                querylist.append("stop_name LIKE ?")
                values.append(str(stop_name))
            if stop_desc:
                querylist.append("stop_desc LIKE ?")
                values.append(str(stop_desc))
            if location_type:
                querylist.append("location_type=?")
                values.append(int(location_type))
            if parent_station:
                querylist.append("parent_station=?")
                values.append(int(parent_station))
            if stop_type:
                if stop_type is StopType.TRAIN or str(stop_type).lower() == StopType.TRAIN.value.lower():
                    querylist.append("stop_id >= 30000")
                else:
                    querylist.append("parent_station < 30000")

            # Generate Query (with WHERE statements if necessary)
            if len(querylist) > 0:
                queries = " AND ".join(querylist)
                c.execute(f"SELECT * FROM stops WHERE {queries};",values)
                cols = [c[0] for c in c.description]
                for row in c.fetchall():
                    data.append({col:row[idx] for idx, col in enumerate(cols)})
            else:
                c.execute("SELECT * FROM stops;")
                cols = [c[0] for c in c.description]
                for row in c.fetchall():
                    data.append({col:row[idx] for idx, col in enumerate(cols)})
        
        return data

    def trips(
        self,*,
        route_id=None,
        service_id=None,
        trip_id=None,
        direction_id=None,
        block_id=None,
        shape_id=None,
        direction=None,
        wheelchair_accessible=None,
        schd_trip_id,
        **kwargs
        ):
        wheelchair_accessible = kwargs.get("wheelchair_boarding", wheelchair_accessible)
        
        data = []
        with get_db_connection("cta") as conn:
            c = conn.cursor()
            
            querylist = []
            values = []
            if route_id:
                querylist.append("route_id=?")
                values.append(str(route_id))
            if service_id:
                querylist.append("service_id=?")
                values.append(str(service_id))
            if trip_id:
                querylist.append("trip_id=?")
                values.append(str(trip_id))
            if direction_id:
                querylist.append("direction_id=?")
                values.append(int(direction_id))
            if block_id:
                querylist.append("block_id=?")
                values.append(int(block_id))
            if shape_id:
                querylist.append("shape_id=?")
                values.append(str(shape_id))
            if direction:
                if direction in list(Direction):
                    direction = direction.value
                else:
                    direction = str(direction).lower()
                    if direction[0] == "n": direction = "North"
                    elif direction[0] == "s": direction = "South"
                    elif direction[0] == "e": direction = "East"
                    elif direction[0] == "w": direction = "West"
                    
                querylist.append("direction=?")
                values.append(direction)
            if wheelchair_accessible:
                querylist.append("wheelchair_accessible=?")
                values.append(int(wheelchair_accessible))
            if schd_trip_id:
                querylist.append("schd_trip_id=?")
                values.append(str(schd_trip_id))
                
            # Generate Query (with WHERE statements if necessary)
            if len(querylist) > 0:
                queries = " AND ".join(querylist)
                c.execute(f"SELECT * FROM trips WHERE {queries};",values)
                cols = [c[0] for c in c.description]
                for row in c.fetchall():
                    data.append({col:row[idx] for idx, col in enumerate(cols)})
            else:
                c.execute("SELECT * FROM trips;")
                cols = [c[0] for c in c.description]
                for row in c.fetchall():
                    data.append({col:row[idx] for idx, col in enumerate(cols)})
        
        return data

    def L_stops(
        self,*,
        stop_id:int=None,
        stop_name:str=None,
        direction_id:str=None,
        parent_station:int=None,
        ada:bool=None,
        red:bool=None,
        blue:bool=None,
        green:bool=None,
        brown:bool=None,
        purple:bool=None,
        purple_exp:bool=None,
        yellow:bool=None,
        pink:bool=None,
        orange:bool=None,
        **kwargs
        ) -> typing.List[typing.Dict]:
        """
        Query L-stops table
        
        stop_id: int
        
        stop_name: str
        
        direction_id: str
            Normal direction of train traffic at platform. Accepts various denotations
            of directions. For example, acceptable values for train stops servicing 
            'Northbound' trains are "N", "North", "Northbound", "NB".
        
        parent_station: int
            Parent station ID (or map ID) of a stop. Parent stations typically have two
            stops, with one platform servicing trains in a single direction, and another
            servicing trains in the opposite direction.        
        
        ada: bool
            Stop/station is ADA compliant
        
        red: bool
            Stop/station services the Red line
        
        blue: bool
            Stop/station services the Blue line
        
        green: bool
            Stop/station services the Green line
        
        brown: bool
            Stop/station services the Brown line
        
        purple: bool
            Stop/station services the Purple line
        
        purple_exp: bool
            Stop/station services Purple line express trains 
        
        yellow: bool
            Stop/station services the Yellow line

        pink: bool
            Stop/station services the Pink line

        orange: bool
            Stop/station services the Orange line
        """
        
        ada = kwargs.get("wheelchair_boarding",kwargs.get("wheelchair_accessible",ada))
        
        data = []
        with get_db_connection("train") as conn:
            if kwargs.get("dict_factory") == True:
                conn.row_factory = _dict_factory
            c = conn.cursor()
            
            querylist = []
            values = []
            if stop_id:
                querylist.append("stop_id=?")
                values.append(int(stop_id))
            if stop_name:
                querylist.append("stop_name LIKE ?")
                values.append(str(stop_name))
            if direction_id:
                _dir = self.__validate_direction_id(direction_id)
                querylist.append("direction_id=?")
                values.append(_dir)
            if parent_station:
                querylist.append("parent_station=?")
                values.append(int(parent_station))
            if ada:
                querylist.append("ada=?")
                values.append(ada)
            if red:
                querylist.append("red=?")
                values.append(red)
            if blue:
                querylist.append("blue=?")
                values.append(blue)
            if green:
                querylist.append("green=?")
                values.append(green)
            if green:
                querylist.append("green=?")
                values.append(green)
            if brown:
                querylist.append("brown=?")
                values.append(brown)
            if purple:
                querylist.append("purple=?")
                values.append(purple)
            if purple_exp:
                querylist.append("purple_exp=?")
                values.append(purple_exp)
            if yellow:
                querylist.append("yellow=?")
                values.append(yellow)
            if pink:
                querylist.append("pink=?")
                values.append(pink)
            if orange:
                querylist.append("orange=?")
                values.append(orange)
                
            # Generate Query (with WHERE statements if necessary)
            if len(querylist) > 0:
                queries = " AND ".join(querylist)
                c.execute(f"SELECT * FROM stops WHERE {queries};",values)
                cols = [c[0] for c in c.description]
                for row in c.fetchall():
                    data.append({col:row[idx] for idx, col in enumerate(cols)})
            else:
                c.execute("SELECT * FROM stops;")
                cols = [c[0] for c in c.description]
                for row in c.fetchall():
                    data.append({col:row[idx] for idx, col in enumerate(cols)})
        
        return data

    def update_L_stops(self):
        data = self.__get_L_stops()
        data.sort(key=lambda x: x["stop_id"])

        with get_db_connection("train") as conn:
            c = conn.cursor()
            
            c.executescript(
                """
                DROP TABLE IF EXISTS stops;
                CREATE TABLE stops (
                    stop_id INTEGER,
                    direction_id TEXT,
                    stop_name TEXT,
                    station_name TEXT,
                    station_name_descriptive TEXT,
                    parent_station INTEGER,
                    ada INTEGER,
                    red INTEGER,
                    blue INTEGER,
                    green INTEGER,
                    brown INTEGER,
                    purple INTEGER,
                    purple_exp INTEGER,
                    yellow INTEGER,
                    pink INTEGER,
                    orange INTEGER,
                    latitude REAL,
                    longitude REAL
                );
                """
            )
            
            c.executemany(
                """
                INSERT INTO stops VALUES (
                    :stop_id,
                    :direction_id,
                    :stop_name,
                    :station_name,
                    :station_name_descriptive,
                    :parent_station,
                    :ada,
                    :red,
                    :blue,
                    :green,
                    :brown,
                    :purple,
                    :purple_exp,
                    :yellow,
                    :pink,
                    :orange,
                    :latitude,
                    :longitude
                )
                """,
                data)
            
            c.close()
    
    train_stops = L_stops
    update_train_stops = update_L_stops
    
    def __get_L_stops(self) -> typing.List[typing.Dict]:
        """
        Data for L-stops/stations.
        
        Not directly from the API, but it comes from Chicago's Data Portal:
        
        https://data.cityofchicago.org/Transportation/CTA-System-Information-List-of-L-Stops/8pix-ypme
        """
        
        url = "https://data.cityofchicago.org/resource/8pix-ypme.json"
        r = httpx.get(url)
        
        data = []
        for d in r.json():
            loc = d.get("location",{})
            data.append({
                "stop_id": int(d.get("stop_id")),
                "direction_id": d.get("direction_id"),
                "stop_name": d.get("stop_name","").strip(),
                "station_name": d.get("station_name","").strip(),
                "station_name_descriptive": d.get("station_name_descriptive","").strip(),
                "parent_station": int(d.get("map_id",-1)),
                "ada": d.get("ada"),
                "red": d.get("red"),
                "blue": d.get("blue"),
                "green": d.get("g"),
                "brown": d.get("brn"),
                "purple": d.get("p"),
                "purple_exp": d.get("pexp"),
                "yellow": d.get("y"),
                "pink": d.get("pnk"),
                "orange": d.get("o"),
                "latitude": float(loc.get("latitude")),
                "longitude": float(loc.get("longitude"))
            })
        
        return data
    
    def __validate_direction_id(_dir:str,/):
        _dir = _dir.lower()
        if _dir in ("n","north","northbound","nb"):
            return "N"
        elif _dir in ("s","south","southbound","sb"):
            return "S"
        elif _dir in ("e","east","eastbound","eb"):
            return "E"
        elif _dir in ("w","west","westbound","wb"):
            return "W"
    
ctadb = CTAdb()


# ----------------------------- #
# Closest Stops
# ----------------------------- #
@typing.overload
def closest_stops(x1:float, x2:float,*, number:int, stop_type:StopType, platform_stops_only:bool=None, parent_stops_only:bool=None, group_platform_stops:bool=None) -> typing.List[typing.Dict]:...
@typing.overload
def closest_stops(point:tuple,*, number:int, stop_type:StopType, platform_stops_only:bool=None, parent_stops_only:bool=None, group_platform_stops:bool=None) -> typing.List[typing.Dict]:...
@typing.overload
def closest_stops(*,q:str, number:int, stop_type:StopType, platform_stops_only:bool=None, parent_stops_only:bool=None, group_platform_stops:bool=None) -> typing.List[typing.Dict]:...
@typing.overload
def closest_stops(*,q:str, number:int, stop_type:StopType, platform_stops_only:bool=None, parent_stops_only:bool=None, group_platform_stops:bool=None) -> typing.List[typing.Dict]:...

def closest_stops(*args,q:str=None,number:int=5,stop_type:StopType=None, child_stops_only:bool=None, parent_stops_only:bool=None, group_child_stops:bool=None) -> typing.List[typing.Dict]:
    if len(args) == 1:
        point = args[0]
    elif len(args) == 2:
        point = utils.Point(float(args[0]), float(args[1]))
    elif len(args) == 0:
        locs = utils.geosearch(q)
        point = locs[0]["point"]
    
    data = ctadb.stops(stop_type=stop_type)
    data.sort(key=lambda x: utils.distance(utils.Point(x["stop_lat"],x["stop_lon"]), point))
    
    if stop_type == "Train":
        if group_child_stops == True:
            parent_stop_data = [d for d in data if d["stop_id"] >= 40000]
            parent_stations = [d["stop_id"] for d in parent_stop_data[:number]]
            data = [d for d in data if d["parent_station"] in parent_stations]
            
            return data
        
        elif parent_stops_only == True:
            data = [d for d in data if d["stop_id"] >= 40000]
        elif child_stops_only == True:
            data = [d for d in data if 30000 <= d["stop_id"] < 40000]
    
    
    return data[:number]
    