const express = require("express");

const {
  getAreaOccupancy,
  updateAreaOccupancy,
  getAllAreaOccupancy,
  getLotOccupancy,
  getAllLotOccupancy,
  loadScenario,
} = require("../services/occupancyManager");

const router = express.Router();

// GET /api/occupancy
router.get("/", (req, res) => {
  res.json(getAllLotOccupancy());
});

// GET /api/occupancy/lots/:lotId
router.get("/lots/:lotId", (req, res) => {
  try {
    const result = getLotOccupancy(req.params.lotId.toUpperCase());

    res.json(result);
  } catch (error) {
    res.status(404).json({ error: error.message });
  }
});

// GET /api/occupancy/areas
router.get("/areas", (req, res) => {
  res.json(getAllAreaOccupancy());
});

// GET /api/occupancy/areas/:areaId
router.get("/areas/:areaId", (req, res) => {
  try {
    res.json(getAreaOccupancy(req.params.areaId));
  } catch (error) {
    res.status(404).json({ error: error.message });
  }
});

// PATCH /api/occupancy/areas/:areaId
router.patch("/areas/:areaId", (req, res) => {
  try {
    const { occupied } = req.body;

    const area = updateAreaOccupancy(req.params.areaId, occupied);

    const result = getAllLotOccupancy();

    // Broadcast updated occupancy to connected clients.
    req.app.get("io").emit("parking-occupancy-updated", {
      area,
      lots: result.lots,
      totalOccupied: result.totalOccupied,
      totalAvailable: result.totalAvailable,
    });

    res.json(area);
  } catch (error) {
    const status = error.message.startsWith("Unknown") ? 404 : 400;

    res.status(status).json({ error: error.message });
  }
});

// POST /api/occupancy/scenario
// Load a parking scenario and reset simulated occupancy.
router.post("/scenario", (req, res) => {
  try {
    const { scenario } = req.body;

    const scenarioFiles = {
      normal_occupancy:
        "simulation/sumo/scenarios/normal_occupancy/occupancy_seed_42.json",
      high_occupancy:
        "simulation/sumo/scenarios/high_occupancy/occupancy_seed_42.json",
    };

    if (!Object.prototype.hasOwnProperty.call(scenarioFiles, scenario)) {
      return res.status(400).json({
        error: "Invalid parking scenario",
      });
    }

    const path = require("path");

    const filePath = path.resolve(
      __dirname,
      "../../..",
      scenarioFiles[scenario],
    );

    const result = loadScenario(filePath);

    req.app.get("io").emit("parking-occupancy-updated", {
      lots: result.lots,
      totalOccupied: result.totalOccupied,
      totalAvailable: result.totalAvailable,
      totalCapacity: result.totalCapacity,
    });

    res.json({
      success: true,
      scenario,
      ...result,
    });
  } catch (error) {
    console.error("Failed to load parking scenario:", error);
    res.status(400).json({ error: error.message });
  }
});

module.exports = router;
