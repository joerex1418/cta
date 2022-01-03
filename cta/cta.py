import lxml
import html5lib
import requests
import pandas as pd
from pprint import pformat, pprint
from unicodedata import normalize
from bs4 import BeautifulSoup as bs

from .constants import *

from .utils import locate
from .utils import get_coordinates
from .utils import geolocate
from .utils import prettify_time
from .utils import get_distance
from .utils import ISO_FMT_ALT

from .utils_cta import *


# ====================================================================================================
# CTA Bus Objects 
# ====================================================================================================
class BusRoute:
    """
    # Bus Route
    Represents a bus service going in a single direction

    Required Attributes
    -------------------
    - 'route': alphanumeric bus number
    - 'direction': the general direction of travel ("Northboud nd","Southbound","Westbound","Eastbound")
        - Shorthand allowed - > 'n'/'north', 'e'/'east', 's'/'south', 'w'/'west'
    """
    def __init__(self,route,direction):
        self.__route = str(route)
        self.__direction = filter_direction(direction)
        self.__stops = self.__get_stops()
        
        self.__get_patterns()
        self.__update_vehicle_locations()
    
    def __repr__(self) -> str:
        return f"""<cta.Bus object | Route: {self.__route} ({self.__direction})>"""

    def route(self):
        return self.__route
    
    def direction(self):
        return self.__direction

    def stops(self) -> pd.DataFrame:
        """
        Returns dataframe of stops serviced by the Bus
        """
        return self.__stops
    
    def stops_by_distance(self,latitude,longitude,limit=1) -> pd.DataFrame:
        """
        Return the 'stops' dataframe, sorted by distance to given latitude & longitude

        Params:
        -------
        - latitude (required)
        - longitude (required)
        """
        return self.__sort_by_shortest_distance(latitude,longitude,self.__stops).head(limit).reset_index(drop=True)


    def vehicles(self,vid=None,update_on_call=True,update=None) -> pd.DataFrame:
        """
        Returns dataframe of the geolocations for each vehicle along the route

        Params
        ------
        - 'vid': a single vehicle's ID or a comma-delimited list of multiple vehicle IDs
            - Parameter is optional. By default, the method will return data on all busses for this route 
            - Single API call does not update the entire dataset of the parent objects vehicle data
        - 'update_on_call': Default, TRUE. If set to FALSE, method will return previously retrieved data

        """
        if update is not None:
            update_on_call = update
        if vid is None:
            if update_on_call is True:
                self.__update_vehicle_locations()
            else:
                pass
            df = self.__vehicles
            return df
        else:
            return self.__update_vehicle_locations(vid)

    def predictions(self,stpid=None,vid=None,top=None,sort_by=None) -> pd.DataFrame:
        """
        Predicted arrival/departure data for the Bus (by 'stpid' or 'vid')

        REQUIRED: ONE of the following -> 'stpid' or 'vid'
        NOTE: Cannot be used together. If both params are propagated, the method will prioritize 'stpid'

        - `stpid`: Comma-delimited list of stop IDs whose predictions are to be returned
        NOTE: Maximum of 10 identifiers can be specified

        - `vid`: Comma-delimited list of vehicle IDs whose predictions should be returned
        NOTE: Maximum of 10 identifiers can be specified

        - `top`: Maximum number of predictions to be returned

        - `sort_by`: column that will be used to sort the dataframe entries
        """
        if stpid is not None:
            if str(stpid) not in list(self.__stops.stop_id):
                print(f"Stop # {stpid} is not on this route")
                return None
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_BUS_API_KEY
        else:
            key = ALT_BUS_API_KEY
        params = {
            "key":key,
            "rt":self.__route,
            "format":"json"}
        if stpid is not None:
            params["stpid"] = stpid
        elif vid is not None:
            params["vid"] = vid
        else:
            print("must use either stpid or vid param")
            return None
        if top is not None:
            params["top"] = top

        url = CTA_BUS_BASE + f"/getpredictions?"

        response = requests.get(url,params=params)
        data = []
        for p in response.json()["bustime-response"]["prd"]:
            row_data = []
            for col in PREDICTION_COLS:
                if col == "prdctdn":
                    prediction_val = f'{p.get(col,"-")} mins' if p.get(col,"-") != "DUE" else "Due"
                    row_data.append(prediction_val)
                elif col != "tmstmp":
                    row_data.append(p.get(col,"-"))
                else:
                    ### MIGHT NEED TO FIX SOON
                    try:row_data.append(prettify_time(p.get(col,"-")))
                    except:row_data.append(p.get(col,"-"))
            data.append(row_data)
        
        df = pd.DataFrame(data=data,columns=PREDICTION_COLS.values())
        if sort_by is None:
            pass
        elif sort_by == "vehicle" or sort_by == "vid":
            df.sort_values(by="vid",ascending=True,inplace=True)
        elif sort_by == "stpid" or sort_by == "stop_id":
            df.sort_values(by="stpid",ascending=True,inplace=True)
        elif sort_by == "stpnm" or sort_by == "stop_name" or sort_by == "stop":
            df.sort_values(by="stop",ascending=True,inplace=True)

        return df

    def patterns(self) -> list:
        """
        **NOT CONFIGURED YET\n
        Returns an array of python dictionary for the Bus route points which, when mapped, can construct the geo-positional layout of a 'route variation'
        """
        return self.__pids

    def __sort_by_shortest_distance(self,curr_lat,curr_lon,stop_df):
        stop_df_records = stop_df.to_dict("records")
        distances = []
        for coords in stop_df_records:
            distances.append(get_distance(curr_lat,curr_lon,coords["lat"],coords["lon"]))
        stop_df["dist"] = distances
        return stop_df.sort_values(by="dist",ascending=True)

    def __get_patterns(self):
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_BUS_API_KEY
        else:
            key = ALT_BUS_API_KEY
        params = {
            "key":key,
            "rt":self.__route,
            "format":"json"
        }
        url = CTA_BUS_BASE + f"/getpatterns?"
        response = requests.get(url,params=params)
        resp = response.json()["bustime-response"]
        patterns = resp["ptr"]
        pids = []
        for ptr in patterns:
            if ptr["rtdir"] == self.__direction:
                pids.append(ptr["pid"])
        self.__pids = pids

        return patterns

    def __get_stops(self):
        df = get_bus_route_stops(self.__route,self.__direction)
        return df

    def __update_vehicle_locations(self,vid=None):
        params = {
            "key":CTA_BUS_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_BUS_API_KEY,
            "format":"json"
        }
        if vid is None:
            params["rt"] = self.__route
        else:
            params["vid"] = str(vid).replace(" ","")
        url = CTA_BUS_BASE + "/getvehicles"
        response = requests.get(url,params=params)
        data = []
        for v in response.json()["bustime-response"]["vehicle"]:
            row_data = [
                v.get("vid","-"),
                v.get("tmstmp","-"),
                v.get("lat","-"),
                v.get("lon","-"),
                v.get("hdg","-"),
                v.get("pid","-"),
                v.get("rt","-"),
                v.get("des","-"),
                v.get("pdist","-"),
                v.get("dly",None),
                v.get("tatripid","-"),
                v.get("tablockid","-")]
            
            data.append(row_data)
        df = pd.DataFrame(data=data,columns=VEHICLE_COLS.values())
        df = df[df["pattern_id"].isin(self.__pids)]
        
        if vid is not None:
            return df
        else:
            self.__vehicles = df


    # ALIASES ---------------------
    locations = positions = vehicles
    arrivals = predictions
    # -----------------------------

class BusStop:
    """
    # BusStop

    A single bus stop or a "group" of bus stops

    NOTE: Use cta.stop_search() to search for stop IDs by stop name

    Positional Arguments (by search method):
    ----------------------------------------
    - By STOP ID:
        1. stop_id: a single stop ID or comma-delimited list of stop IDs ("1863,1915"); MAX 10
    - By ROUTE (gets closest stops)
        1. route: a single route that services the stops closest to the specified location
        2. direction: direction of the route service
        3. location: coordinates (type tuple or list) or search query (type str)
            - would recommend using coordinates. If entering an search query, use a specific address. Otherwise you will 
            probably not get accurate results
        - 'limit' (optional): Limit the number of stops queried; Default is 2
            - Example: `limit=4` will yield the 4 closest stops to a specified locaton

    """
    def __init__(self,*args,limit=2):
        if len(args) == 1:
            self.__stop_id = str(args[0]).replace(" ","")
            self.__route = None
        else:
            if len(args) != 3:
                print("Second argument, address query (type str) or coordinates (type tuple or list) is required ")
                return None
            rt = args[0]
            direction = filter_direction(args[1])
            loc = args[2]
            stops_df = self.__get_stops(rt,direction)
            if type(loc) is str:
                coords = get_coordinates(query=loc)
            elif type(loc) is list or type(loc) is tuple:
                coords = loc
            lat = str(coords[0])
            lon = str(coords[1])
            self.__route = rt
            close_stops_df = self.__sort_by_shortest_distance(lat,lon,stops_df).head(limit)
            self.__stop_id = ",".join(list(close_stops_df["stop_id"]))
    
    def predictions(self,rt=None):
        """
        Get predictited arrival data for buses coming to this stop

        Params:
        -------
        - 'rt': a single route ID or comma-delimited list of route IDs (optional)
        """
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_BUS_API_KEY
        else:
            key = ALT_BUS_API_KEY
        params = {
            "key":key,
            "stpid":self.__stop_id,
            "format":"json"}
        if rt is not None:
            params["rt"] = rt

        url = CTA_BUS_BASE + "/getpredictions?"
        response = requests.get(url,params=params)
        data = []
        for p in response.json()["bustime-response"]["prd"]:
            row_data = []
            for col in PREDICTION_COLS.keys():
                if col != "tmstmp":
                    if col == "prdctdn":
                        rem = p.get(col)
                        row_data.append(f"{rem} mins" if rem!="DUE" else f"1 min")
                    elif col == "typ":
                        row_data.append(PRD_TYPES[p.get(col)])
                    else:
                        row_data.append(p.get(col))
                else:
                    row_data.append(p.get(col))
            data.append(row_data)
        
        df = pd.DataFrame(data=data,columns=PREDICTION_COLS.values()).sort_values(by=["stop_id","time_rem"],ascending=[True,True]).reset_index(drop=True)
        return df
    
    def __get_stops(self,rt,direction):
        df = get_bus_route_stops(rt,direction)
        return df

    def __sort_by_shortest_distance(self,curr_lat,curr_lon,stop_df):
        stop_df_records = stop_df.to_dict("records")
        distances = []
        for coords in stop_df_records:
            distances.append(get_distance(curr_lat,curr_lon,coords["lat"],coords["lon"]))
        stop_df["dist"] = distances
        return stop_df.sort_values(by="dist",ascending=True)

    # ALIASES ---------------------
    # -----------------------------

class Bus:
    def __init__(self,vid):
        self.__vid = vid
        self.__get_vehicles()
        self.__get_predictions()

    def vehicle(self,update_on_call=True):
        if update_on_call is True:
            self.__get_vehicles()
        return self.__vehicle

    def predictions(self,update_on_call=True):
        if update_on_call is True:
            self.__get_predictions()
        df = self.__predictions
        return df
    
    def patterns(self):
        lst = self.__pattern
        return lst

    def __get_vehicles(self):
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_BUS_API_KEY
        else:
            key = ALT_BUS_API_KEY
        
        params = {
            "key":key,
            "vid":self.__vid,
            "format":"json"}
        
        url = CTA_BUS_BASE + "/getvehicles?"
        response = requests.get(url,params=params)
        print(response.url)
        data = []
        for v in response.json()["bustime-response"]["vehicle"]:
            self.__pid = v.get("pid")
            row_data = [
                v.get("vid","-"),
                v.get("tmstmp","-"),
                v.get("lat","-"),
                v.get("lon","-"),
                v.get("hdg","-"),
                v.get("pid","-"),
                v.get("rt","-"),
                v.get("des","-"),
                v.get("pdist","-"),
                v.get("dly",None),
                v.get("tatripid","-"),
                v.get("tablockid","-")]
            
            data.append(row_data)
        df = pd.DataFrame(data=data,columns=VEHICLE_COLS.values())
        # df = df[df["pattern_id"].isin(self.__pids)]
        
        self.__vehicle = df

    def __get_predictions(self):
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_BUS_API_KEY
        else:
            key = ALT_BUS_API_KEY
        params = {
            "key":key,
            "vid":self.__vid,
            "format":"json"}

        url = CTA_BUS_BASE + f"/getpredictions?"

        response = requests.get(url,params=params)
        data = []
        for p in response.json()["bustime-response"]["prd"]:
            row_data = []
            for col in PREDICTION_COLS:
                if col != "tmstmp":
                    row_data.append(p.get(col,"-"))
                else:
                    ### NEED TO FIX THIS IN UTILS
                    try:row_data.append(prettify_time(p.get(col,"-")))
                    except:row_data.append(p.get(col,"-"))
            data.append(row_data)
        
        df = pd.DataFrame(data=data,columns=PREDICTION_COLS.values())
        df.sort_values(by=["predicted_time","stop"],ascending=[True,True],inplace=True)
        self.__predictions = df

    def __get_pattern(self):
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_BUS_API_KEY
        else:
            key = ALT_BUS_API_KEY
        params = {
            "key":key,
            "pid":self.__pid,
            "format":"json"}

        url = CTA_BUS_BASE + "/getpatterns?"
        response = requests.get(url,params=params)
        ptrn_sequences = []
        pattern_idx = response.json()["bustime-response"]["ptr"][0]
        self.__direction = pattern_idx["rtdir"]
        for pt in pattern_idx["pt"]:
            ptrn_sequences.append(pt)
        self.__pattern = ptrn_sequences

    # ALIASES ------------------------------
    vehicles = location = locations = position = positions = vehicle
    # --------------------------------------

# ====================================================================================================
# CTA Train Objects
# ====================================================================================================
class TrainRoute:
    """
    Represents an instance of an "L" line (specified by the 'line' attribute)
    """
    def __init__(self,line):
        self.line = line.lower()
        self.line_ref = LINES[self.line]
        self.line_label = LINE_LABELS[self.line_ref]
        self.line_name = LINE_NAMES[self.line_ref]
        self.line_color = LINE_COLORS[self.line_ref]
        self.rt = self.line_ref
        self.__filter_col = FILTER_COL[self.line_ref]
        self.__filter_stations_df_by_line()
        if self.__filter_col == "purple" or self.__filter_col == "purple_exp":
            self.__cols_for_stations_df = ["stop_id","stop_name","map_id","station_name","station_descriptive_name","direction_id","purple","purple_exp","lat","lon"]
        else:
            self.__cols_for_stations_df = ["stop_id","stop_name","map_id","station_name","station_descriptive_name","direction_id",self.__filter_col,"lat","lon"]

    def __repr__(self) -> str:
        return f"""<cta.TrainRoute object | {self.line_name}>"""

    def stations(self,hide_desc_col=True,hide_other_lines=True):
        """
        Returns dataframe of all the stations that the Line services
        
        (Utilizes the same data as the module's `train_stations()` function)
        """
        df = self.__stations
        if hide_other_lines is False:
            df = df
        else:
            df = df[self.__cols_for_stations_df]
        
        if hide_desc_col is False:
            return df.reset_index(drop=True)
        else:
            return df.drop(columns="station_descriptive_name").reset_index(drop=True)
    
    def arrivals(self,stpid_or_mapid=None,hide_desc_col=True):
        """
        Returns dataframe estimated arrival times & locations (given a station/stop) for vehicles serviced by the Line.\n
        (Method will auto detect if the entered param value is a stop id or a station id)
        
        Required Param:
        ---------------
        - `stp_or_map_id`: Valid 'stpid' or 'mapid'
        """
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_TRAIN_API_KEY
        else:
            key = ALT_TRAIN_API_KEY
        params = {
            "key":key,
            "rt":self.line_ref,
            "outputType":"JSON"}
        if str(stpid_or_mapid)[0] == "3":
            params["stpid"] = stpid_or_mapid
        elif str(stpid_or_mapid)[0] == "4":
            params["mapid"] = stpid_or_mapid
        else:
            print("Error: Ensure that you have entered a valid 'stpid' or 'mapid'")
            return None

        url = f"{CTA_TRAIN_BASE}/ttarrivals.aspx?"
        response = requests.get(url,params=params)

        ctatt = response.json()["ctatt"]
        timestamp = ctatt.get("tmst")
        timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
        arrvs = ctatt["eta"]
        data = []
        for a in arrvs:
            prdt = a.get("prdt")
            prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
            arrT = a.get("arrT")
            arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
            due_in = int((arrT_obj - prdt_obj).seconds / 60)
            due_in = 'Due' if due_in == 1 else f'{due_in} mins'
            time_since_update = timestamp_obj - prdt_obj
            time_since_update = f'{time_since_update.seconds} seconds ago'

            # Col-value definitions:
            stop_id = a.get("stpId")
            stop_name = self.__get_stop_name(stop_id)
            map_id = a.get("staId")
            station_name = a.get("staNm")
            station_desc = a.get("stpDe")
            run_num = a.get("rn")
            rt = a.get("rt")
            dest_stop = a.get("destSt")
            dest_name = a.get("destNm")
            trDr = a.get("trDr")
            data.append([
                stop_id,
                stop_name,
                map_id,
                station_name,
                station_desc,
                run_num,
                rt,
                dest_stop,
                dest_name,
                trDr,
                prettify_time(prdt),
                prettify_time(arrT),
                arrT,
                due_in,
                time_since_update,
                a.get("isApp"),
                a.get("isSch"),
                a.get("isDly"),
                a.get("isFlt"),
                a.get("flags"),
                a.get("lat"),
                a.get("lon"),
                a.get("heading")])
        df = pd.DataFrame(data=data,columns=L_ARRIVALS_COLS)
        if hide_desc_col is True:
            return df.drop(columns=["station_desc"])
        return df

    def locations(self):
        """
        Gets the current position of every vehicle for this Line
        """
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_TRAIN_API_KEY
        else:
            key = ALT_TRAIN_API_KEY
        params = {
        "key":key,
        "rt":self.line_ref,
        "outputType":"JSON"}
        url = f"{CTA_TRAIN_BASE}/ttpositions.aspx?"
        response = requests.get(url,params=params)
        ctatt = response.json()["ctatt"]
        timestamp = ctatt.get("tmst")
        timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
        data = []
        for r in ctatt["route"]:
            line = FILTER_COL[r.get("@name")]
            train_arrivals = r.get("train")
            for t in train_arrivals:
                prdt = t.get("prdt")
                prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
                arrT = t.get("arrT")
                arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
                due_in = int((arrT_obj - prdt_obj).seconds / 60)
                due_in = 'Due' if due_in == 1 else f'{due_in} mins'
                time_since_update = timestamp_obj - prdt_obj
                time_since_update = f'{time_since_update.seconds} seconds ago'
                
                run_num = t.get("rn")
                dest_stop_id = t.get("destSt")
                service_name = t.get("destNm")
                next_map_id = t.get("nextStaId")
                next_station_name = t.get("nextStaNm")
                next_stop_id = t.get("nextStpId")
                trDr = t.get("trDr")
                data.append([
                    line,
                    run_num,
                    dest_stop_id,
                    service_name,
                    next_map_id,
                    next_station_name,
                    next_stop_id,
                    trDr,
                    prettify_time(prdt),
                    prettify_time(arrT),
                    due_in,
                    time_since_update,
                    t.get("isApp"),
                    t.get("isDly"),
                    t.get("flags"),
                    t.get("lat"),
                    t.get("lon"),
                    t.get("heading")])
        df = pd.DataFrame(data=data,columns=L_POSITIONS_COLS)
        return df

    def follow(self,rn,hide_desc_col=True):
        """
        Returns a dataframe of a line's arrival/location data for a specific run_number (rn)
        
        Params:
        -------
        - `rn`: the run number to retrieve data for
        """
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_TRAIN_API_KEY
        else:
            key = ALT_TRAIN_API_KEY
        params = {
        "key":key,
        "runnumber":rn,
        "outputType":"JSON"}

        url = CTA_TRAIN_BASE + "/ttfollow.aspx?"
        response = requests.get(url,params=params)
        ctatt = response.json()["ctatt"]
        timestamp = ctatt.get("tmst")
        timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
        position = ctatt["position"]
        lat = position["lat"]
        lon = position["lon"]
        heading = position["heading"]
        data = []
        for e in ctatt["eta"]:
            stpId = e.get("stpId")
            coords = self.__get_stop_coords(stpId)
            stpLat = coords[0]
            stpLon = coords[1]
            prdt = e.get("prdt")
            prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
            arrT = e.get("arrT")
            arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
            due_in = int((arrT_obj - prdt_obj).seconds / 60)
            due_in = 'Due' if due_in == 1 else f'{due_in} mins'
            time_since_update = timestamp_obj - prdt_obj
            time_since_update = f'{time_since_update.seconds} seconds ago'
            data.append([
                stpId,
                stpLat,
                stpLon,
                e.get("staId"),
                e.get("staNm"),
                e.get("stpDe"),
                e.get("destNm"),
                e.get("rn"),
                e.get("rt"),
                e.get("destSt"),
                e.get("trDr"),
                prettify_time(prdt),
                prettify_time(arrT),
                due_in,
                time_since_update,
                e.get("isApp"),
                e.get("isSch"),
                e.get("isDly"),
                e.get("isFlt"),
                e.get("flags"),
                lat,
                lon,
                heading])
        df = pd.DataFrame(data=data,columns=L_FOLLOW_COLS)
        if hide_desc_col is True:
            return df.drop(columns=["service_desc"])
        return df

    def __filter_stations_df_by_line(self):
        df = get_train_stations()
        df.astype({"map_id":"str"})
        df = df[df[self.__filter_col] == True]
        self.__stations = df

    def __get_stop_coords(self,stpid):
        df = self.__stations
        station_row = df[df["stop_id"]==stpid].iloc[0]
        return (str(station_row.lat.item()),str(station_row.lon.item()))

    def __get_stop_name(self,stpid):
        df = self.__stations
        station_row = df[df["stop_id"]==str(stpid)]
        return station_row.stop_name.item()
    
    
    # ALIASES ---------------------
    positions = vehicles = trains = locations
    stops = stations
    # -----------------------------

class TrainStation:
    """
    # TrainStation

    Represents an instance of an "L" parent station specified by corresponding station ID or (map ID) or stop ID
    
    NOTE: Use cta.stop_search() to search for stop IDs by stop name

    Positional Arguments (by search method):
    ----------------------------------------
    - By STATION ID:
        1. station_id: a single stop ID or comma-delimited list of stop IDs; MAX 10
    - By ROUTE (gets closest stops)
        1. route: a single route/line that services the closest station
        2. location: coordinates (type tuple or list) or search query (type str)
            - would recommend using coordinates. If entering an search query, use a specific address. Otherwise you will 
            probably not get accurate results
    """
    def __init__(self,*args):
        isParent = False
        if len(args) == 1:
            station_id = str(args[0])
            main_df = get_train_stations()
            if station_id[0] == "3":          # station is a specific platform
                df = main_df[main_df.stop_id==station_id]
                self.__map_id = df.map_id.item()
                # print("ID IS FOR STOP PLATFORM")
                # print(self.__map_id)
                self.__station_id = station_id
            elif station_id[0] == "4":        # station is a parent station
                isParent = True      
                df = main_df[main_df.map_id==station_id]
                self.__map_id = station_id
                # print("ID IS FOR PARENT")
                # print(self.__map_id)
                self.__station_id = station_id

        else:
            if len(args) != 2:
                print("Exactly TWO positional arguments required when searching for closest stops by route - 'route', 'location'")
                print("Second argument, address query (type str) or coordinates (type tuple or list) is required")
                return None
            else:
                main_df = get_train_stations()
                rt = args[0].lower()
                rt_stops_df = main_df[main_df[rt]==True]
                loc = args[1]
                # stops_df = self.__get_stops(rt,direction)
                if type(loc) is str:
                    coords = get_coordinates(query=loc)
                elif type(loc) is list or type(loc) is tuple:
                    coords = loc
                lat = str(coords[0])
                lon = str(coords[1])
                close_stops_df = self.__sort_by_shortest_distance(lat,lon,rt_stops_df).head(1)
                station_id = close_stops_df["map_id"].item()

                if str(station_id)[0] == "3":          # station is a specific platform
                    df = main_df[main_df.stop_id==str(station_id)]
                    self.__map_id = station_id
                    self.__station_id = station_id
                elif str(station_id)[0] == "4":        # station is a parent station
                    isParent = True      
                    df = main_df[main_df.map_id==str(station_id)]
                    self.__map_id = station_id
                    self.__station_id = station_id

        if isParent is True:
            self.__station_df = main_df[main_df.map_id==str(self.__station_id)]
        else:
            self.__map_id = main_df[main_df.stop_id==str(self.__station_id)].iloc[0].map_id
            self.__station_df = main_df[main_df.map_id==str(self.__map_id)]
        
        df = self.__station_df

        routes = {}
        line_list = []
        for c in COLOR_LABEL_LIST:
            if True in list(df[c]):
                line_list.append(c)
                routes[c] = {
                    "line":LINE_NAMES[LINES[c]],
                    "label":LINE_LABELS[LINES[c]],
                    "code":LINES[c]}
        
        self.__station_name = df.iloc[0].station_name
        self.__description = df.iloc[0].station_descriptive_name
        self.__lat = df.iloc[0].lat
        self.__lon = df.iloc[0].lon
        self.__routes = routes
        self.__line_list = line_list
    
    def __repr__(self):
        return f"<cta.TrainStation Name: {self.__station_name} | ID: {self.__map_id}>"

    def station(self):
        station_dict = {
            "station_name":self.__station_name,
            "description":self.__description,
            "station_id":self.__station_id,
            "lat":self.__lat,
            "lon":self.__lon
        }
        return pd.Series(station_dict)
    
    def stops(self):
        """
        Get dataframe of the parent station's separate stops/platforms (going separate directions)
        """
        df = self.__station_df
        return df[["stop_id","stop_name","station_name","direction_id","map_id","ada"]+self.__line_list]

    def routes(self):
        """
        Show all possible routes that are serviced by the station
        """
        return self.__routes

    def arrivals(self,rt=None,max=None,route=None,line=None,limit=None,top=None,hide_desc_col=True):
        """
        Returns dataframe of estimated arrival times & locations for the station
        
        Params:
        -------
        - 'rt': can be used to specify a single route that comes through the station
            - 'route':ALIAS for 'rt'
            - 'line': ALIAS for 'rt'
        - 'max': limits the amount of results shown
            - 'limit':ALIAS for 'max'
            - 'top':ALIAS for 'max'

        Method ALIAS: 'predictions'
        """
        if route is not None:
            rt = route
        if line is not None:
            rt = line
        if top is not None:
            max = top
        if limit is not None:
            max = limit
        params = {
            "key":CTA_TRAIN_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_TRAIN_API_KEY,
            "mapid":self.__map_id,
            "outputType":"JSON"}
        if rt is not None:
            params["rt"] = rt
        if max is not None:
            params["max"] = max

        url = CTA_TRAIN_BASE + "/ttarrivals.aspx?"
        response = requests.get(url,params=params)

        ctatt = response.json()["ctatt"]
        timestamp = ctatt.get("tmst")
        timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
        arrvs = ctatt["eta"]
        data = []
        for a in arrvs:
            prdt = a.get("prdt")
            prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
            arrT = a.get("arrT")
            arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
            due_in = int((arrT_obj - prdt_obj).seconds / 60)
            due_in = 'Due' if due_in == 1 else f'{due_in} mins'
            time_since_update = timestamp_obj - prdt_obj
            time_since_update = f'{time_since_update.seconds} seconds ago'

            # Col-value definitions:
            stop_id = a.get("stpId")
            stop_name = self.__get_stop_name(stop_id)
            map_id = a.get("staId")
            station_name = a.get("staNm")
            station_desc = a.get("stpDe")
            run_num = a.get("rn")
            rt = FILTER_COL[a.get("rt")]
            dest_stop = a.get("destSt")
            dest_name = a.get("destNm")
            trDr = a.get("trDr")
            data.append([
                stop_id,
                stop_name,
                map_id,
                station_name,
                station_desc,
                run_num,
                rt,
                dest_stop,
                dest_name,
                trDr,
                prettify_time(prdt),
                prettify_time(arrT),
                arrT,
                due_in,
                time_since_update,
                a.get("isApp"),
                a.get("isSch"),
                a.get("isDly"),
                a.get("isFlt"),
                a.get("flags"),
                a.get("lat"),
                a.get("lon"),
                a.get("heading")])
        df = pd.DataFrame(data=data,columns=L_ARRIVALS_COLS)
        if hide_desc_col is True:
            return df.drop(columns=["station_desc"])
        return df

    def __get_stop_name(self,stpid):
        df = self.__station_df
        station_row = df[df["stop_id"]==str(stpid)]
        return station_row.stop_name.item()

    def __sort_by_shortest_distance(self,curr_lat,curr_lon,stop_df:pd.DataFrame):
        stop_df_records = stop_df.to_dict("records")
        distances = []
        for coords in stop_df_records:
            distances.append(get_distance(curr_lat,curr_lon,coords["lat"],coords["lon"]))
        # stop_df["dist"] = distances
        stop_df.insert(0,"dist",distances)
        return stop_df.sort_values(by="dist",ascending=True)
    
    # Aliases ---------------------------------
    predictions = arrivals
    # -----------------------------------------

class Train:
    def __init__(self,rn):
        self.__rn = rn
        self.__stations = get_train_stations()
        self.__follow()
    
    def __repr__(self):
        return f"<cta.Train {self.__line_rt} | {self.__service_name} | {self.__rn}>"
    
    def follow(self,hide_desc_col=True):
        return self.__follow(hide_desc_col)

    def __follow(self,hide_desc_col=True):
        params = {
            "key":CTA_TRAIN_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_TRAIN_API_KEY,
            "runnumber":self.__rn,
            "outputType":"JSON"}

        url = CTA_TRAIN_BASE + "/ttfollow.aspx?"
        response = requests.get(url,params=params)
        ctatt = response.json()["ctatt"]
        timestamp = ctatt.get("tmst")
        timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
        position = ctatt["position"]
        lat = position["lat"]
        lon = position["lon"]
        heading = position["heading"]
        data = []
        self.__service_name = ctatt["eta"][0].get("destNm")
        self.__line_rt = ctatt["eta"][0].get("rt")
        for e in ctatt["eta"]:
            stpId = e.get("stpId")
            coords = self.__get_stop_coords(stpId)
            stpLat = coords[0]
            stpLon = coords[1]
            prdt = e.get("prdt")
            prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
            arrT = e.get("arrT")
            arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
            due_in = int((arrT_obj - prdt_obj).seconds / 60)
            due_in = 'Due' if due_in == 1 else f'{due_in} mins'
            time_since_update = timestamp_obj - prdt_obj
            time_since_update = f'{time_since_update.seconds} seconds ago'


            data.append([
                stpId,
                stpLat,
                stpLon,
                e.get("staId"),
                e.get("staNm"),
                e.get("stpDe"),
                e.get("destNm"),
                e.get("rn"),
                e.get("rt"),
                e.get("destSt"),
                e.get("trDr"),
                prettify_time(prdt),
                prettify_time(arrT),
                due_in,
                time_since_update,
                e.get("isApp"),
                e.get("isSch"),
                e.get("isDly"),
                e.get("isFlt"),
                e.get("flags"),
                lat,
                lon,
                heading])
        df = pd.DataFrame(data=data,columns=L_FOLLOW_COLS)
        if hide_desc_col is True:
            return df.drop(columns=["service_desc"])
        return df
    
    def __get_stop_coords(self,stpid):
        df = self.__stations
        station_row = df[df["stop_id"]==stpid].iloc[0]
        return (str(station_row.lat.item()),str(station_row.lon.item()))

# ====================================================================================================
# API Wrappers
# ====================================================================================================
class StaticFeed:
    """
    # CTA GTFS Static Feed

    Interface with the CTA static feed to display information from the local machine's GTFS txt files

    - Run 'cta.update_static_feed()' to download .txt files to local storage

    """
    def __init__(self) -> None:
        pass

    def stops(self) -> pd.DataFrame:
        """
        Returns dataframe of GTFS `stops.txt` file

        NOTE: Not 'real-time' data; intended for reference purposes
        """
        df = get_stops().fillna("")
        # replacing NaN values with "-"
        df.fillna("-",inplace=True)
        # rearranging column order for better readability
        columns = ['stop_id','stop_code','map_id','stop_name','stop_desc','stop_lat','stop_lon','location_type','wheelchair_boarding']
        df = df[columns]
        route_dirs = []
        for desc in df.stop_desc:
            if "northbound" in desc.lower():
                route_dirs.append("N")
            elif "southbound" in desc.lower():
                route_dirs.append("S")
            elif "westbound" in desc.lower():
                route_dirs.append("W")
            elif "eastbound" in desc.lower():
                route_dirs.append("E")
            else:
                route_dirs.append("-")

        df.insert(4,"rtdir",route_dirs)
        return df

    def routes(self) -> pd.DataFrame:
        return get_routes()

    def shapes(self) -> pd.DataFrame:
        return get_shapes()

    def trips(self) -> pd.DataFrame:
        """
        Returns dataframe of GTFS `trips.txt` file

        NOTE: Not 'real-time' data; intended for reference purposes
        """
        df = get_trips()
        return df

    def calendar(self) -> pd.DataFrame:
        """
        Returns dataframe of GTFS `calendar.txt` file

        NOTE: Not 'real-time' data; intended for reference purposes
        """
        df = get_calendar()
        return df

    def transfers(self) -> pd.DataFrame:
        """
        Returns dataframe of GTFS `transfers.txt` file
        
        NOTE: Not 'real-time' data; intended for reference purposes
        """
        df = get_transfers()
        return df

    def stop_times(self,*args) -> pd.DataFrame:
        """
        Returns dataframe of GTFS `stop_times.txt` file
        
        NOTE: Not 'real-time' data; intended for reference purposes
        """
        if len(args) != 0:
            if args[0] == 'bus':
                return get_bus_stop_times()
            elif args[0] == 'train':
                return get_train_stop_times()
        return get_stop_times()

    def calendar_dates(self) -> pd.DataFrame:
        return get_calendar_dates()

    def bus_routes(self,update_data=False) -> pd.DataFrame:
        """Retrieves locally saved bus route data from CTA Bus Tracker API

        Params
        ------
        - `update_data`: (Default FALSE) Set to TRUE to have the data updated before returning it

        Columns in returned dataframe
        --------
        `rt`: bus route id\n
        `rtnm`:bus route name\n
        `rtclr`:bus route color code (HEX CODE)\n
        `rtdd`:bus route 'dd' code? (not completely sure tbh)

        Note:
        -----
        Use cta.update_bus_routes() to ensure the most up-to-date data is being used
        """
        if update_data is True:
            update_bus_routes()
        df = get_bus_routes()
        return df
    
    def route_transfers(self) -> pd.DataFrame:
        return get_route_transfers()

class BusTracker:
    """
    # BusTracker API

    Interface with CTA's BusTrackerAPI to display busses, routes, and other information from the transit system

    Endpoint Methods:
    --------------------
    - stops
    - routes
    - vehicles
    - predictions
    - directions
    - patterns
    """
    def __init__(self):
        self.__stop_reference = get_stops()
        self.__trips = get_trips().dropna()

    def __repr__(self) -> str:
        return f"""<cta.BusTracker>"""

    def stops(self,rt,direction) -> pd.DataFrame:
        """
        Returns dataframe of stops serviced by the Bus
        """
        direction = filter_direction(direction)
        params = {
            "key":CTA_BUS_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_BUS_API_KEY,
            "rt":rt,
            "dir":direction,
            "format":"json"
        }
        url = CTA_BUS_BASE + "/getstops"
        response = requests.get(url,params=params).json()
        data = []
        for s in response["bustime-response"]["stops"]:
            row_data = [
                s.get("stpid"),
                s.get("stpnm"),
                s.get("lat"),
                s.get("lon")]
            data.append(row_data)
        df = pd.DataFrame(data=data,columns=("stpid","stpnm","lat","lon"))
        return df

    def routes(self) -> pd.DataFrame:
        """
        Retrieve a set of routes serviced by the system
        """
        params = {
            "key":CTA_BUS_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_BUS_API_KEY,
            "format":"json"
        }
        url = CTA_BUS_BASE + "/getroutes"
        response = requests.get(url,params=params).json()
        data = []
        for rt in response["bustime-response"]["routes"]:
            data.append([
                rt.get("rt"),
                rt.get("rtnm"),
                rt.get("rtclr"),
                rt.get("rtdd")])
        
        return pd.DataFrame(data=data,columns=("rt","rtnm","rtclr","rtdd"))

    def vehicles(self,vid=None,rt=None,tmres=None) -> pd.DataFrame:
        """
        Returns dataframe of the geolocations for each vehicle along the route

        Params
        ------
        - 'vid'
        - 'rt'
        - 'tmres'
        - 'get_directions'
        """
        params = {
            "key":CTA_BUS_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_BUS_API_KEY,
            "format":"json"
        }
        if tmres is not None:
            params["tmres"] = tmres
        if vid is not None:
            params["vid"] = vid
        elif rt is not None:
            params["rt"] = rt
        else:
            print("must use one of the following params - 'vid', 'rt'")
            return None

        with requests.Session() as sesh:
            t = self.__trips
            url = CTA_BUS_BASE + "/getvehicles"
            response = sesh.get(url,params=params)
            data = []
            for v in response.json()["bustime-response"]["vehicle"]:
                row_data = [
                    v.get("vid"),
                    v.get("tmstmp"),
                    v.get("lat"),
                    v.get("lon"),
                    v.get("hdg"),
                    v.get("pid"),
                    v.get("rt"),
                    v.get("des"),
                    v.get("pdist"),
                    v.get("dly"),
                    v.get("tatripid"),
                    v.get("tablockid")]
                
                data.append(row_data)
            df = pd.DataFrame(data=data,columns=VEHICLE_COLS.values()).astype("str")
            dirs = []
            for i in range(len(df)):
                s = df.iloc[i]
                dirs.append(t[(t.shape_id.str.contains(s.pattern_id))&(t.route_id==s.route)].iloc[0]["direction"]+"bound")
            df.insert(7,"direction",dirs)
        return df

    def predictions(self,stpid=None,vid=None,rt=None,top=None) -> pd.DataFrame:
        """
        Predicted arrival/departure data for the Bus (by 'stpid' or 'vid')

        REQUIRED: ONE of the following -> 'stpid' or 'vid'
        NOTE: Cannot be used together. If both params are propagated, the method will prioritize 'stpid'

        - `stpid`: Comma-delimited list of stop IDs whose predictions are to be returned
        NOTE: Maximum of 10 identifiers can be specified

        - `vid`: Comma-delimited list of vehicle IDs whose predictions should be returned
        NOTE: Maximum of 10 identifiers can be specified

        - `top`: Maximum number of predictions to be returned

        - `sort_by`: column that will be used to sort the dataframe entries
        """
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_BUS_API_KEY
        else:
            key = ALT_BUS_API_KEY
        params = {
            "key":key,
            "format":"json"}
        if stpid is not None:
            params["stpid"] = stpid
            if rt is not None:
                params["rt"] = rt
        elif vid is not None:
            params["vid"] = vid
        else:
            print("must use either stpid or vid param")
            return None
        if top is not None:
            params["top"] = top

        url = CTA_BUS_BASE + f"/getpredictions?"

        response = requests.get(url,params=params)
        data = []
        for p in response.json()["bustime-response"]["prd"]:
            row_data = []
            for col in PREDICTION_COLS.keys():
                if col != "tmstmp":
                    if col == "prdctdn":
                        rem = p.get(col)
                        row_data.append(f"{rem} mins" if rem!="DUE" else f"1 min")
                    elif col == "typ":
                        row_data.append(PRD_TYPES[p.get(col)])
                    else:
                        row_data.append(p.get(col))
                else:
                    row_data.append(p.get(col))
            data.append(row_data)

        return pd.DataFrame(data=data,columns=PREDICTION_COLS.values()).sort_values(by=["vehicle_id","predicted_time"],ascending=[True,True]).reset_index(drop=True)

    def directions(self,rt) -> list:
        params = {
            "key":CTA_BUS_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_BUS_API_KEY,
            "rt":rt,
            "format":"json"}
        url = CTA_BUS_BASE + "/getdirections"
        response = requests.get(url,params=params).json()
        directions = []

        for d in response["bustime-response"]["directions"]:
            directions.append(d["dir"])
        
        return directions

    def stop_reference(self):
        return self.__stop_reference

    def patterns(self,pid=None,rt=None) -> list:
        """
        Returns an array of python dictionary for the Bus route points which, when mapped, can construct the geo-positional layout of a 'route variation'
        
        Params:
        ------
        - 'pid': comma-delimited list of pattern IDs
        - 'rt': single route identifier to retrieve pattern sequences
        """
        if pid is None and rt is None:
            print("must use either 'pid' or 'rt'")
            return None
        return self.__get_patterns(pid,rt)

    def stops_by_distance(self,latitude,longitude,limit=1) -> pd.DataFrame:
        """
        Return the 'stops' dataframe, sorted by distance to given latitude & longitude

        Params:
        -------
        - latitude (required)
        - longitude (required)
        """
        return self.__sort_by_shortest_distance(latitude,longitude,self.__stops).head(limit).reset_index(drop=True)

    def __get_patterns(self,pid=None,rt=None):
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_BUS_API_KEY
        else:
            key = ALT_BUS_API_KEY
        params = {
            "key":key,
            "format":"json"
        }
        if pid is not None:
            params["pid"] = pid
        if rt is not None:
            params["rt"] = rt
        url = CTA_BUS_BASE + f"/getpatterns?"
        response = requests.get(url,params=params)
        resp = response.json()["bustime-response"]
        patterns = resp["ptr"]

        return patterns

    def __sort_by_shortest_distance(self,curr_lat,curr_lon,stop_df):
        stop_df_records = stop_df.to_dict("records")
        distances = []
        for coords in stop_df_records:
            distances.append(get_distance(curr_lat,curr_lon,coords["lat"],coords["lon"]))
        stop_df["dist"] = distances
        return stop_df.sort_values(by="dist",ascending=True)



    # ALIASES -----------------------
    closest_stops = stops_by_distance
    positions = locations = vehicles
    arrivals = predictions
    stop_ref = stop_reference

    # -------------------------------

class TrainTracker:
    """
    # TrainTracker API

    Interface with CTA's TrainTrackerAPI to display trains, routes, and other information from the transit system
    """
    def __init__(self):
        self.__stations = get_train_stations().dropna(subset=["map_id"])
    
    def stations(self):
        return self.__stations
    
    def arrivals(self,*args,mapid=None,stpid=None,max=None,rt=None,limit=None,top=None,route=None,hide_desc_col=True):
        params = {
            "key":CTA_TRAIN_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_TRAIN_API_KEY,
            "outputType":"JSON"}
        if limit is not None:
            max = limit
        if top is not None:
            max = top
        if route is not None:
            rt = route

        if mapid is not None:
            params["mapid"] = mapid
        elif stpid is not None:
            params["stpid"] = stpid
        elif str(args[0])[0] == "3":
            params["stpid"] = args[0]
        elif str(args[0])[0] == "4":
            params["mapid"] = args[0]
        
        if len(args) == 2:
            try:
                params["rt"] = LINES[args[1].lower()]
            except:
                params["rt"] = LINES[rt.lower()]
        else:
            if rt is not None:
                params["rt"] = LINES[rt.lower()]
        if max is not None:
            params["max"] = max
        url = CTA_TRAIN_BASE + "/ttarrivals.aspx?"

        response = requests.get(url,params=params)

        ctatt = response.json()["ctatt"]
        timestamp = ctatt.get("tmst")
        timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
        arrvs = ctatt["eta"]
        data = []
        for a in arrvs:
            prdt = a.get("prdt")
            prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
            arrT = a.get("arrT")
            arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
            due_in = int((arrT_obj - prdt_obj).seconds / 60)
            due_in = 'Due' if due_in == 1 else f'{due_in} mins'
            time_since_update = timestamp_obj - prdt_obj
            time_since_update = f'{time_since_update.seconds} seconds ago'

            # Col-value definitions:
            stop_id = a.get("stpId")
            stop_name = self.__get_stop_name(stop_id)
            map_id = a.get("staId")
            station_name = a.get("staNm")
            station_desc = a.get("stpDe")
            run_num = a.get("rn")
            rt = FILTER_COL[a.get("rt")]
            dest_stop = a.get("destSt")
            dest_name = a.get("destNm")
            trDr = a.get("trDr")
            data.append([
                stop_id,
                stop_name,
                map_id,
                station_name,
                station_desc,
                run_num,
                rt,
                dest_stop,
                dest_name,
                trDr,
                prettify_time(prdt),
                prettify_time(arrT),
                arrT,
                due_in,
                time_since_update,
                a.get("isApp"),
                a.get("isSch"),
                a.get("isDly"),
                a.get("isFlt"),
                a.get("flags"),
                a.get("lat"),
                a.get("lon"),
                a.get("heading")])
        df = pd.DataFrame(data=data,columns=L_ARRIVALS_COLS)
        if hide_desc_col is True:
            return df.drop(columns=["station_desc"])
        return df

    def follow(self,runnumber=None,rn=None,hide_desc_col=True):
        """
        Returns a dataframe of a line's arrival/location data for a specific run_number (rn)
        
        Params:
        -------
        - 'runnumber': the run number (train/vehicle ID) to track (REQUIRED)
        - 'rn': shorthand alias for 'runnumber'

        """
        params = {
        "key":CTA_TRAIN_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_TRAIN_API_KEY,
        "outputType":"JSON"}
        if rn is not None:
            runnumber = rn
        if runnumber is not None:
            params["runnumber"] = runnumber
        else:
            print("Error: 'runnumber' parameter is required")
            return None

        url = CTA_TRAIN_BASE + "/ttfollow.aspx?"
        response = requests.get(url,params=params)
        ctatt = response.json()["ctatt"]
        timestamp = ctatt.get("tmst")
        timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
        if ctatt["errCd"] == "501":
            return ctatt["errNm"]
        position = ctatt["position"]
        lat = position["lat"]
        lon = position["lon"]
        heading = position["heading"]
        data = []
        for e in ctatt["eta"]:
            stpId = e.get("stpId")
            coords = self.__get_stop_coords(stpId)
            stpLat = coords[0]
            stpLon = coords[1]
            prdt = e.get("prdt")
            prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
            arrT = e.get("arrT")
            arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
            due_in = int((arrT_obj - prdt_obj).seconds / 60)
            due_in = 'Due' if due_in == 1 else f'{due_in} mins'
            time_since_update = timestamp_obj - prdt_obj
            time_since_update = f'{time_since_update.seconds} seconds ago'
            data.append([
                stpId,
                stpLat,
                stpLon,
                e.get("staId"),
                e.get("staNm"),
                e.get("stpDe"),
                e.get("destNm"),
                e.get("rn"),
                e.get("rt"),
                e.get("destSt"),
                e.get("trDr"),
                prettify_time(prdt),
                prettify_time(arrT),
                due_in,
                time_since_update,
                e.get("isApp"),
                e.get("isSch"),
                e.get("isDly"),
                e.get("isFlt"),
                e.get("flags"),
                lat,
                lon,
                heading])
        df = pd.DataFrame(data=data,columns=L_FOLLOW_COLS)
        if hide_desc_col is True:
            return df.drop(columns=["service_desc"])
        return df

    def locations(self,route):
        """
        Gets the current position of every train for a given route (line)

        Params:
        -------
        - 'route': route code/line to track locations (can be a comma-separated list of multiple route identifiers)
        """
        params = {
        "key":CTA_TRAIN_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_TRAIN_API_KEY,
        "outputType":"JSON"}
        if route is not None:
            routes = route.split(",")
            new_routes = []
            for rt in routes:
                new_routes.append(LINES[rt.replace(" ","").lower()])
            params["rt"] = ",".join(new_routes)
        else:
            print("Error: 'route' parameter is required")
            return None
        url = f"{CTA_TRAIN_BASE}/ttpositions.aspx?"
        response = requests.get(url,params=params)
        ctatt = response.json()["ctatt"]
        timestamp = ctatt.get("tmst")
        timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
        data = []
        try:
            for r in ctatt["route"]:
                line = FILTER_COL[r.get("@name")]
                train_arrivals = r.get("train")
                for t in train_arrivals:
                    prdt = t.get("prdt")
                    prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
                    arrT = t.get("arrT")
                    arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
                    due_in = int((arrT_obj - prdt_obj).seconds / 60)
                    due_in = 'Due' if due_in == 1 else f'{due_in} mins'
                    time_since_update = timestamp_obj - prdt_obj
                    time_since_update = f'{time_since_update.seconds} seconds ago'
                    
                    run_num = t.get("rn")
                    dest_stop_id = t.get("destSt")
                    service_name = t.get("destNm")
                    next_map_id = t.get("nextStaId")
                    next_station_name = t.get("nextStaNm")
                    next_stop_id = t.get("nextStpId")
                    trDr = t.get("trDr")
                    data.append([
                        line,
                        run_num,
                        dest_stop_id,
                        service_name,
                        next_map_id,
                        next_station_name,
                        next_stop_id,
                        trDr,
                        prettify_time(prdt),
                        prettify_time(arrT),
                        due_in,
                        time_since_update,
                        t.get("isApp"),
                        t.get("isDly"),
                        t.get("flags"),
                        t.get("lat"),
                        t.get("lon"),
                        t.get("heading")])
            df = pd.DataFrame(data=data,columns=L_POSITIONS_COLS)
            return df
        except:
            return pd.DataFrame()

    def __get_stop_name(self,stpid):
        df = self.__stations
        station_row = df[df["stop_id"]==str(stpid)]
        return station_row.stop_name.item()

    def __get_stop_coords(self,stpid):
        df = self.__stations
        station_row = df[df["stop_id"]==stpid].iloc[0]
        return (str(station_row.lat.item()),str(station_row.lon.item()))

    # ALIASES ---------------------
    stops = stations
    predictions = arrivals
    positions = vehicles = trains = locations
    # -----------------------------

class CustomerAlerts:
    """
    # CustomerAlerts API

    Interface with the CTA's CustomerAlertsAPI to display information about active/upcoming alerts for specific routes, trips, and stations 
    """
    def __init__(self):
        # http://lapi.transitchicago.com/api/1.0/routes.aspx?outputType=json
        self.__status = CTA_ALERTS_BASE + "/routes.aspx?"
        self.__details = CTA_ALERTS_BASE + "/alerts.aspx?"
    
    def status(self,service=None,routeid=None,stationid=None,**kwargs):
        """
        Get the overall status information of all (or specified) service types, routes, or stations

        Params:
        -------
        - 'service': single or comma-delimited list of service types (Default value -> "bus,rail,systemwide")
            - Valid values include -> "bus", "rail" ("train"), "station" ("stop"), "systemwide"
        - 'routeid': get status for a specific route/'L'-line
            - 'route' | 'rt' | 'line'
        - 'stationid': get status for a specific station or stop
            - 'stop_id' | 'stpid' | 'map_id' | 'mapid'
        """
        keys = kwargs.keys()
        if "route" in keys:
            routeid = kwargs["route"]
        elif "routes" in keys:
            routeid = kwargs["routes"]
        elif "routeids" in keys:
            routeid = kwargs["routeids"]
        elif "route_ids" in keys:
            routeid = kwargs["route_ids"]
        elif "rt" in keys:
            routeid = kwargs["rt"]
        elif "line" in keys:
            routeid = kwargs["line"]
        elif "lines" in keys:
            routeid = kwargs["line"]

        for i in ("stop_id","map_id","mapid","stpid","station"):
            if i in keys:
                stationid = kwargs[i]
                break
            elif i+"s" in keys:
                stationid = kwargs[i+"s"]
                break

        params = {
            "outputType":"JSON"
            }

        if service is not None:
            service = service.lower().replace(" ","")
            if "train" in service:
                service = service.replace("train","rail")
            if "stop" in service:
                service = service.replace("stop","station")
            params["type"] = service

        if routeid is not None:
            routeid = str(routeid)
            params["routeid"] = LINES.get(routeid.lower(),routeid)
            
        if stationid is not None:
            params["stationid"] = stationid

        url = self.__status
        response = requests.get(url,params=params)
        data = []
        route_info = response.json()["CTARoutes"]["RouteInfo"]
        try:
            for ri in route_info:
                data.append([
                    ri.get("Route"),
                    ri.get("ServiceId"),
                    ri.get("RouteStatus"),
                    ri.get("RouteStatusColor"),
                    ri.get("RouteColorCode"),
                    ri.get("RouteTextColor"),
                    ri.get("RouteURL",{}).get("#cdata-section"),
                ])
        except:
            data = []
            data.append([
                route_info.get("Route"),
                route_info.get("ServiceId"),
                route_info.get("RouteStatus"),
                route_info.get("RouteStatusColor"),
                route_info.get("RouteColorCode"),
                route_info.get("RouteTextColor"),
                route_info.get("RouteURL",{}).get("#cdata-section"),
            ])

        df = pd.DataFrame(data=data,columns=("service","service_id","status","status_color","route_color","route_text","url"))
        return df

    def details(self,activeonly=False,accessibility=True,planned=None,routeid=None,stationid=None,bystartdate=None,recentdays=None,**kwargs):
        """
        Get full details of alerts

        Params:
        -------
        - 'activeonly': Default FALSE; if set to TRUE, response yields events only where the start time is in the past and the end time is in the future (or unknown)
        - 'accessibility': Default TRUE; if set to FALSE, response excludes events that affect accessible paths in stations
        - 'planned': Default TRUE; if set to FALSE, response excludes common planned alerts and includes only UNplanned alerts
        - 'bystartdate': (YYYYmmdd) if specified, response includes only events with a start date pre-dating the one specified
            - excludes events that don't begin until on or after the specified point in the future
        - 'recentdays': if specified, yields events that have started within 'x' number of days before today
        - 'routeid': get status for a specific route/'L'-line
            - 'route' | 'rt' | 'line'
        - 'stationid': get status for a specific station or stop
            - 'stop_id' | 'stpid' | 'map_id' | 'mapid'        
        """
        activeonly = kwargs.get("active",activeonly)

        accessibility = kwargs.get(
            "accessible",kwargs.get(
                "handicapped",accessibility
            )
        )
        routeid = kwargs.get(
            "route",kwargs.get(
                "rt",kwargs.get(
                    "line",routeid
                )
            )
        )
        stationid = kwargs.get(
            "stop_id",kwargs.get(
                "map_id",kwargs.get(
                    "stpid",kwargs.get(
                        "mapid",stationid
                    )
                )
            )
        )
        bystartdate = kwargs.get(
            "start_date",kwargs.get(
                "startdate",kwargs.get(
                    "startDate",kwargs.get(
                        "start",kwargs.get(
                            "from",kwargs.get(
                                "from_date",kwargs.get(
                                    "fromDate",bystartdate
                                )
                            )
                        )
                    )
                )
            )
        )
        recentdays = kwargs.get(
            "pastdays",kwargs.get(
                "last",kwargs.get(
                    "numdays",recentdays
                )
            )
        )

        params = {
            "outputType":"JSON",
            "activeonly":activeonly,
            "accessibility":accessibility,
            "planned":planned}
        
        if routeid is not None:
            params["routeid"] = routeid
        if stationid is not None:
            params["stationid"] = stationid
        if bystartdate is not None:
            params["bystartdate"] = bystartdate
        if recentdays is not None:
            params["recentdays"] = recentdays

        url = self.__details
        response = requests.get(url,params=params)
        data = []
        cta_alerts = response.json()["CTAAlerts"]
        for a in cta_alerts["Alert"]:
            service = a.get("ImpactedService",{}).get("Service")
            description = a.get("FullDescription",{}).get("#cdata-section")
            soup = bs(description,"html5lib")
            css = a.get("SeverityCSS")
            start = a.get("EventStart")
            end = a.get("EventEnd")
            all_ps = soup.find_all("p")
            # info = self.__simplify_soup(soup,css)
            desc = soup.text.strip().replace("\xa0"," ")
            if type(service) is list:
                for s in service:
                    data.append([
                        s.get("ServiceType"),
                        s.get("ServiceTypeDescription"),
                        s.get("ServiceName"),
                        s.get("ServiceId"),
                        s.get("ServiceBackColor"),
                        s.get("ServiceTextColor"),
                        a.get("AlertId"),
                        a.get("Headline"),
                        desc,
                        soup,
                        # info,
                        a.get("SeverityScore"),
                        a.get("SeverityColor"),
                        css,
                        a.get("Impact"),
                        start,
                        end,
                        a.get("TBD"),
                        a.get("MajorAlert")
                        ])
            elif type(service) is dict:
                data.append([
                    service.get("ServiceType"),
                    service.get("ServiceTypeDescription"),
                    service.get("ServiceName"),
                    service.get("ServiceId"),
                    service.get("ServiceBackColor"),
                    service.get("ServiceTextColor"),
                    a.get("AlertId"),
                    a.get("Headline"),
                    desc,
                    soup,
                    # info,
                    a.get("Impact"),
                    a.get("SeverityScore"),
                    a.get("SeverityColor"),
                    css,
                    start,
                    end,
                    a.get("TBD"),
                    a.get("MajorAlert")
                ])
        
        df = pd.DataFrame(data=data,columns=(
            "type_id",
            "type",
            "name",
            "service_id",
            "service_color",
            "service_text",
            "alert_id",
            "headline",
            "desc",
            "desc_html",
            # "info",
            "impact",
            "score",
            "color",
            "css",
            "start",
            "end",
            "tbd",
            "major"))
        
        return df
    
    def __simplify_soup(self,soup,css):
        all_ps = soup.find_all("p")
        if css == "normal":
            if len(all_ps) == 3:
                t1 = normalize("NFKD",all_ps[0].text.replace("How does this affect my trip?","").replace("\n"," ").replace("\r","").strip())
                t2 = normalize("NFKD",all_ps[1].text.strip())
                t3 = normalize("NFKD",all_ps[2].text.strip().replace("Why is service being changed?","").replace("\n"," ").replace("\r","").strip())
                info = f'{t1}<N>{t2}<N>{t3}'
            elif len(all_ps) == 2:
                t1 = normalize("NFKD",all_ps[0].text.replace("How does this affect my trip?","").replace("\n"," ").replace("\r","").strip())
                t2 = normalize("NFKD",all_ps[1].text.strip().replace("Why is service being changed?","").replace("\n"," ").replace("\r","").strip())
                info = f'{t1}<N>{t2}'
        else:
            info = "--"
        # elif css == "planned":
        #     desc1 = normalize("NFKD",all_ps[0].text.replace("How does this affect my trip?\r\n","").strip())
        #     desc2 = normalize("NFKD",all_ps[1].text.strip())
        #     desc3 = normalize("NFKD",all_ps[2].text.strip().replace("Why is service being changed?\r\n","").strip())
        # elif css == "Elevator Status":
        #     desc1 = normalize("NFKD",all_ps[0].text.replace("How does this affect my trip?\r\n","").strip())
        #     desc2 = normalize("NFKD",all_ps[1].text.strip())
        #     desc3 = normalize("NFKD",all_ps[2].text.strip().replace("Why is service being changed?\r\n","").strip())
        # elif css == "Minor":
        #     desc1 = normalize("NFKD",all_ps[0].text.replace("How does this affect my trip?\r\n","").strip())
        #     desc2 = normalize("NFKD",all_ps[1].text.strip())
        #     desc3 = normalize("NFKD",all_ps[2].text.strip().replace("Why is service being changed?\r\n","").strip())
        # elif css == "Major":
        #     desc1 = normalize("NFKD",all_ps[0].text.replace("How does this affect my trip?\r\n","").strip())
        #     desc2 = normalize("NFKD",all_ps[1].text.strip())
        #     desc3 = normalize("NFKD",all_ps[2].text.strip().replace("Why is service being changed?\r\n","").strip())
        return info

# ====================================================================================================
# Other
# ====================================================================================================
class StopSearch:
    def __init__(self):
        df = get_stops().rename(columns={"stop_lat":"lat","stop_lon":"lon"}).drop(columns=["map_id","stop_code","location_type"])
        self.__cta_stops = df.dropna(subset=['stop_id']).astype({'stop_id':'int','stop_desc':'str'})
        self.__route_stops = get_route_transfers().astype('str')
        self.__train_stops = get_train_stations()

        # self.__train_stations = get_train_stations()
        # self.__train_stops = df[df.map_id.notna()]
        # self.__bus_stops = df[df.map_id.isna()]

    def find_stop(self,query,stop_type=None,rtdir=None,hide_desc_col=False):
        """
        Search for a CTA stop/station by name.
        """
        df = get_stops().astype('str')
        q = query.lower().replace("and","&")
        if "&" in q:
            q_list = str(q).split("&")
            street1 = q_list[0].strip()
            street2 = q_list[1].strip()
            results = []
            for idx,s in enumerate(df.stop_name):
                if street1 in str(s).lower() and street2 in str(s).lower():
                    results.append(df.iloc[idx])
        else:
            results = []
            for idx,s in enumerate(df.stop_name):
                if q in str(s).lower():
                    results.append(df.iloc[idx])

        df = pd.DataFrame(results)
        route_dirs = []
        for desc in df.stop_desc:
            if "northbound" in desc.lower():
                route_dirs.append("N")
            elif "southbound" in desc.lower():
                route_dirs.append("S")
            elif "westbound" in desc.lower():
                route_dirs.append("W")
            elif "eastbound" in desc.lower():
                route_dirs.append("E")
            else:
                route_dirs.append("-")
        df.insert(4,"rtdir",route_dirs)
        # df["stop_desc"].str.slice(df["stop_desc"].str.find(", ")+2)
        if rtdir is not None:
            rtdir = rtdir.lower()
            if "north" in rtdir:
                rtdir = 'n'
            elif "south" in rtdir:
                rtdir = 's'
            elif "west" in rtdir:
                rtdir = 'w'
            elif "east" in rtdir:
                rtdir = 'e'
            df = df[df["rtdir"].str.lower()==rtdir]
        
        if stop_type is not None:
            stop_type = stop_type.lower()
            df = df.astype({'stop_id':'int'})
            if stop_type == 'bus':
                df = df[df['stop_id']<30000]
            elif stop_type == 'train' or stop_type == 'rail' or stop_type == 'l':
                df = df[df['stop_id']>29999]
                
        df = df.astype({'stop_id':'str'})
        if hide_desc_col is True:
            return df.drop(columns=["stop_desc"]).reset_index(drop=True)
        else:
            return df.reset_index(drop=True)

    def closest_stops(self,*args,routes=None,directions=None,limit=3,stop_type=None,exclude_stops=None,**kwargs):
        """
        Retrieve the closest CTA bus and/or train stops near a given location (by coordinates)

        Required Positional Args:
        -------------------------
        - coordinates (str | list | tuple)
            - can be one arg as list (or tuple) of latitude & longitude
            - can be one arg as comma-delimited coordinates (str or float)
            - can be two separate args (str or float)
        
        Optional Parameters:
        -------------------------
        - 'routes':
        - 'directions':
        - 'limit':
        - 'stop_type':
        - 'exclude_stops':
        """
        train_stops_only = self.__train_stops
        
        # ------- ASSIGNING ALIASES TO SINGLE VARIABLES ----------

        for key in ("route","line","lines"):
            if key in kwargs.keys():
                routes = kwargs[key].lower()
                break
        for key in ("dirs","rtdirs","dir_ids"):
            if key in kwargs.keys():
                directions = kwargs[key].lower()
                break
        for key in ("max","top"):
            if key in kwargs.keys():
                limit = kwargs[key]
                break
        for key in ("category","type"):
            if key in kwargs.keys():
                stop_type = kwargs[key].lower()
                break
        for key in ("exclude","excluded","exclude_stop","excluded_stops"):
            if key in kwargs.keys():
                exclude_stops = kwargs[key].lower()
                break
        
        # ------- HANDLING DIRECTIONS PARAM  ---------------------
        busdirs = None
        traindirs = None
        if directions is not None:
            if type(directions) is str:
                directions = directions.replace(" ","").split(",")
                directions = list(map(get_direction_symbol,directions))
                busdirs = directions
                traindirs = directions
            elif type(directions) is list or type(directions) is tuple:
                directions = list(map(get_direction_symbol,directions))
                busdirs = directions
                traindirs = directions
            else:
                busdirs = directions.get("bus")
                traindirs = directions.get("train")
                if type(busdirs) is str:
                    busdirs = busdirs.replace(" ","").split(",")
                    busdirs = list(map(get_direction_symbol,busdirs))
                elif type(busdirs) is list or type(busdirs) is tuple:
                    busdirs = list(map(get_direction_symbol,busdirs))
                if type(traindirs) is str:
                    traindirs = traindirs.replace(" ","").split(",")
                    traindirs = list(map(get_direction_symbol,traindirs))
                elif type(traindirs) is list or type(traindirs) is tuple:
                    traindirs = list(map(get_direction_symbol,traindirs))

        # ------- DEALING WITH POSSIBLE TYPES FOR LIMIT PARAM ----

        if type(limit) is list or type(limit) is tuple:
            bus_limit = limit[0]
            train_limit = limit[1]
        elif type(limit) is dict:
            bus_limit = limit.get('bus',3)
            train_limit = limit.get('train',3)
        else:
            bus_limit = limit
            train_limit = limit

        # ------- DEALING WITH TYPES FOR POSITIONAL ARGS ---------

        if len(args) == 1:
            if type(args[0]) is tuple or type(args[0]) is list:
                lat = args[0][0]
                lon = args[0][1]
            elif type(args) is str:
                coords = args[0].replace(" ","").split(",")
                lat = coords[0]
                lon = coords[1]
            else:
                return None
        elif len(args) == 2:
            lat = args[0]
            lon = args[1]
        else:
            print("Minimum ONE positional argument required, maximum TWO allowed")
        
        # ------- CREATING SEPARATE BUS/TRAIN STOPS --------------

        # BUS STOPS
        df = self.__cta_stops.copy()
        bus_stop_df = df[df['stop_id']<30000]
        # TRAIN STOPS
        train_stop_df = df[df['stop_id'].between(30000,39999,'both')]

        if routes is not None:
            # ------- GETTING ONLY INCLUDED ROUTES ---------------
            rtstops = self.__route_stops

            if type(routes) is str:
                routes = routes.replace(" ","").split(",")
            elif type(routes) is list or type(routes) is tuple:
                routes = routes

            routes = list(map(str.title,routes))
            rtstops_df = rtstops[rtstops["rt"].isin(routes)]

            stops_to_filter_by = list(set(rtstops_df.stop_id))

            # BUS STOPS
            bus_stop_df = bus_stop_df[bus_stop_df["stop_id"].astype('str').isin(stops_to_filter_by)]

            # TRAIN STOPS
            train_stop_df = train_stop_df[train_stop_df["stop_id"].astype('str').isin(stops_to_filter_by)]

        elif exclude_stops is not None:
            # ------- FILTERING OUT EXCLUDED ROUTES --------------
            rtstops = self.__route_stops

            if type(exclude_stops) is str:
                exclude_stops = exclude_stops.replace(" ","").split(",")
            elif type(exclude_stops) is list or type(exclude_stops) is tuple:
                exclude_stops = exclude_stops

            exclude_stops = list(map(str.title,exclude_stops))

            # BUS STOPS
            bus_stop_df = bus_stop_df[~bus_stop_df["stop_id"].astype('str').isin(exclude_stops)]

            # TRAIN STOPS
            train_stop_df = train_stop_df[~train_stop_df["stop_id"].astype('str').isin(exclude_stops)]

        

        # ------- CALCULATING DISTANCES FROM STOPS ---------------

        bus_stop_records = bus_stop_df.to_dict("records")
        train_stop_records = train_stop_df.to_dict("records")
        bus_stop_distances = []
        train_stop_distances = []

        # BUS STOPS
        for rec in bus_stop_records:
            bus_stop_distances.append(get_distance(lat,lon,rec["lat"],rec["lon"]))
        
        # TRAIN STOPS
        for rec in train_stop_records:
            train_stop_distances.append(get_distance(lat,lon,rec["lat"],rec["lon"]))

        # ------- SORTING BY DISTANCE ----------------------------

        # BUS STOPS
        bus_stop_df.insert(len(bus_stop_df.columns),"dist",bus_stop_distances)
        bus_stop_df = bus_stop_df.sort_values(by="dist",ascending=True)
        bus_stop_df = bus_stop_df #.head(bus_limit)
        bus_stop_df.insert(0,"type","bus")
            # ---- CREATING BUS DIRECTIONS COL -------------------
        bus_stop_df.insert(2,"dir",bus_stop_df.apply(lambda row: translate_bus_dir(row),axis=1))

        # TRAIN STOPS
        train_stop_df.insert(len(train_stop_df.columns),"dist",train_stop_distances)
        train_stop_df = train_stop_df.sort_values(by="dist",ascending=True)
        train_stop_df = train_stop_df #.head(train_limit)
        train_stop_df.insert(0,"type","train")
            # ---- CREATING TRAIN DIRECTIONS COL -----------------
        train_dirs_data = []
        for idx in range(len(train_stop_df)):
            s = train_stop_df.iloc[idx]
            train_dirs_data.append(train_stops_only[train_stops_only["stop_id"]==str(s.stop_id)].direction_id.item())
        train_stop_df.insert(2,"dir",train_dirs_data)

        # ------- FILTERING BY DIRECTIONS ------------------------
        if busdirs is not None:
            bus_stop_df = bus_stop_df[bus_stop_df["dir"].isin(busdirs)]
        if traindirs is not None:
            train_stop_df = train_stop_df[train_stop_df["dir"].isin(traindirs)]

        bus_stop_df = bus_stop_df.head(bus_limit)
        bus_stop_df = bus_stop_df.astype('str')
        train_stop_df = train_stop_df.head(train_limit)
        train_stop_df = train_stop_df.astype('str')
        
        if len(train_stop_df) == 0 or stop_type == "bus":
            return bus_stop_df.reset_index(drop=True)
        elif len(bus_stop_df) == 0 or stop_type == "train" or stop_type == "l" or stop_type == "rail":
            return train_stop_df.reset_index(drop=True)
        else:
            return pd.concat([bus_stop_df,train_stop_df]).reset_index(drop=True)

    def lookup(self,query):
        """
        Retrieve details of a location by query
        """
        return locate(q=query)

class TransitData:
    """
    # CTA Ridership (Socrata API)
    """
    def __init__(self):
        self.__today_obj = dt.datetime.today()
        self.__today = self.__today_obj.strftime(r"%Y-%m-%d")
        self.__delta_365_obj = self.__today_obj - dt.timedelta(days=365)
        self.__delta_365 = self.__delta_365_obj.strftime(r"%Y-%m-%d")

    def query(self,date=None,date_range=None,limit=None):
        """
        Date values should follow the format, "YYYY-mm-dd"

        NOTE: 'date' and 'date_range' params should be used independently. If 'date' is used, 'date_range' value will be ignored

        """
        params={}
        sfx = "T00:00:00.000"
        from_date = self.__delta_365 + sfx
        to_date = self.__today + sfx
        if date is not None:
            date_range = date_range.split(",")
            from_date = date_range[0].replace("/","-").strip() + sfx
            to_date = date_range[1].replace("/","-").strip() + sfx
            params["$where"] = f"service_date = '{date}'"
        elif date_range is not None:
            if type(date_range) is list or type(date_range) is tuple:
                from_date = date_range[0].replace("/","-").strip() + sfx
                to_date = date_range[1].replace("/","-").strip() + sfx
                params["$where"] = f"service_date between '{from_date}' and '{to_date}'"
            elif type(date_range) is str:
                date_range = date_range.split(",")
                from_date = date_range[0].replace("/","-").strip() + sfx
                to_date = date_range[1].replace("/","-").strip() + sfx
                params["$where"] = f"service_date between '{from_date}' and '{to_date}'"
        if limit is not None:
            params["$limit"] = limit
        
        response = requests.get(DATA_BASE,params=params)
        print(response.url)
        data = response.json()
        return pd.DataFrame(data)

class RouteSketch:
    """
    Create a mapped route made up of a series of coordinates
    """
    def __init__(self,sketch_type,data):
        pass

# ====================================================================================================
# Functions
# ====================================================================================================
def cta_stops():
    """
    Get a dataframe of all bus stops & train stations/platforms serviced by the CTA
    """
    return get_stops()

def cta_trips():
    """
    Get a dataframe of all trips performed by CTA vehicles (bus & L train) 
    """
    return get_trips()

def route_transfers() -> pd.DataFrame:
    """
    Returns a dataframe of transfer details for each route & stop/station)

    (Retrieved from `CTA_STOP_XFERS.txt` file provided by CTA in static feed directory)
    
    NOTE: Not 'real-time' data; intended for reference purposes
    """
    return get_route_transfers()

def bus_routes(update_data=False) -> pd.DataFrame:
    """Retrieves locally saved bus route data from CTA Bus Tracker API

    Params
    ------
    - `update_data`: (Default FALSE) Set to TRUE to have the data updated before returning it

    Columns in returned dataframe
    --------
    `rt`: bus route id\n
    `rtnm`:bus route name\n
    `rtclr`:bus route color code (HEX CODE)\n
    `rtdd`:bus route 'dd' code? (not completely sure tbh)

    Note:
    -----
    Use cta.update_bus_routes() to ensure the most up-to-date data is being used
    """
    if update_data is True:
        update_bus_routes()
    df = get_bus_routes()
    return df

def bus_locations(vid) -> pd.DataFrame:
    """
    Returns current geo data for a specific vehicle (or vehicles)

    Params
    ------
    - `vid`: vehicle id (or comma-delimited list of multiple vehicle ids - limit 10)
    """
    if dt.datetime.now().time() < dt.time(16,0,0):
        key = CTA_BUS_API_KEY
    else:
        key = ALT_BUS_API_KEY
    params = {
        "key":key,
        "vid":vid,
        "format":"json"
    }
    url = CTA_BUS_BASE + "/getvehicles"
    response = requests.get(url,params=params)
    data = []
    for v in response.json()["bustime-response"]["vehicle"]:
        row_data = [
            v.get("vid","-"),
            v.get("tmstmp","-"),
            v.get("lat","-"),
            v.get("lon","-"),
            v.get("hdg","-"),
            v.get("pid","-"),
            v.get("rt","-"),
            v.get("des","-"),
            v.get("pdist","-"),
            v.get("dly",None),
            v.get("tatripid","-"),
            v.get("tablockid","-")]
        
        data.append(row_data)
    df = pd.DataFrame(data=data,columns=VEHICLE_COLS.values())
    return df

def bus_vehicles(vid) -> pd.DataFrame:
    """
    ALIAS FOR `bus_locations`\nReturns current geo data for a specific vehicle (or vehicles)

    Params
    ------
    - `vid`: vehicle id (or comma-delimited list of multiple vehicle ids - limit 10)
    """
    return bus_locations(vid)

def bus_directions(route) -> pd.DataFrame:
    """
    Returns a python dictionary detailing the directions a bus route follows\n
    (Northbound, Southbound, Eastbound, Westbound)

    Params
    ------
    - `route`: bus number/route code

    NOTE: Fetches Data from CTA's Bus Tracker API
    """
    if dt.datetime.now().time() < dt.time(16,0,0):
        key = CTA_BUS_API_KEY
    else:
        key = ALT_BUS_API_KEY
    params = {
        "key":key,
        "rt":route,
        "format":"json"
    }
    url = CTA_BUS_BASE + f"/getdirections?"
    response = requests.get(url,params=params)
    return pformat(response.json())

def bus_predictions(stpid=None,vid=None,route=None,top=None) -> pd.DataFrame:
    """
    Returns dataframe of predicted arrival data for a specified stop(s) or a specific vehicle(s)

    Params
    ----------
    - `stpid` (CONDITIONALLY REQUIRED): Comma-delimited list of stop IDs whose predictions are to be returned
        - Required if vehicle id not provided (cannot be used with `vid`)
        - Maximum of 10 identifiers can be specified
    - `vid` (CONDITIONALLY REQUIRED): Comma-delimited list of vehicle IDs whose predictions should be returned
        - - Required if stop id not provided (cannot be used with `stpid`)
        - Maximum of 10 identifiers can be specified
    - `rt`: Comma-delimited list of routes or which matching predictions are to be returned
    - `top`: Maximum number of predictions to be returned
    """
    if dt.datetime.now().time() < dt.time(16,0,0):
        key = CTA_BUS_API_KEY
    else:
        key = ALT_BUS_API_KEY
    params = {
        "key":key,
        "format":"json"
    }
    if stpid is not None:
        params["stpid"] = stpid
    elif vid is not None:
        params["vid"] = vid
    else:
        print("must use either stpid or vid param")
    if top is not None:
        params["top"] = top
    if route is not None:
        params["rt"] = route

    url = CTA_BUS_BASE + f"/getpredictions?"

    response = requests.get(url,params=params)
    data = []
    for p in response.json()["bustime-response"]["prd"]:
        row_data = []
        for col in PREDICTION_COLS:
            row_data.append(p.get(col,"-"))
        data.append(row_data)
    
    df = pd.DataFrame(data=data,columns=PREDICTION_COLS.values())

    return df

def bus_route_stops(route,direction) -> pd.DataFrame:
    """
    Returns dataframe of all stops for a bus service

    Required Params
    ------
    - `route`: bus number/route code (e.g. '151' or 'X20')
    - `direction`: operating direction serviced by a specific bus number
        - E.g. 'Northbound' or 'Eastbound'
        - Can also accept "shorthand" values ('n', 's', 'e', 'w')
        - Refer to the `bus_directions` function to get a list of accepted `direction` values for any given route
    """
    df = get_bus_route_stops(route,direction)
    return df

def bus_stop_times() -> pd.DataFrame:
    return get_bus_stop_times()

def train_stations(hide_desc_col=True) -> pd.DataFrame:
    """
    Returns dataframe of train stations provided by the City of Chicago's transit database via JSON url

    NOTE: This data differs slightly from the Static Feed data
    """
    df = get_train_stations()
    if hide_desc_col is True:
        return df.drop(columns=["station_descriptive_name"])
    else:
        return df

def train_arrivals(*args,**kwargs) -> pd.DataFrame:
    """
    Returns dataframe estimated arrival times & locations (given a station/stop) for vehicles serviced by the Line.\n
    (Method will auto detect if the entered param value is a stop id or a station id)
    
    Required Args:
    ---------------
    - `stp_or_map_id`: Valid 'stpid' or 'mapid'
    """
    stpid_or_mapid = args[0]

    if dt.datetime.now().time() < dt.time(16,0,0):
        key = CTA_TRAIN_API_KEY
    else:
        key = ALT_TRAIN_API_KEY
    params = {
        "key":key,
        "outputType":"JSON"}
    if str(stpid_or_mapid)[0] == "3":
        params["stpid"] = stpid_or_mapid
    elif str(stpid_or_mapid)[0] == "4":
        params["mapid"] = stpid_or_mapid
    else:
        print("Error: Ensure that you have entered a valid 'stpid' or 'mapid'")
        return None

    for possible_key in ("line","route","rt","route_id","line_ref"):
        if possible_key in kwargs.keys():
            params['rt'] = kwargs[possible_key]
            break
            
    url = f"{CTA_TRAIN_BASE}/ttarrivals.aspx?"
    response = requests.get(url,params=params)

    ctatt = response.json()["ctatt"]
    timestamp = ctatt.get("tmst")
    timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
    arrvs = ctatt["eta"]
    data = []
    for a in arrvs:
        prdt = a.get("prdt")
        prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
        arrT = a.get("arrT")
        arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
        due_in = int((arrT_obj - prdt_obj).seconds / 60)
        due_in = 'Due' if due_in == 1 else f'{due_in} mins'
        time_since_update = timestamp_obj - prdt_obj
        time_since_update = f'{time_since_update.seconds} seconds ago'

        # Col-value definitions:
        stop_id = a.get("stpId")
        stop_name = get_stop_name(stop_id)
        map_id = a.get("staId")
        station_name = a.get("staNm")
        station_desc = a.get("stpDe")
        run_num = a.get("rn"),
        rt = a.get("rt"),
        dest_stop = a.get("destSt")
        dest_name = a.get("destNm")
        trDr = a.get("trDr")
        data.append([
            stop_id,
            stop_name,
            map_id,
            station_name,
            station_desc,
            run_num,
            rt,
            dest_stop,
            dest_name,
            trDr,
            prettify_time(prdt),
            prettify_time(arrT),
            due_in,
            time_since_update,
            a.get("isApp"),
            a.get("isSch"),
            a.get("isDly"),
            a.get("isFlt"),
            a.get("flags"),
            a.get("lat"),
            a.get("lon"),
            a.get("heading")])
    df = pd.DataFrame(data=data,columns=L_ARRIVALS_COLS)
    return df

def train_positions(rt) -> pd.DataFrame:
    """
    (Not properly configured yet)
    Gets the current position of every vehicle for this CTA Line's Route

    Required Args:
    ---------------
    - 'rt': a valid route identifier
    """
    if dt.datetime.now().time() < dt.time(16,0,0):
        key = CTA_TRAIN_API_KEY
    else:
        key = ALT_TRAIN_API_KEY
    params = {
    "key":key,
    "rt":rt,
    "outputType":"JSON"}
    url = f"{CTA_TRAIN_BASE}/ttpositions.aspx?"
    response = requests.get(url,params=params)
    ctatt = response.json()["ctatt"]
    timestamp = ctatt.get("tmst")
    timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
    data = []
    for r in ctatt["route"]:
        line = FILTER_COL[r.get("@name")]
        train_arrivals = r.get("train")
        for t in train_arrivals:
            prdt = t.get("prdt")
            prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
            arrT = t.get("arrT")
            arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
            due_in = int((arrT_obj - prdt_obj).seconds / 60)
            due_in = 'Due' if due_in == 1 else f'{due_in} mins'
            time_since_update = timestamp_obj - prdt_obj
            time_since_update = f'{time_since_update.seconds} seconds ago'
            
            run_num = t.get("rn")
            dest_stop_id = t.get("destSt")
            service_name = t.get("destNm")
            next_map_id = t.get("nextStaId")
            next_station_name = t.get("nextStaNm")
            next_stop_id = t.get("nextStpId")
            trDr = t.get("trDr")
            data.append([
                line,
                run_num,
                dest_stop_id,
                service_name,
                next_map_id,
                next_station_name,
                next_stop_id,
                trDr,
                prettify_time(prdt),
                prettify_time(arrT),
                due_in,
                time_since_update,
                t.get("isApp"),
                t.get("isDly"),
                t.get("flags"),
                t.get("lat"),
                t.get("lon"),
                t.get("heading")])
    df = pd.DataFrame(data=data,columns=L_POSITIONS_COLS)
    return df

def train_follow(rn,hide_desc_col=True) -> pd.DataFrame:
    """
    (Not properly configured yet)
    Returns a dataframe of a line's arrival/location data for a specific run_number (rn)
    
    Params:
    -------
    - `rn`: the run number to retrieve data for
    """
    if dt.datetime.now().time() < dt.time(16,0,0):
        key = CTA_TRAIN_API_KEY
    else:
        key = ALT_TRAIN_API_KEY
    params = {
    "key":key,
    "runnumber":rn,
    "outputType":"JSON"}
    url = f"{CTA_TRAIN_BASE}/ttfollow.aspx?"
    response = requests.get(url,params=params)
    ctatt = response.json()["ctatt"]
    timestamp = ctatt.get("tmst")
    timestamp_obj = dt.datetime.strptime(timestamp,ISO_FMT_ALT)
    position = ctatt["position"]
    lat = position["lat"]
    lon = position["lon"]
    heading = position["heading"]
    data = []
    for e in ctatt["eta"]:
        stpId = e.get("stpId")
        coords = get_stop_coords(stpId)
        stpLat = coords[0]
        stpLon = coords[1]
        prdt = e.get("prdt")
        prdt_obj = dt.datetime.strptime(prdt,ISO_FMT_ALT)
        arrT = e.get("arrT")
        arrT_obj = dt.datetime.strptime(arrT,ISO_FMT_ALT)
        due_in = int((arrT_obj - prdt_obj).seconds / 60)
        due_in = 'Due' if due_in == 1 else f'{due_in} mins'
        time_since_update = timestamp_obj - prdt_obj
        time_since_update = f'{time_since_update.seconds} seconds ago'
        data.append([
            stpId,
            stpLat,
            stpLon,
            e.get("staId"),
            e.get("staNm"),
            e.get("stpDe"),
            e.get("destNm"),
            e.get("rn"),
            e.get("rt"),
            e.get("destSt"),
            e.get("trDr"),
            prettify_time(prdt),
            prettify_time(arrT),
            due_in,
            time_since_update,
            e.get("isApp"),
            e.get("isSch"),
            e.get("isDly"),
            e.get("isFlt"),
            e.get("flags"),
            lat,
            lon,
            heading])
    df = pd.DataFrame(data=data,columns=L_FOLLOW_COLS)
    if hide_desc_col is True:
        return df.drop(columns=["service_desc"])
    return df

def train_stop_times() -> pd.DataFrame:
    return get_train_stop_times()




