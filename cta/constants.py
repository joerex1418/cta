BUS_BASE = "https://www.ctabustracker.com/bustime/api/v2"

TRAIN_BASE = "http://lapi.transitchicago.com/api/1.0"

# I don't think an API key is needed for this endpoint...which is nice :)
ALERTS_BASE = "http://lapi.transitchicago.com/api/1.0"

# DATA_BASE = "https://data.cityofchicago.org/resource/6iiy-9s97.json?"

DIRECTIONS = {"N": "Northbound", "S": "Southbound", "E": "Eastbound", "W": "Westbound"}

STATIC_FILES = (
    "trips",
    "stops",
    "stop_times",
    "shapes",
    "routes",
    "frequencies",
    "calendar_dates",
    "transfers",
    "agency"
)

XFER_COLS = (
    "route_id", 
    "location_type", 
    "stop_name", 
    "stop_id", 
    "lat", 
    "lon", 
    "bearing", 
    "transfers"
)

PRD_TYPES = {
    "A":"arrival",
    "D":"departure"
}

ROUTE_COLS = {
    "rt": "route_id",
    "rtnm": "route_name",
    "rtclr": "route_color",
    "rtdd": "route_dd"
}

VEHICLE_COLS = {
    "vid":"vehicle_id",
    "tmstmp":"timestamp",
    "lat":"lat",
    "lon":"lon",
    "hdg":"heading",
    "pid":"pattern_id",
    "rt":"route",
    "des":"destination",
    "pdist":"distance",
    "dly":"delayed",
    "tatripid":"trip_id",
    "origtatripno": "original_trip_num",
    "tablockid":"block_id",
    "zone": "zone"
}

STOP_COLS = {
    "stpid":"stop_id",
    "stpnm":"stop",
    "lat":"lat",
    "lon":"lon"
}

PREDICTION_COLS = {
    "tmstmp":"timestamp",
    "typ":"type",
    "stpnm":"stop_name",
    "stpid":"stop_id",
    "vid":"vehicle_id",
    "dstp":"distance_remaining",
    "rt":"route",
    "rtdir":"direction",
    "des":"destination",
    "prdtm":"predicted_time",
    "prdctdn":"time_remaining",
    "tablockid":"block_id",
    "tatripid":"trip_id",
    "origtatripno": "original_trip_num",
    "dly":"delayed"
}

LINES = {
    "red":"Red",
    "r":"Red",
    "brown":"Brn",
    "br":"Brn",
    "blue":"Blue",
    "bl":"Blue",
    "green":"G",
    "g":"G",
    "orange":"Org",
    "o":"Org",
    "purpleexp":"Pexp",
    "pexp":"Pexp",
    "purple_express":"Pexp",
    "purple express":"Pexp",
    "purple_exp":"Pexp",
    "p express":"Pexp",
    "express":"Pexp",
    "p_exp":"Pexp",
    "exp":"Pexp",
    "express":"Pexp",
    "purple":"P",
    "pink":"Pink",
    "yellow":"Y",
    "y":"Y",
}

LINE_NAMES = {
    "Red":"Red Line",
    "Brn":"Brown Line",
    "Blue": "Blue Line",
    "G":"Green Line",
    "Org":"Orange Line",
    "Pexp":"Purple Line Express",
    "P":"Purple Line",
    "Pink":"Pink Line",
    "Y":"Yellow Line"
}

LINE_LABELS = {
    "Red":"Howard-95th/Dan Ryan",
    "Brn":"Kimball-Loop",
    "Blue": "O'Hare-Forest Park",
    "G":"Harlem/Lake-Ashland/63rd-Cottage Grove",
    "Org":"Midway-Loop",
    "Pexp":"Linden-Loop",
    "P":"Linden-Howard shuttle",
    "Pink":"54th/Cermak-Loop",
    "Y":"Skokie-Howard [Skokie Swift] shuttle"
}

LINE_COLORS = {
    "Red":"Red",
    "Brn":"Brown",
    "Blue": "Blue",
    "G":"Green",
    "Org":"Orange",
    "Pexp":"Purple",
    "P":"Purple",
    "Pink":"Pink",
    "Y":"Yellow"
}

COLOR_LABEL_LIST = ("red","blue","green","brown","purple","purple_exp","yellow","pink","orange")

L_ARRIVALS_COLS = (
    "stop_id",
    "stop_name",
    "map_id",
    "station_name",
    "station_desc",
    "run_num",
    "rt",
    "dest_stop",
    "dest_name",
    "trDr",
    "prdt_time",
    "eta",
    "eta_timestamp",
    "time_rem",
    "updated",
    "isApp",
    "isSch",
    "isDly",
    "isFlt",
    "flags",
    "lat",
    "lon",
    "heading")

L_FOLLOW_COLS = (
    "stop_id",
    "stop_lat",
    "stop_lon",
    "map_id",
    "station_name",
    "service_desc",
    "service_name",
    "run_num",
    "line_rt",
    "dest_map_id",
    "trDr",
    "prdt_time",
    "eta",
    "eta_timestamp",
    "time_rem",
    "last_updated",
    "isApp",
    "isSch",
    "isDly",
    "isFlt",
    "flags",
    "lat",
    "lon",
    "heading")

L_POSITIONS_COLS = (
    "line",
    "run_num",
    "dest_stop_id",
    "service_name",
    "next_map_id",
    "next_station_name",
    "next_stop_id",
    "trDr",
    "prdt_time",
    "eta",
    "due_in",
    "last_updated",
    "isApp",
    "isDly",
    "flags",
    "lat",
    "lon",
    "heading")

DIR_CODE_RLOOKUP = {
    "1":{
        "red":"Howard-bound",
        "blue":"O'Hare-bound",
        "brown":"Kimball-bound",
        "green":"Harlem/Lake-bound",
        "orange":"Loop-bound",
        "purple":"Linden-bound",
        "pink":"Loop-bound",
        "yellow":"Skokie-bound",
        "Red":"Howard-bound",
        "Blue":"O'Hare-bound",
        "Brn":"Kimball-bound",
        "G":"Harlem/Lake-bound",
        "Org":"Loop-bound",
        "P":"Linden-bound",
        "Pexp":"Linden-bound",
        "Pink":"Loop-bound",
        "Y":"Skokie-bound",
    },
    "5":{
        "red":"95th/Dan Ryan-bound",
        "blue":"Forest Park-bound",
        "brown":"Loop-bound",
        "green":"Ashland/63rd- or Cottage Grove-bound (toward 63rd St destinations)",
        "orange":"Midway-bound",
        "purple":"Howard- or Loop-bound",
        "pink":"54th/Cermak-bound",
        "yellow":"Howard-bound",
        "Red":"95th/Dan Ryan-bound",
        "Blue":"Forest Park-bound",
        "Brn":"Loop-bound",
        "G":"Ashland/63rd- or Cottage Grove-bound (toward 63rd St destinations)",
        "Org":"Midway-bound",
        "P":"Howard- or Loop-bound",
        "Pexp":"Loop-bound",
        "Pink":"54th/Cermak-bound",
        "Y":"Howard-bound",
    }}

DIR_CODE_LOOKUP = {
    "red":{
        "1":"Howard-bound",
        "5":"95th/Dan Ryan-bound"
    },
    "blue":{
        "1":"O'Hare-bound",
        "5":"Forest Park-bound"
    },
    "brown":{
        "1":"Kimball-bound",
        "5":"Loop-bound"
    },
    "green":{
        "1":"Harlem/Lake-bound",
        "5":"Ashland/63rd- or Cottage Grove-bound (toward 63rd St destinations)"
    },
    "orange":{
        "1":"Loop-bound",
        "5":"Midway-bound"
    },
    "purple":{
        "1":"Linden-bound",
        "5":"Howard- or Loop-bound"
    },
    "pink":{
        "1":"Loop-bound",
        "5":"54th/Cermak-bound"
    },
    "yellow":{
        "1":"Skokie-bound",
        "5":"Howard-bound"
    },
    "Red":{
        "1":"Howard-bound",
        "5":"95th/Dan Ryan-bound"
    },
    "Blue":{
        "1":"O'Hare-bound",
        "5":"Forest Park-bound"
    },
    "Brn":{
        "1":"Kimball-bound",
        "5":"Loop-bound"
    },
    "G":{
        "1":"Harlem/Lake-bound",
        "5":"Ashland/63rd- or Cottage Grove-bound (toward 63rd St destinations)"
    },
    "Org":{
        "1":"Loop-bound",
        "5":"Midway-bound"
    },
    "P":{
        "1":"Linden-bound",
        "5":"Howard- or Loop-bound"
    },
    "Pexp":{
        "1":"Linden-bound",
        "5":"Loop-bound"
    },
    "Pink":{
        "1":"Loop-bound",
        "5":"54th/Cermak-bound"
    },
    "Y":{
        "1":"Skokie-bound",
        "5":"Howard-bound"
    }}


