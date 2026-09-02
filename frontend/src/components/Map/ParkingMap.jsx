import { useEffect, useRef } from "react";
import { Map, Popup } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import socket from "../../services/socket";

function ParkingMap() {
  const mapContainer = useRef(null);

  useEffect(() => {
    const map = new Map({
      container: mapContainer.current,
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [-117.819, 34.056],
      zoom: 15,
    });

    map.on("load", async () => {
      const response = await fetch("http://localhost:5000/api/spaces/geojson");

      const parkingData = await response.json();

      map.addSource("parking-spaces", {
        type: "geojson",
        data: parkingData,
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

      map.on("click", "parking-spaces", (event) => {
        const feature = event.features?.[0];

        if (!feature) {
          return;
        }

        const properties = feature.properties;

        new Popup()
          .setLngLat(event.lngLat)
          .setHTML(
            `
            <strong>${properties.id}</strong><br />
            Parking Area: ${properties.parkingAreaId}<br />
            Status: ${properties.status}<br />
            SUMO X: ${properties.sumoX}<br />
            SUMO Y: ${properties.sumoY}
          `,
          )
          .addTo(map);
      });

      map.on("mouseenter", "parking-spaces", () => {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", "parking-spaces", () => {
        map.getCanvas().style.cursor = "";
      });

      socket.on("parking-space-updated", ({ spaceId, status }) => {
        const feature = parkingData.features.find(
          (space) => space.properties.id === spaceId,
        );

        if (!feature) {
          return;
        }

        feature.properties.status = status;

        const source = map.getSource("parking-spaces");

        if (source) {
          source.setData(parkingData);
        }
      });
    });

    return () => {
      socket.off("parking-space-updated");
      map.remove();
    };
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
