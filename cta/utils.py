import requests
import pandas as pd
import datetime as dt
from dateutil import tz
from tabulate import tabulate
from haversine import haversine

UTC_ZONE = tz.tzutc()
ET_ZONE = tz.gettz("America/New_York")
CT_ZONE = tz.gettz("America/Chicago")
MT_ZONE = tz.gettz("America/Phoenix")
PT_ZONE = tz.gettz("America/Los_Angeles")

STANDARD_FMT = r"%-I:%M %p"
MILITARY_FMT = r"%H:%M"
ISO_FMT = r"%Y-%m-%dT%H:%M:%SZ"
ISO_FMT_ALT = r"%Y-%m-%dT%H:%M:%S"
ISO_FMT_MS = r"%Y-%m-%dT%H:%M:%S.%fZ"


def tablify(df,tablefmt="simple",showindex=False):
    print(tabulate(df,headers="keys",showindex=showindex,tablefmt=tablefmt))

def prettify_time(t=dt.datetime.strftime(dt.datetime.utcnow(),ISO_FMT),outfmt="twelve",tzone="ct",input_tzone='ct') -> str:
    """Converts ISO Format to standard 12-Hour or 24-Hour format

    (ISO Format `2021-11-03T08:34:53Z`)

    Params:
    -------
    Accepted 'fmt' values:
    - `'twelve' ` \t\t -> 8:34 PM
    - `'military'` \t -> 16:34
    - `'iso'` \t\t -> 2021-11-03T16:34:53Z

    Accepted 'tz' values:
    - `'ct'` -> Central Time (Default)    
    - `'et'` -> Eastern Time
    - `'mt'` -> Mountain Time
    - `'pt'` -> Pacific Time
    - `'utc'` -> UTC Time
    """

    if input_tzone == "ct":
        input_tzone = CT_ZONE
    elif input_tzone == "et":
        input_tzone = ET_ZONE
    elif input_tzone == "mt":
        input_tzone = MT_ZONE
    elif input_tzone == "pt":
        input_tzone = PT_ZONE
    elif input_tzone == "utc":
        input_tzone = UTC_ZONE

    try:
        dt_obj = dt.datetime.strptime(t,ISO_FMT_ALT)
    except:
        try:
            dt_obj = dt.datetime.strptime(t,ISO_FMT)
        except:
            try:
                dt_obj = dt.datetime.strptime(t,ISO_FMT_MS)
            except:
                # print(f"couldn't convert - {t} - to date object")
                return ""
    
    utc_time_obj = dt_obj.replace(tzinfo=input_tzone) # tells the date object that tells function what timezone to read it as

    utc_time_obj = utc_time_obj
    utc_time_iso = dt.datetime.strftime(utc_time_obj,ISO_FMT)
    utc_time_12 = dt.datetime.strftime(utc_time_obj,STANDARD_FMT)
    utc_time_24 = dt.datetime.strftime(utc_time_obj,MILITARY_FMT)

    et_time_obj = utc_time_obj.astimezone(ET_ZONE)
    et_time_iso = dt.datetime.strftime(et_time_obj,ISO_FMT)
    et_time_12 = dt.datetime.strftime(et_time_obj,STANDARD_FMT)
    et_time_24 = dt.datetime.strftime(et_time_obj,MILITARY_FMT)

    ct_time_obj = utc_time_obj.astimezone(CT_ZONE)
    ct_time_iso = dt.datetime.strftime(ct_time_obj,ISO_FMT)
    ct_time_12 = dt.datetime.strftime(ct_time_obj,STANDARD_FMT)
    ct_time_24 = dt.datetime.strftime(ct_time_obj,MILITARY_FMT)

    mt_time_obj = utc_time_obj.astimezone(MT_ZONE)
    mt_time_iso = dt.datetime.strftime(mt_time_obj,ISO_FMT)
    mt_time_12 = dt.datetime.strftime(mt_time_obj,STANDARD_FMT)
    mt_time_24 = dt.datetime.strftime(mt_time_obj,MILITARY_FMT)

    pt_time_obj = utc_time_obj.astimezone(PT_ZONE)
    pt_time_iso = dt.datetime.strftime(pt_time_obj,ISO_FMT)
    pt_time_12 = dt.datetime.strftime(pt_time_obj,STANDARD_FMT)
    pt_time_24 = dt.datetime.strftime(pt_time_obj,MILITARY_FMT)

    if tzone == "et":
        if outfmt == "twelve":
            return et_time_12
        elif outfmt == "military":
            return et_time_24
        elif outfmt == "iso":
            return et_time_iso
    elif tzone == "ct":
        if outfmt == "twelve":
            return ct_time_12
        elif outfmt == "military":
            return ct_time_24
        elif outfmt == "iso":
            return ct_time_iso
    elif tzone == "mt":
        if outfmt == "twelve":
            return mt_time_12
        elif outfmt == "military":
            return mt_time_24
        elif outfmt == "iso":
            return mt_time_iso
    elif tzone == "pt":
        if outfmt == "twelve":
            return pt_time_12
        elif outfmt == "military":
            return pt_time_24
        elif outfmt == "iso":
            return pt_time_iso
    elif tzone == "utc":
        if outfmt == "twelve":
            return utc_time_12
        elif outfmt == "military":
            return utc_time_24
        elif outfmt == "iso":
            return utc_time_iso

def geolocate(query:str|int):
    q = str(query)
    GEO_BASE = "https://nominatim.openstreetmap.org/search?"
    params = {
        "format":"json",
        "limit":"1"
    }
    if q.isdigit():
        params["postalcode"] = q
    else:
        params["q"] = q
    response = requests.get(GEO_BASE,params=params)
    place = response.json()[0]
    lat = place["lat"]
    lon = place["lon"]
    coords = pd.Series(data={"lat":lat,"lon":lon})
    return coords

def get_distance(x1,y1,x2,y2,unit='ft'):
    """
    Get the distance between two geographical points on the planet

    Params:
    ------
    - x1: latitudinal value of the first point (Required)
    - y1: longitudinal value of the first point (Required)
    - x2: latitudinal value of the second point (Required)
    - y2: longitudinal value of the second point (Required)
    - unit: the unit of measurement that the calculate value will be in (Default = 'ft')
    """
    x1 = round(float(x1),15)
    y1 = round(float(y1),15)
    x2 = round(float(x2),15)
    y2 = round(float(y2),15)
    point1 = (x1,y1)
    point2 = (x2,y2)
    dist = haversine(point1,point2,unit=unit)
    return dist

def locate(**kwargs):
    """
    Get location info by query, latitude/longitude, address details and other keyword arguments

    Keyword Args by Search Type:
    -------------
    - Simple Query (CONDITIONALLY REQUIRED)
        - 'query' | 'q'

    - Coordinates (CONDITIONALLY REQUIRED)
        - 'latitude' | 'lat'
        - 'longitude' | 'lon'

    - Address Details (CONDITIONALLY REQUIRED)
        - 'street' | 'address' | 'addr' |'a'
        - 'city' | 'c' | 'town' | 't'
        - 'statecode' | 'state' | 'st' | 's'
        - 'countrycode' | 'country' | 'cc'
            - default = "us"
        - 'zipcode' | 'zip' | 'postalcode' | 'zc' | 'pc'

    - Other (OPTIONAL)
        - 'limit' (the amount of results to display)
            - default = 1
    """
    params = {
        "format":"jsonv2",
        "limit":1,
        "country":"us",
        "addressdetails":1}
    areCoords = False
    if "lat" in kwargs.keys():
        params["lat"] = kwargs["lat"]
        areCoords = True
    elif "latitude" in kwargs.keys():
        params["lat"] = kwargs["latitude"]
        areCoords = True
    if "lon" in kwargs.keys():
        params["lon"] = kwargs["lon"]
        areCoords = True
    elif "longitude" in kwargs.keys():
        params["lat"] = kwargs["longitude"]
        areCoords = True
    
    if areCoords is True:
        response = requests.get("https://nominatim.openstreetmap.org/reverse.php?",params=params)
        return response.json()
    
    for key,val in kwargs.items():
        if key.lower() in ("zip","zipcode","postalcode","zc","pc"):
            params["postalcode"] = val
        elif key.lower() in ('statecode','state','st','s'):
            params["state"] = val
        elif key.lower() in ('countrycode','country','cc'):
            params["country"] = val
        elif key.lower() == 'county':
            params["county"] = val
        elif key.lower() == "max":
            params["limit"] = val
        elif key.lower() == "q":
            params["q"] = val
        elif key.lower() == "query":
            params["q"] = val
        elif key.lower() in ("city","town","c","t"):
            params["city"] = val
        elif key.lower() in ("address","addr","street","a"):
            params["street"] = val
        else:
            print(f"{key} is not a valid argument")

    response = requests.get("https://nominatim.openstreetmap.org/search?",params=params)
    return response.json()

def get_coordinates(query) -> tuple:
    """
    Returns a tuple of geo coordinates based on the 'query'
    """
    resp = locate(q=query)
    lat = resp[0]["lat"]
    lon = resp[0]["lon"]
    return (lat,lon)

def time_since_midnight(time_str:str):
    """
    Pass in time string (format: HH:MM:SS) and returns the time since midnight (in seconds)
    """

    ts = time_str
    h = int(ts[:2])
    into_next_day = False
    if h > 23:
        into_next_day = True
        h = h - 24
    m = int(ts[3:5])
    s = int(ts[-2:])
    if into_next_day is False:
        full_day_diff = dt.timedelta(seconds=86400)
        tm_obj = dt.time(hour=h,minute=m,second=s)
        dt_obj = dt.datetime(1,1,1,hour=h,minute=m,second=s)
    else:
        full_day_diff = dt.timedelta(seconds=86400)
        tm_obj = dt.time(hour=h,minute=m,second=s)
        dt_obj = dt.datetime(1,1,1,hour=h,minute=m,second=s)







