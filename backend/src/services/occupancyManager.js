const fs = require("fs");
const path = require("path");

const capacityPath = path.resolve(
  __dirname,
  "../../../shared/config/parking-capacity.json",
);

const capacityData = JSON.parse(fs.readFileSync(capacityPath, "utf8"));

// In-memory occupancy state.
// Initially, all areas are assumed empty for testing.
const occupancy = new Map();

for (const areaId of Object.keys(capacityData.areas)) {
  occupancy.set(areaId, 0);
}

function getAreaOccupancy(areaId) {
  const area = capacityData.areas[areaId];

  if (!area) {
    throw new Error(`Unknown parking area: ${areaId}`);
  }

  const occupied = occupancy.get(areaId);
  const capacity = area.capacity;

  return {
    id: areaId,
    capacity,
    occupied,
    available: capacity - occupied,
    occupancyRate: capacity > 0 ? (occupied / capacity) * 100 : 0,
  };
}

function updateAreaOccupancy(areaId, occupied) {
  const area = capacityData.areas[areaId];

  if (!area) {
    throw new Error(`Unknown parking area: ${areaId}`);
  }

  if (!Number.isInteger(occupied) || occupied < 0 || occupied > area.capacity) {
    throw new Error(
      `Invalid occupancy for ${areaId}. Must be between 0 and ${area.capacity}`,
    );
  }

  occupancy.set(areaId, occupied);

  return getAreaOccupancy(areaId);
}

function getLotOccupancy(lotId) {
  const lot = capacityData.lots[lotId];

  if (!lot) {
    throw new Error(`Unknown parking lot: ${lotId}`);
  }

  const areas = lot.parkingAreas.map(getAreaOccupancy);

  const occupied = areas.reduce((sum, area) => sum + area.occupied, 0);

  return {
    id: lotId,
    name: lot.name,
    capacity: lot.capacity,
    occupied,
    available: lot.capacity - occupied,
    occupancyRate: lot.capacity > 0 ? (occupied / lot.capacity) * 100 : 0,
    parkingAreaCount: areas.length,
  };
}

function getAllLotOccupancy() {
  const lots = Object.keys(capacityData.lots).map(getLotOccupancy);

  const totalOccupied = lots.reduce((sum, lot) => sum + lot.occupied, 0);

  return {
    totalCapacity: capacityData.totalCapacity,
    totalOccupied,
    totalAvailable: capacityData.totalCapacity - totalOccupied,
    lots,
  };
}

module.exports = {
  getAreaOccupancy,
  updateAreaOccupancy,
  getLotOccupancy,
  getAllLotOccupancy,
};
