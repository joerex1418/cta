import io
import csv
import typing
import sqlite3
import pathlib
import zipfile
import pprint

import httpx


pp = pprint.PrettyPrinter(sort_dicts=False, indent=2)


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


def download_static_zipfile() -> zipfile.ZipFile:
    url = "https://www.transitchicago.com/downloads/sch_data/google_transit.zip"
    
    r = httpx.get(url,timeout=10)
    
    z = zipfile.ZipFile(io.BytesIO(r.read()))
    
    return z


def static_stop_data_db():
    with download_static_zipfile() as z:
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

