qoinware = {};

qoinware.geo = {};

(function(geo) {
    geo.centre = new google.maps.LatLng(map_centre_lat, map_centre_lng);

    geo.cleanCoord = function(c) {
		return parseFloat((c+"").substring(0,14));
    };

    geo.FormMap = function(elem, lat, lng, zoom, settings) {
		var res = {};

		settings.zoom = (settings.zoom == null || typeof settings.zoom == 'undefined') ? 12 : settings.zoom;

		res.lat = $("[name=" + lat + "]");
		res.lng = $("[name=" + lng + "]");
		res.zoom = $("[name=" + zoom + "]");
		res.currentMarker = null;
		res.map = new google.maps.Map($('#' + elem).get(0), settings);
		res.map.setCenter(geo.centre);		

		// Make a new marker
		res.setMarker = function(loc) {
			// Get rid of the old marker
		    if (this.currentMarker) {
				this.currentMarker.setMap(null);
		    }

		    // Make the new one
		    res.currentMarker = new google.maps.Marker({
				position: loc,
				map: this.map
			});

		    // Set the form fields to have the new postion values
		    this.lat.val(geo.cleanCoord(loc.lat()));
		    this.lng.val(geo.cleanCoord(loc.lng()));
		    this.zoom.val(this.map.getZoom());
		}

		// If someone clicks the map, call setMarker with the latlng just clicked
		google.maps.event.addListener(res.map, 'click', function(event) {
		    res.setMarker(event.latLng);
		});

		// Make the map centre around the current co-ords
		res.centralize = function() {
		    var lat = parseFloat(this.lat.val()),
		    	lng = parseFloat(this.lng.val());

		    if (lat && lng) {
				var loc = new google.maps.LatLng(lat, lng);
				
				this.setMarker(loc);
				this.map.setCenter(loc);
		    }
		};

		res.centralize();

		return res;
	}
    
})(qoinware.geo);
