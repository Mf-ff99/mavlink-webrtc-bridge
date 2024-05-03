var documentLoaded = false
var map

document.addEventListener('DOMContentLoaded', () => {
    documentLoaded = true
    
})

if (documentLoaded) {
    console.log('doc loaded')
    map = L.map('map').setView([0, 0], 10)
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map)
}
    
function updateMap(latitude, longitude) {
    if (!map) {
        console.error('Map is not initialized.');
        return;
    }

    // Clear previous markers
    map.eachLayer(function(layer) {
        if (layer instanceof L.Marker) {
            map.removeLayer(layer);
        }
    });

    // Add new marker with updated GPS coordinates
    L.marker([latitude, longitude]).addTo(map)
        .bindPopup('Drone Location').openPopup();

    // Pan the map to the new location
    map.panTo(new L.LatLng(latitude, longitude));
}

// export default updateMap()