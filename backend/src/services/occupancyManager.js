const fs = require("fs");
const path = require("path");

const capacityPath = path.resolve(
  __dirname,
  "../../../shared/config/parking-capacity.json",
);

const scenarioPath = process.env.PARKING_SCENARIO_FILE;

const capacityData = JSON.parse(fs.readFileSync(capacityPath, "utf8"));

const scenarioData = scenarioPath
  ? JSON.parse(fs.readFileSync(path.resolve(scenarioPath), "utf8"))
  : null;

console.log("Parking scenario path:", scenarioPath || "DEFAULT");
console.log("Scenario loaded:", scenarioData !== null);

if (scenarioData) {
  console.log("Scenario:", scenarioData.scenario);
  console.log(
    "Modeled initial occupancy:",
    scenarioData.modeled_initial_occupied,
  );
}

const occupancy = new Map();

for (const areaId of Object.keys(capacityData.areas)) {
  occupancy.set(areaId, 0);
}

function getCapacity(areaId) {
  const area = capacityData.areas[areaId];

  if (!area) {
    throw new Error(`Unknown parking area: ${areaId}`);
  }

  if (!scenarioData) {
    return {
      physicalCapacity: area.capacity,
      initialOccupied: 0,
      effectiveCapacity: area.capacity,
    };
  }

  const scenarioArea = scenarioData.areas[areaId];

  if (!scenarioArea) {
    throw new Error(`Missing scenario area: ${areaId}`);
  }

  return {
    physicalCapacity: scenarioArea.physical_capacity,
    initialOccupied: scenarioArea.modeled_initial_occupied,
    effectiveCapacity: scenarioArea.effective_capacity,
  };
}

function getAreaOccupancy(areaId) {
  const { physicalCapacity, initialOccupied, effectiveCapacity } =
    getCapacity(areaId);

  const simulatedOccupied = occupancy.get(areaId);
  const occupied = initialOccupied + simulatedOccupied;

  return {
    id: areaId,
    capacity: physicalCapacity,
    effectiveCapacity,
    initialOccupied,
    simulatedOccupied,
    occupied,
    available: Math.max(0, effectiveCapacity - simulatedOccupied),
    occupancyRate:
      physicalCapacity > 0 ? (occupied / physicalCapacity) * 100 : 0,
  };
}

function updateAreaOccupancy(areaId, occupied) {
  const { effectiveCapacity } = getCapacity(areaId);

  if (
    !Number.isInteger(occupied) ||
    occupied < 0 ||
    occupied > effectiveCapacity
  ) {
    throw new Error(
      `Invalid occupancy for ${areaId}. Must be between 0 and ${effectiveCapacity}`,
    );
  }

  occupancy.set(areaId, occupied);
  return getAreaOccupancy(areaId);
}

function getAllAreaOccupancy() {
  return {
    areas: Object.keys(capacityData.areas).map(getAreaOccupancy),
  };
}

function getLotOccupancy(lotId) {
  const lot = capacityData.lots[lotId];

  if (!lot) {
    throw new Error(`Unknown parking lot: ${lotId}`);
  }

  const areas = lot.parkingAreas.map(getAreaOccupancy);

  const capacity = areas.reduce((sum, area) => sum + area.capacity, 0);

  const occupied = areas.reduce((sum, area) => sum + area.occupied, 0);

  return {
    id: lotId,
    name: lot.name,
    capacity,
    occupied,
    available: capacity - occupied,
    occupancyRate: capacity > 0 ? (occupied / capacity) * 100 : 0,
    parkingAreaCount: areas.length,
  };
}

function getAllLotOccupancy() {
  const lots = Object.keys(capacityData.lots).map(getLotOccupancy);

  const totalCapacity = lots.reduce((sum, lot) => sum + lot.capacity, 0);

  const totalOccupied = lots.reduce((sum, lot) => sum + lot.occupied, 0);

  return {
    totalCapacity,
    totalOccupied,
    totalAvailable: totalCapacity - totalOccupied,
    lots,
  };
}

module.exports = {
  getAreaOccupancy,
  getAllAreaOccupancy,
  updateAreaOccupancy,
  getLotOccupancy,
  getAllLotOccupancy,
};
