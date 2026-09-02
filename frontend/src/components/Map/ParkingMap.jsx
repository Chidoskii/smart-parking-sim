import { useEffect, useRef } from "react";
import { Map } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

function ParkingMap() {
  const mapContainer = useRef(null);

  useEffect(() => {
    const map = new Map({
      container: mapContainer.current,

      style: "https://tiles.openfreemap.org/styles/liberty",

      center: [-117.819, 34.056],
      zoom: 15,
    });

    map.on("load", () => {
      map.addSource("parking-spaces", {
        type: "geojson",
        data: "/geojson/parking-spaces.geojson",
      });

      map.addLayer({
        id: "parking-spaces",
        type: "fill",
        source: "parking-spaces",

        paint: {
          "fill-color": [
            "match",
            ["get", "status"],

            "available",
            "#22c55e",

            "occupied",
            "#ef4444",

            "#64748b",
          ],

          "fill-opacity": 0.8,
          "fill-outline-color": "#ffffff",
        },
      });
    });

    return () => map.remove();
  }, []);

  return (
    <div
      ref={mapContainer}
      style={{
        width: "100%",
        height: "600px",
      }}
    />
  );
}

export default ParkingMap;
