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
