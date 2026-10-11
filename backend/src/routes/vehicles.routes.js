const express = require("express");

const router = express.Router();

let latestVehicles = [];

// GET /api/vehicles/positions
router.get("/positions", (req, res) => {
  res.json({ vehicles: latestVehicles });
});

// POST /api/vehicles/positions
router.post("/positions", (req, res) => {
  const { vehicles } = req.body;

  if (!Array.isArray(vehicles)) {
    return res.status(400).json({
      error: "vehicles must be an array",
    });
  }

  latestVehicles = vehicles;

  req.app.get("io").emit("vehicle-positions-updated", {
    vehicles: latestVehicles,
  });

  res.json({
    received: latestVehicles.length,
  });
});

module.exports = router;
