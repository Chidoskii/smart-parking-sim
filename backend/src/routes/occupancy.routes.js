const express = require("express");

const {
  getAreaOccupancy,
  updateAreaOccupancy,
  getLotOccupancy,
  getAllLotOccupancy,
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

module.exports = router;
