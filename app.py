from flask import request
from flask.app import Flask
from flask.json import jsonify
from flask.templating import render_template
from flask.helpers import url_for
from flask_assets import Environment, Bundle

from cta import train, bus
from cta.static import StopType
from cta.static import closest_stops
from cta.static import get_db_connection
from helpers import add_supplementary_keys

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

assets = Environment(app)
scss = Bundle('style.scss',filters='pyscss',output='style.css')
assets.register('style',scss)

@app.context_processor
def inject_dict_for_all_templates():
    return {}

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/api/stoplist",methods=["GET","POST"])
def api_stoplist():
    lat = float(request.json.get("lat"))
    lon = float(request.json.get("lon"))
    
    all_stops = []
    
    # Bus stops
    bus_stops = closest_stops(lat, lon, number=3, stop_type="Bus")
    stop_ids = ",".join([f"{s['stop_id']}" for s in bus_stops])
    conn = get_db_connection("cta.db")
    c = conn.execute(f"SELECT stop_id, trip_id FROM stop_times WHERE stop_id IN ({stop_ids})")
    trip_ids = c.fetchall()
    stops_at_trips = {i[1]: [] for i in trip_ids}
    for i in trip_ids:
        stops_at_trips[i[1]].append(i[0])
    
    routes_at_stop = {i['stop_id']: [] for i in bus_stops}
    for trip_id, stop_ids in stops_at_trips.items():
        c.execute("SELECT route_id FROM trips WHERE trip_id=?",[trip_id])
        route_id = c.fetchone()[0]
        for stop_id in stop_ids:
            if route_id not in routes_at_stop[stop_id]:
                routes_at_stop[stop_id].append(route_id)
    
    all_stops.extend(add_supplementary_keys(bus_stops))
    
    # Train ("L") stops
    train_stops = closest_stops(lat, lon, number=3, stop_type="Train", group_child_stops=True)
    all_stops.extend(add_supplementary_keys(train_stops))
    
    stoplist_html = render_template("snippets/stoplist.html", all_stops=all_stops, routes_at_stop=routes_at_stop)
    
    return jsonify({
        "all_stops": all_stops, 
        "bus_stops": bus_stops, 
        "train_stops": train_stops, 
        "stoplist_html": stoplist_html
    })

@app.route("/api/tracking/stop",methods=["GET"])
def api_trackstop():
    stop_id = request.args.get("stop_id")

if __name__ == "__main__":
    app.run("127.0.0.1",port=5000,debug=True)
