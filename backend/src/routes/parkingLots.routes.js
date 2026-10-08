const express = require("express");
const fs = require("fs");
const path = require("path");

const router = express.Router();

const capacityPath = path.resolve(
  __dirname,
  "../../../shared/config/parking-capacity.json",
);

// GET /api/parking-lots
router.get("/", (req, res) => {
  try {
    const capacityData = JSON.parse(fs.readFileSync(capacityPath, "utf8"));

    const lots = Object.entries(capacityData.lots).map(([id, lot]) => ({
      id,
      name: lot.name,
      capacity: lot.capacity,
      parkingAreaCount: lot.parkingAreas.length,
    }));

    res.json({
      totalCapacity: capacityData.totalCapacity,
      lots,
    });
  } catch (error) {
    console.error("Error loading parking lots:", error);

    res.status(500).json({
      error: "Failed to load parking lot information",
    });
  }
});

// GET /api/parking-lots/:lotId
router.get("/:lotId", (req, res) => {
  try {
    const capacityData = JSON.parse(fs.readFileSync(capacityPath, "utf8"));

    const lotId = req.params.lotId.toUpperCase();
    const lot = capacityData.lots[lotId];

    if (!lot) {
      return res.status(404).json({
        error: `Parking lot ${lotId} not found`,
      });
    }

    res.json({
      id: lotId,
      name: lot.name,
      capacity: lot.capacity,
      parkingAreaCount: lot.parkingAreas.length,
      parkingAreas: lot.parkingAreas,
    });
  } catch (error) {
    console.error("Error loading parking lot:", error);

    res.status(500).json({
      error: "Failed to load parking lot information",
    });
  }
});

module.exports = router;
