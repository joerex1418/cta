from typing import Iterable
import requests
import pandas as pd
from pprint import pformat

from .constants import *

from .utils import prettify_time
from .utils import get_distance
from .utils import ISO_FMT_ALT

from .utils_cta import *

class StaticFeed:
    """
    # CTA GTFS Static Feed

    Interface with the CTA static feed to display information from the local machine's GTFS txt files

    - Run 'cta.update_static_feed()' to download .txt files to local storage

    """
    def __init__(self) -> None:
        pass

    def stops(self,hide_desc_col=True) -> pd.DataFrame:
        """
        Returns dataframe of GTFS `stops.txt` file

        NOTE: Not 'real-time' data; intended for reference purposes
        """
        df = get_stops()
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
        if hide_desc_col == True:
            return df.drop(columns=["stop_desc"])
        else:
            return df

    def routes(self,update_data=False) -> pd.DataFrame:
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

    def stop_times(self) -> pd.DataFrame:
        """
        Returns dataframe of GTFS `stop_times.txt` file
        
        NOTE: Not 'real-time' data; intended for reference purposes
        """
        df = get_stop_times()
        return df

class BusRoute:
    """
    # Bus Route
    Represents a bus service going in a single direction

    Required Attributes
    -------------------
    - 'route': alphanumeric bus number
    - 'direction': the general direction of travel ("Northbound","Southbound","Westbound","Eastbound")
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

    def bus(self) -> pd.DataFrame:
        """
        Display Bus Route information
        """
        return f"""
        Bus Number: {self.__route}
        Direction:  {self.__direction}
        """

    def show_route(self):
        return self.__route
    
    def show_direction(self):
        return self.__direction

    def stops(self) -> pd.DataFrame:
        """
        Returns dataframe of stops serviced by the Bus
        """
        return self.__stops

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
        if dt.datetime.now().time() < dt.time(16,0,0):
            key = CTA_BUS_API_KEY
        else:
            key = ALT_BUS_API_KEY
        params = {
            "key":key,
            "rt":self.__route,
            "format":"json"
        }
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
                if col != "tmstmp":
                    row_data.append(p.get(col,"-"))
                else:
                    ### NEED TO FIX THIS IN UTILS
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
                v.get("tablockid","-"),
                v.get("zone","")]
            
            data.append(row_data)
        df = pd.DataFrame(data=data,columns=VEHICLE_COLS.values())
        df = df[df["pattern_id"].isin(self.__pids)]
        
        if vid is not None:
            return df
        else:
            self.__vehicles = df

class BusStop:
    def __init__(self,stop_id) -> None:
        self.__stop_id = stop_id

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
        return f"""<cta.Line object | {self.line_name}>"""

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
        if hide_desc_col is True:
            return df.drop(columns=["station_desc"])
        return df

    def positions(self):
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
        station_row = df[df["stop_id"]==stpid]
        return (str(station_row.lat.item()),str(station_row.lon.item()))

    def __get_stop_name(self,stpid):
        df = self.__stations
        station_row = df[df["stop_id"]==str(stpid)]
        return station_row.stop_name.item()
    
    def stops(self,hide_desc_col=True,hide_other_lines=True):
        return self.stations(hide_desc_col,hide_other_lines)

class TrainStation:
    def __init__(self,station_id):
        self.__station_id = station_id
        self.__map_id = station_id

class RouteSketch:
    """
    Create a mapped route made up of a series of coordinates
    """
    def __init__(self,sketch_type,data):
        pass

# API Wrappers ====================================================================================

class BusTrackerAPI:
    """
    # BusTracker

    Interface with CTA's BusTrackerAPI to display busses, routes, and other information from the transit system in an easy-to-read format
    """
    def __init__(self):
        self.__stop_reference = get_stops()

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

    def vehicles(self,vid=None,rt=None,tmres='m') -> pd.DataFrame:
        """
        Returns dataframe of the geolocations for each vehicle along the route

        Params
        ------
        - 
        """
        params = {
            "key":CTA_BUS_API_KEY if dt.datetime.now().time() < dt.time(16,0,0) else ALT_BUS_API_KEY,
            "format":"json"
        }

        if vid is not None:
            params["vid"] = vid
        elif rt is not None:
            params["rt"] = rt
        else:
            print("must use one of the following params - 'vid', 'rt'")
            return None

        url = CTA_BUS_BASE + "/getvehicles"
        response = requests.get(url,params=params)
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
                v.get("tablockid"),
                v.get("zone")]
            
            data.append(row_data)
        df = pd.DataFrame(data=data,columns=VEHICLE_COLS.values())
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

        url = CTA_BUS_BASE + f"/getpredictions"

        response = requests.get(url,params=params)
        data = []
        for p in response.json()["bustime-response"]["prd"]:
            row_data = []
            for col in PREDICTION_COLS:
                if col != "tmstmp":
                    row_data.append(p.get(col))
                else:
                    try:row_data.append(p.get(col))
                    except:row_data.append(p.get(col))
            data.append(row_data)
        
        # if sort_by is None:
        #     pass
        # elif sort_by == "vehicle" or sort_by == "vid":
        #     df.sort_values(by="vid",ascending=True,inplace=True)
        # elif sort_by == "stpid" or sort_by == "stop_id":
        #     df.sort_values(by="stpid",ascending=True,inplace=True)
        # elif sort_by == "stpnm" or sort_by == "stop_name" or sort_by == "stop":
        #     df.sort_values(by="stop",ascending=True,inplace=True)

        return pd.DataFrame(data=data,columns=PREDICTION_COLS.values()).sort_values(by=["vehicle_id","time_rem"],ascending=[True,True])

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

    def __patterns(self) -> list:
        """
        **NOT CONFIGURED YET\n
        Returns an array of python dictionary for the Bus route points which, when mapped, can construct the geo-positional layout of a 'route variation'
        """
        return self.__get_patterns()

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

class TrainTrackerAPI:
    """
    Wrapper for the CTA's "Train Tracker API"

    (NOT YET CONFIGURED)
    """
    def __init__(self):
        pass

class CustomerAlertsAPI:
    """
    Wrapper for the CTA's "Customer Alerts API"

    (NOT YET CONFIGURED)
    """
    def __init__(self):
        url = CTA_ALERTS_BASE + "/routes.aspx?outputType=json"
        url = CTA_ALERTS_BASE + "/alerts.aspx?outputType=json"

class TransitData:
    """
    Interact with CTA Ridership Data API (powered by Socrata)
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

# =================================================================================================

def stop_search(query,hide_desc_col=True) -> pd.Series | pd.DataFrame:
    """
    Search for a CTA stop/station by name.
    """
    df = get_stops()
    q = query.lower().replace("and","&")
    if "&" in q:
        q_list = str(q).split("&")
        street1 = q_list[0].strip()
        street2 = q_list[1].strip()
        results = []
        for idx,s in enumerate(df.stop_name):
            if street1 in str(s).lower() and street2 in str(s).lower():
                results.append(df.iloc[idx])
        if hide_desc_col is True:
            return pd.DataFrame(results).drop(columns=["stop_desc"])
        else:
            return pd.DataFrame(results)
    
    results = []
    for idx,s in enumerate(df.stop_name):
        if q in str(s).lower():
            results.append(df.iloc[idx])
    if hide_desc_col is True:
        return pd.DataFrame(results).drop(columns=["stop_desc"])
    else:
        return pd.DataFrame(results)

def route_transfers() -> pd.DataFrame:
    """
    Returns a dataframe of transfer details for each route & stop(/or station)

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
            v.get("tablockid","-"),
            v.get("zone","")]
        
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
    
def train_stations(hide_desc_col=True) -> pd.DataFrame:
    """Returns dataframe of train stations provided by the City of Chicago's transit database via JSON url"""
    df = get_train_stations()
    if hide_desc_col is True:
        return df.drop(columns=["station_descriptive_name"])
    else:
        return df

def train_arrivals(self,stpid_or_mapid=None) -> pd.DataFrame:
    """
    (Not properly configured yet)
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

def train_positions(self) -> pd.DataFrame:
    """
    (Not properly configured yet)
    Gets the current position of every vehicle for this CTA Line
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

def train_follow(self,rn,hide_desc_col=True) -> pd.DataFrame:
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
