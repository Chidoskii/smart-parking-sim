import { useEffect, useRef, useState } from "react";
import { Map as MapLibreMap, Popup } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import socket from "../../services/socket";
import "./ParkingMap.css";

function createVehicleGeoJSON(vehicles) {
  return {
    type: "FeatureCollection",
    features: vehicles
      .filter(
        (vehicle) =>
          Number.isFinite(vehicle.longitude) &&
          Number.isFinite(vehicle.latitude),
      )
      .map((vehicle) => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [vehicle.longitude, vehicle.latitude],
        },
        properties: {
          id: vehicle.id,
          speed: vehicle.speed,
          angle: Number(vehicle.angle) || 0,
          roadId: vehicle.roadId,
          moving: vehicle.speed > 0.5,
        },
      })),
  };
}

function tintColor(hex, amt) {
  const h = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  const c = (v) => Math.max(0, Math.min(255, v + amt));
  return `rgb(${c(r)},${c(g)},${c(b)})`;
}

function createCarIcon(bodyColor) {
  const W = 64,
    H = 96;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");

  const dark = tintColor(bodyColor, -30);
  const slightly = tintColor(bodyColor, -12);

  // Car body path (reused for multiple draws)
  function bodyPath() {
    ctx.beginPath();
    ctx.moveTo(22, 8);
    ctx.bezierCurveTo(22, 6, 42, 6, 42, 8); // front bumper
    ctx.bezierCurveTo(50, 10, 52, 18, 50, 26); // front-right fender flare
    ctx.lineTo(50, 60);
    ctx.bezierCurveTo(52, 68, 50, 76, 42, 88); // rear-right fender
    ctx.bezierCurveTo(42, 90, 22, 90, 22, 88); // rear bumper
    ctx.bezierCurveTo(14, 76, 12, 68, 14, 60); // rear-left fender
    ctx.lineTo(14, 26);
    ctx.bezierCurveTo(12, 18, 14, 10, 22, 8); // front-left fender flare
    ctx.closePath();
  }

  // 1. Drop shadow
  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,0.38)";
  ctx.shadowBlur = 8;
  ctx.shadowOffsetX = 1;
  ctx.shadowOffsetY = 4;
  ctx.fillStyle = "rgba(0,0,0,0.01)";
  bodyPath();
  ctx.fill();
  ctx.restore();

  // 2. Tires (drawn before body so body overlaps them slightly)
  function drawTire(x, y, w, h) {
    ctx.fillStyle = "#1c1c1e";
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 4);
    ctx.fill();
    ctx.fillStyle = "#8d8d93";
    ctx.beginPath();
    ctx.roundRect(x + 2, y + 2, w - 4, h - 4, 3);
    ctx.fill();
    ctx.fillStyle = "#3a3a3c";
    ctx.beginPath();
    ctx.roundRect(x + 4, y + 4, w - 8, h - 8, 2);
    ctx.fill();
    ctx.fillStyle = "#c7c7cc";
    ctx.beginPath();
    ctx.arc(x + w / 2, y + h / 2, 2, 0, Math.PI * 2);
    ctx.fill();
  }
  drawTire(3, 16, 14, 20);
  drawTire(47, 16, 14, 20);
  drawTire(3, 60, 14, 20);
  drawTire(47, 60, 14, 20);

  // 3. Body fill
  ctx.fillStyle = bodyColor;
  bodyPath();
  ctx.fill();

  // 4. Hood (slightly darker)
  ctx.fillStyle = slightly;
  ctx.beginPath();
  ctx.moveTo(22, 8);
  ctx.bezierCurveTo(22, 6, 42, 6, 42, 8);
  ctx.bezierCurveTo(50, 10, 52, 18, 50, 26);
  ctx.lineTo(14, 26);
  ctx.bezierCurveTo(12, 18, 14, 10, 22, 8);
  ctx.closePath();
  ctx.fill();

  // 5. Front windshield (large and prominent)
  ctx.fillStyle = dark;
  ctx.beginPath();
  ctx.moveTo(18, 27);
  ctx.lineTo(46, 27);
  ctx.lineTo(44, 49);
  ctx.lineTo(20, 49);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "#bae6fd";
  ctx.globalAlpha = 0.92;
  ctx.beginPath();
  ctx.moveTo(20, 29);
  ctx.lineTo(44, 29);
  ctx.lineTo(42, 47);
  ctx.lineTo(22, 47);
  ctx.closePath();
  ctx.fill();
  ctx.globalAlpha = 1;

  // Glass glare
  ctx.fillStyle = "rgba(255,255,255,0.48)";
  ctx.beginPath();
  ctx.moveTo(21, 30);
  ctx.lineTo(31, 30);
  ctx.lineTo(29, 40);
  ctx.lineTo(21, 40);
  ctx.closePath();
  ctx.fill();

  // 6. Roof panel
  ctx.fillStyle = dark;
  ctx.beginPath();
  ctx.roundRect(19, 49, 26, 10, 3);
  ctx.fill();

  // 7. Rear windshield
  ctx.fillStyle = dark;
  ctx.beginPath();
  ctx.moveTo(18, 59);
  ctx.lineTo(46, 59);
  ctx.lineTo(44, 74);
  ctx.lineTo(20, 74);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "#1e3a8a";
  ctx.globalAlpha = 0.88;
  ctx.beginPath();
  ctx.moveTo(20, 61);
  ctx.lineTo(44, 61);
  ctx.lineTo(42, 72);
  ctx.lineTo(22, 72);
  ctx.closePath();
  ctx.fill();
  ctx.globalAlpha = 1;

  ctx.fillStyle = "rgba(255,255,255,0.15)";
  ctx.beginPath();
  ctx.moveTo(21, 62);
  ctx.lineTo(27, 62);
  ctx.lineTo(26, 68);
  ctx.lineTo(21, 68);
  ctx.closePath();
  ctx.fill();

  // 8. Trunk panel
  ctx.fillStyle = slightly;
  ctx.beginPath();
  ctx.moveTo(20, 75);
  ctx.lineTo(44, 75);
  ctx.bezierCurveTo(50, 76, 50, 84, 42, 88);
  ctx.bezierCurveTo(42, 90, 22, 90, 22, 88);
  ctx.bezierCurveTo(14, 84, 14, 76, 20, 75);
  ctx.closePath();
  ctx.fill();

  // 9. Side mirrors
  ctx.fillStyle = dark;
  ctx.beginPath();
  ctx.roundRect(7, 33, 7, 5, 2);
  ctx.fill();
  ctx.beginPath();
  ctx.roundRect(50, 33, 7, 5, 2);
  ctx.fill();
  ctx.fillStyle = "rgba(186,230,253,0.5)";
  ctx.beginPath();
  ctx.roundRect(8, 34, 5, 3, 1);
  ctx.fill();
  ctx.beginPath();
  ctx.roundRect(51, 34, 5, 3, 1);
  ctx.fill();

  // 10. Headlights
  ctx.fillStyle = "#fef9c3";
  ctx.beginPath();
  ctx.roundRect(18, 10, 9, 6, 2);
  ctx.fill();
  ctx.beginPath();
  ctx.roundRect(37, 10, 9, 6, 2);
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.ellipse(21, 12, 2.5, 1.5, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(42, 12, 2.5, 1.5, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(253,224,71,0.7)";
  ctx.lineWidth = 1.5;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(20, 17);
  ctx.lineTo(44, 17);
  ctx.stroke();

  // 11. Taillights
  ctx.fillStyle = "#fca5a5";
  ctx.beginPath();
  ctx.roundRect(18, 80, 9, 6, 2);
  ctx.fill();
  ctx.beginPath();
  ctx.roundRect(37, 80, 9, 6, 2);
  ctx.fill();
  ctx.fillStyle = "#ef4444";
  ctx.beginPath();
  ctx.roundRect(19, 81, 7, 4, 1);
  ctx.fill();
  ctx.beginPath();
  ctx.roundRect(38, 81, 7, 4, 1);
  ctx.fill();
  ctx.strokeStyle = "rgba(239,68,68,0.6)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(20, 80);
  ctx.lineTo(44, 80);
  ctx.stroke();

  // 12. Body outline
  ctx.strokeStyle = "rgba(255,255,255,0.35)";
  ctx.lineWidth = 1.2;
  bodyPath();
  ctx.stroke();

  return ctx.getImageData(0, 0, W, H);
}

function ParkingMap() {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);
  const parkingAreasRef = useRef(null);
  const parkingSpacesRef = useRef(null);
  const occupancyRef = useRef(new Map());
  const selectedLotRef = useRef("all");
  const vehiclesRef = useRef([]);

  const [selectedLot, setSelectedLot] = useState("all");

  const refreshParkingSpaces = () => {
    const map = mapRef.current;
    const parkingData = parkingSpacesRef.current;

    if (!map || !parkingData) return;

    const grouped = new Map();

    for (const feature of parkingData.features) {
      const areaId = feature.properties.parkingAreaId;

      if (!grouped.has(areaId)) {
        grouped.set(areaId, []);
      }

      grouped.get(areaId).push(feature);
    }

    for (const [areaId, features] of grouped) {
      const occupied = occupancyRef.current.get(areaId);

      if (occupied === undefined) continue;

      features.sort((a, b) =>
        a.properties.id.localeCompare(b.properties.id, undefined, {
          numeric: true,
        }),
      );

      features.forEach((feature, index) => {
        feature.properties.status = index < occupied ? "occupied" : "available";
      });
    }

    const filteredFeatures =
      selectedLotRef.current === "all"
        ? parkingData.features
        : parkingData.features.filter(
            (feature) =>
              feature.properties.campusLot === selectedLotRef.current,
          );

    const source = map.getSource("parking-spaces");

    if (source) {
      source.setData({
        ...parkingData,
        features: filteredFeatures,
      });
    }
  };

  useEffect(() => {
    const map = new MapLibreMap({
      container: mapContainer.current,
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [-117.819, 34.056],
      zoom: 15,
    });

    mapRef.current = map;
    let receivedLiveVehicleUpdate = false;

    const handleVehiclePositions = ({ vehicles }) => {
      if (!Array.isArray(vehicles)) return;

      receivedLiveVehicleUpdate = true;
      vehiclesRef.current = vehicles;

      const source = map.getSource("vehicles");

      if (source) {
        source.setData(createVehicleGeoJSON(vehicles));
      }
    };

    socket.on("vehicle-positions-updated", handleVehiclePositions);

    fetch("http://localhost:5000/api/vehicles/positions")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Unable to fetch vehicle positions");
        }
        return response.json();
      })
      .then(({ vehicles }) => {
        if (receivedLiveVehicleUpdate || !Array.isArray(vehicles)) return;

        vehiclesRef.current = vehicles;

        const source = map.getSource("vehicles");
        if (source) {
          source.setData(createVehicleGeoJSON(vehicles));
        }
      })
      .catch((error) => console.error(error));

    map.on("load", async () => {
      const response = await fetch("http://localhost:5000/api/spaces/geojson");

      const parkingData = await response.json();
      parkingSpacesRef.current = parkingData;

      const occupancyResponse = await fetch(
        "http://localhost:5000/api/occupancy/areas",
      );

      if (!occupancyResponse.ok) {
        throw new Error("Unable to fetch parking occupancy");
      }

      const occupancyData = await occupancyResponse.json();

      for (const area of occupancyData.areas) {
        if (!occupancyRef.current.has(area.id)) {
          occupancyRef.current.set(area.id, area.occupied);
        }
      }

      map.addSource("parking-spaces", {
        type: "geojson",
        data: parkingData,
      });

      socket.on("parking-occupancy-updated", (payload) => {
        const area = payload.area;

        if (!area) return;

        const areaId = area.id ?? area.areaId ?? area.parkingAreaId;
        const occupied = Number(area.occupied);

        if (!areaId || !Number.isFinite(occupied)) return;

        occupancyRef.current.set(areaId, Math.max(0, occupied));

        refreshParkingSpaces();
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

      refreshParkingSpaces();

      map.addImage("car-moving", createCarIcon("#2563eb"), {
        pixelRatio: 2,
      });

      map.addImage("car-stopped", createCarIcon("#f59e0b"), {
        pixelRatio: 2,
      });

      map.addSource("vehicles", {
        type: "geojson",
        data: createVehicleGeoJSON(vehiclesRef.current),
      });

      map.addLayer({
        id: "vehicle-markers",
        type: "symbol",
        source: "vehicles",

        layout: {
          "icon-image": [
            "case",
            ["get", "moving"],
            "car-moving",
            "car-stopped",
          ],

          "icon-size": [
            "interpolate",
            ["linear"],
            ["zoom"],
            14,
            0.35,
            16,
            0.55,
            18,
            0.8,
            20,
            1.1,
          ],

          "icon-rotate": ["get", "angle"],
          "icon-rotation-alignment": "map",
          "icon-pitch-alignment": "map",

          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
        },
      });

      map.on("click", "vehicle-markers", (event) => {
        const feature = event.features?.[0];
        if (!feature) return;

        const properties = feature.properties;

        const container = document.createElement("div");

        const heading = document.createElement("strong");
        heading.textContent = properties.id;

        const details = document.createElement("p");
        const speedMph = (Number(properties.speed) * 2.23694).toFixed(1);

        details.textContent = `Speed: ${speedMph} mph | Road: ${properties.roadId}`;

        container.append(heading, details);

        new Popup().setLngLat(event.lngLat).setDOMContent(container).addTo(map);
      });

      map.on("mouseenter", "vehicle-markers", () => {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", "vehicle-markers", () => {
        map.getCanvas().style.cursor = "";
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
        const parkingData = parkingSpacesRef.current;

        if (!parkingData) return;

        const feature = parkingData.features.find(
          (space) => space.properties.id === spaceId,
        );

        if (!feature) return;

        feature.properties.status = status;

        refreshParkingSpaces();
      });
    });

    return () => {
      socket.off("parking-space-updated");
      socket.off("parking-occupancy-updated");
      socket.off("vehicle-positions-updated", handleVehiclePositions);

      parkingAreasRef.current = null;
      parkingSpacesRef.current = null;
      occupancyRef.current.clear();
      vehiclesRef.current = [];

      mapRef.current = null;
      map.remove();
    };
  }, []);

  const handleLotChange = (lotId) => {
    setSelectedLot(lotId);

    selectedLotRef.current = lotId;
    refreshParkingSpaces();

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
          className="parking-lot-select"
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

      <div ref={mapContainer} className="parking-map" />
    </div>
  );
}

export default ParkingMap;
