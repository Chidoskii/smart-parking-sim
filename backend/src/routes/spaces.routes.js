const express = require("express");
const fs = require("fs");
const path = require("path");

const router = express.Router();

const geojsonPath = path.resolve(
  __dirname,
  "../../../shared/geojson/parking-spaces.geojson",
);

const parkingData = JSON.parse(fs.readFileSync(geojsonPath, "utf-8"));

// Get all parking spaces as GeoJSON
router.get("/geojson", (req, res) => {
  res.json(parkingData);
});

// Update one parking space
router.post("/:spaceId/status", (req, res) => {
  const { spaceId } = req.params;
  const { status } = req.body;

  if (!["available", "occupied"].includes(status)) {
    return res.status(400).json({
      error: "Status must be 'available' or 'occupied'",
    });
  }

  const feature = parkingData.features.find(
    (space) => space.properties.id === spaceId,
  );

  if (!feature) {
    return res.status(404).json({
      error: "Parking space not found",
    });
  }

  feature.properties.status = status;

  const io = req.app.get("io");

  io.emit("parking-space-updated", {
    spaceId,
    status,
  });

  res.json({
    spaceId,
    status,
  });
});

module.exports = router;
