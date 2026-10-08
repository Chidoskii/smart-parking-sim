import { useEffect, useRef, useState } from "react";
import { Map, Popup } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import socket from "../../services/socket";

function ParkingMap() {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);
  const parkingAreasRef = useRef(null);

  const [selectedLot, setSelectedLot] = useState("all");

  useEffect(() => {
    const map = new Map({
      container: mapContainer.current,
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [-117.819, 34.056],
      zoom: 15,
    });

    mapRef.current = map;

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

      const areasResponse = await fetch(
        "http://localhost:5000/api/parking-areas/geojson",
      );

      if (!areasResponse.ok) {
        throw new Error("Unable to fetch parking areas");
      }

      const areasData = await areasResponse.json();
      parkingAreasRef.current = areasData;

      map.addSource("parking-areas", {
        type: "geojson",
        data: areasData,
      });

      map.addLayer({
        id: "parking-area-labels",
        type: "symbol",
        source: "parking-areas",
        minzoom: 16,
        layout: {
          "text-field": ["get", "id"],
          "text-size": 12,
          "text-anchor": "bottom",
          "text-offset": [0, -0.6],
          "text-allow-overlap": false,
        },
        paint: {
          "text-color": "#111827",
          "text-halo-color": "#ffffff",
          "text-halo-width": 2,
        },
      });

      map.on("click", "parking-area-labels", (event) => {
        const feature = event.features?.[0];
        if (!feature) return;

        const properties = feature.properties;
        const container = document.createElement("div");

        const heading = document.createElement("strong");
        heading.textContent = properties.id;

        const details = document.createElement("p");
        details.textContent =
          `Lane: ${properties.lane} | ` +
          `Capacity: ${properties.roadsideCapacity} | ` +
          `Explicit spaces: ${properties.explicitSpaceCount}`;

        container.append(heading, details);

        new Popup().setLngLat(event.lngLat).setDOMContent(container).addTo(map);
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
      mapRef.current = null;
      parkingAreasRef.current = null;
      map.remove();
    };
  }, []);

  const handleLotChange = (lotId) => {
    setSelectedLot(lotId);

    const map = mapRef.current;
    const parkingAreas = parkingAreasRef.current;

    if (!map || !parkingAreas) return;

    const source = map.getSource("parking-areas");

    if (!source) return;

    const filteredFeatures =
      lotId === "all"
        ? parkingAreas.features
        : parkingAreas.features.filter(
            (feature) => feature.properties.campusLot === lotId,
          );

    source.setData({
      ...parkingAreas,
      features: filteredFeatures,
    });
  };

  return (
    <div>
      <div style={{ marginBottom: "12px" }}>
        <label htmlFor="parking-lot-filter">Parking Lot: </label>

        <select
          id="parking-lot-filter"
          value={selectedLot}
          onChange={(event) => handleLotChange(event.target.value)}
        >
          <option value="all">All Parking Areas</option>
          <option value="J">Parking Lot J</option>
          <option value="M">Parking Lot M</option>
          <option value="PS1">Parking Structure 1</option>
          <option value="F2">Parking Lot F2</option>
        </select>
      </div>

      <div
        ref={mapContainer}
        style={{
          width: "100%",
          height: "600px",
        }}
      />
    </div>
  );
}

export default ParkingMap;
