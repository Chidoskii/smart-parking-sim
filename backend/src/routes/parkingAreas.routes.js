const express = require("express");
const fs = require("fs");
const path = require("path");

const router = express.Router();

const geojsonPath = path.resolve(
  __dirname,
  "../../../shared/geojson/parking-areas.geojson",
);

const configPath = path.resolve(
  __dirname,
  "../../../shared/config/parking-lots.json",
);

router.get("/geojson", (req, res) => {
  try {
    const parkingData = JSON.parse(fs.readFileSync(geojsonPath, "utf8"));

    const config = JSON.parse(fs.readFileSync(configPath, "utf8"));

    const areaToLot = {};

    for (const [lotId, lot] of Object.entries(config.lots)) {
      for (const areaId of lot.sumoParkingAreas) {
        areaToLot[areaId] = lotId;
      }
    }

    for (const feature of parkingData.features) {
      const areaId = feature.properties.id;

      feature.properties.campusLot = areaToLot[areaId] ?? null;
    }

    res.json(parkingData);
  } catch (error) {
    console.error("Failed to load parking areas:", error);

    res.status(500).json({
      error: "Unable to load parking areas",
    });
  }
});

module.exports = router;
