import os
import lxml
import zipfile
import requests
import pandas as pd
import datetime as dt
from io import BytesIO
from bs4 import BeautifulSoup as bs

from .constants import CTA_BUS_BASE
from .constants import CTA_BUS_API_KEY
from .constants import ALT_BUS_API_KEY
from .constants import STOP_COLS

# 0-29999       = Bus stops
# 30000-39999   = Train stops
# 40000-49999   = Train stations (parent stops)

def split_datetime(dt_str):
    r = dt_str
    date = r[:8]
    date = f"{date[:4]}/{date[4:6]}/{date[6:]}"
    time = r[9:]
    return {"date":date,"time":time}

def get_now():
    return dt.datetime.now()

def filter_direction(direction):
    if "north" in direction.lower():
        direction = "Northbound"
    elif "south" in direction.lower():
        direction = "Southbound"
    elif "east" in direction.lower():
        direction = "Eastbound"
    elif "west" in direction.lower():
        direction = "Westbound"

    if direction.lower() == "n":
        direction = "Northbound"
    elif direction.lower() == "s":
        direction = "Southbound"
    elif direction.lower() == "e":
        direction = "Eastbound"
    elif direction.lower() == "w":
        direction = "Westbound"
    
    return direction

def get_stops():
    df = pd.read_csv(os.path.abspath("./cta/cta_google_transit/stops.txt"),index_col=False,dtype={"stop_id":"str","stop_code":"str","parent_station":"str"})
    df.rename(columns={"parent_station":"map_id"},inplace=True)
    return df

def get_trips():
    df = pd.read_csv(os.path.abspath("./cta/cta_google_transit/trips.txt"),index_col=False,dtype="str")
    return df

def get_calendar():
    df = pd.read_csv(os.path.abspath("./cta/cta_google_transit/calendar.txt"),index_col=False,dtype="str")
    return df

def get_transfers():
    df = pd.read_csv(os.path.abspath("./cta/cta_google_transit/transfers.txt"),index_col=False,dtype="str")
    return df

def get_stop_times():
    df = pd.read_csv(os.path.abspath("./cta/cta_google_transit/stop_times.txt"),index_col=False,dtype={"trip_id":"str","stop_id":"int","shape_dist_traveled":"int"})
    return df

def get_route_transfers():
    df = pd.read_csv(os.path.abspath("./cta/cta_route_transfers.csv"),index_col=False)
    return df

def update_route_transfers():
    url = "https://www.transitchicago.com/downloads/sch_data/CTA_STOP_XFERS.txt"
    names = ['rt','pathway_mode','stop_name','stop_id','stop_lat','stop_lon','map_id_ext','transfers']
    df = pd.read_csv(url,delimiter=",",names=names,index_col=False)
    new_order = ['rt','pathway_mode','stop_name','stop_id','map_id_ext','stop_lat','stop_lon','transfers']
    df.to_csv(os.path.abspath("./cta/cta_route_transfers.csv"),index=False)

def get_train_stations():
    df = pd.read_csv(os.path.abspath("./cta/cta_train_stations.csv"),index_col=False,dtype={"stop_id":"str"})
    new_order = ['stop_id','map_id','stop_name','station_name','station_descriptive_name','direction_id','ada','red','blue','green','brown','purple','purple_exp','yellow','pink','orange','lat','lon']
    return df

def update_train_stations():
    url = "https://data.cityofchicago.org/resource/8pix-ypme.json"
    response = requests.get(url)
    columns = (
        "stop_id",
        "stop_name",
        "station_name",
        "station_descriptive_name",
        "direction_id",
        "map_id",
        "ada",
        "red",
        "blue",
        "green",
        "brown",
        "purple",
        "purple_exp",
        "yellow",
        "pink",
        "orange",
        "lat",
        "lon")
    data = []
    for s in response.json():
        row_data = [
            s["stop_id"],
            s["stop_name"],
            s["station_name"],
            s["station_descriptive_name"],
            s["direction_id"],
            s["map_id"],
            s["ada"],
            s["red"],
            s["blue"],
            s["g"],
            s["brn"],
            s["p"],
            s["pexp"],
            s["y"],
            s["pnk"],
            s["o"],
            s["location"]["latitude"],
            s["location"]["longitude"]
        ]
        data.append(row_data)
    df = pd.DataFrame(data=data,columns=columns)
    df.to_csv(os.path.abspath("./cta/cta_train_stations.csv"),index=False)

def get_bus_routes():
    df = pd.read_csv(os.path.abspath("./cta/cta_bus_routes.csv"),index_col=False)
    return df

def update_bus_routes():
    params = {
        "format":"json"}
    key = CTA_BUS_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_BUS_API_KEY
    url = CTA_BUS_BASE + f"/getroutes?key={key}"
    response = requests.get(url,params=params)
    data = []
    for r in response.json()["bustime-response"]["routes"]:
        row_data = [r["rt"],r["rtnm"],r["rtclr"],r["rtdd"]]
        data.append(row_data)
    df = pd.DataFrame(data=data,columns=["rt","rtnm","rtclr","rtdd"])

    df.to_csv(os.path.abspath("./cta/cta_bus_routes.csv"),index=False)

def get_bus_route_stops(route,direction):
    direction = filter_direction(direction)
    
    params = {
        "key":CTA_BUS_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_BUS_API_KEY,
        "rt":route,
        "dir":direction,
        "format":"json"}
    url = CTA_BUS_BASE + f"/getstops?"
    response = requests.get(url,params=params)
    data = []
    for s in response.json()["bustime-response"]["stops"]:
        row_data = [
            s.get("stpid"),
            s.get("stpnm"),
            s.get("lat"),
            s.get("lon")]
        data.append(row_data)
    df = pd.DataFrame(data=data,columns=STOP_COLS.values())
    return df

def update_static_feed(force_update=False):
    """Retrieves updated zip file, extracts .txt files and saves to 'cta_google_transit' folder"""
    with requests.Session() as sesh:
        with open(os.path.abspath("./cta/cta_google_transit/updated.txt"),"r") as txtfile:
            last_time_downloaded = txtfile.read()

        feed_url = "https://www.transitchicago.com/downloads/sch_data/"
        feed_response = sesh.get(feed_url)
        feed_link = bs(feed_response.text,"lxml").find("a",attrs={"href":"/downloads/sch_data/google_transit.zip"})
        timestamp = feed_link.previousSibling.text.strip()
        last_idx = timestamp.find("M ") + 1
        timestamp = timestamp[:last_idx]

        if last_time_downloaded != timestamp or force_update is True:
            if last_time_downloaded == timestamp:
                print("Forcing redownload...")
            url = "https://www.transitchicago.com/downloads/sch_data/google_transit.zip"
            response = sesh.get(url,stream=True)
            z = zipfile.ZipFile(BytesIO(response.content))
            z.extractall(os.path.abspath("./cta/cta_google_transit/"))

            with open(os.path.abspath("./cta/cta_google_transit/updated.txt"),"w+") as txtfile:
                txtfile.write(timestamp)
        else:
            print("CTA static feed is already up to date")

def check_feed():
    """
    Fetches the CTA's GTFS transit feed directory to check the last time the feed was updated
    """
    url = "https://www.transitchicago.com/downloads/sch_data/"
    response = requests.get(url)
    soup = bs(response.text,"lxml")
    feed_link = soup.find("a",attrs={"href":"/downloads/sch_data/google_transit.zip"})
    recent_update_time = feed_link.previousSibling.text.strip()
    last_idx = recent_update_time.find("M ") + 1
    recent_update_time = recent_update_time[:last_idx]
    return recent_update_time

def last_feed_update():
    """Gets the last time the user updated the local machine's CTA GTFS transit directory"""
    with open(os.path.abspath("./cta/cta_google_transit/updated.txt"),"r") as txtfile:
        return txtfile.read()

def update_all():
    update_bus_routes()
    update_train_stations()
    update_route_transfers()
    update_static_feed(True)





