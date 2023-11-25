
function fetchNearbyStops() {
    fetch("/api/stoplist?", {
        method: "POST", 
        body: JSON.stringify({
            "lat": `${document.getElementById("lat").textContent}`,
            "lon": `${document.getElementById("lon").textContent}`,

        }),
        headers: {
            "Content-Type": "application/json"
        }
    })
    .then((response) => { 
        console.log(response); 
        return response.json();
    })
    .then(data => {
        console.log(data)
        document.getElementById("stoplist").innerHTML = data["stoplist_html"]
    })
}

if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(function(position) {
        document.getElementById("lat").textContent = position.coords.latitude
        document.getElementById("lon").textContent = position.coords.longitude
    })
}

document.getElementById("nearby-stops-btn").addEventListener("click", function(e) {
    fetchNearbyStops()
})

function trackStop(stop_id) {
    
}