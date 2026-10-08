const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "../..");

const geojsonPath = path.join(root, "shared/geojson/parking-areas.geojson");

const outputPath = path.join(root, "shared/config/parking-lots.json");

const parkingAreas = JSON.parse(fs.readFileSync(geojsonPath, "utf8"));

const lotMAreas = [
  "hill_pa_96",
  "hill_pa_96a",
  "hill_pa_97",
  "hill_pa_97a",
  "hill_pa_98",
  "hill_pa_98a",
  "hill_pa_99",
  "hill_pa_99a",
  "hill_pa_100",
  "hill_pa_100a",
  "hill_pa_101",
  "hill_pa_101a",
  "hill_pa_104",
  "hill_pa_104a",
  "hill_pa_105",
  "hill_pa_105a",
  "hill_pa_107",
  "hill_pa_107a",
];

const allHillAreas = parkingAreas.features
  .map((feature) => feature.properties.id)
  .filter((id) => id.startsWith("hill_"));

const lotJAreas = allHillAreas.filter((id) => !lotMAreas.includes(id));

const parkingStructure1Areas = [
  "far_pa_3",
  "far_pa_4",
  "far_pa_5",
  "far_pa_6",
  "far_pa_7",
  "far_pa_8",
  "far_pa_9",
  "far_pa_10",
  "far_pa_11",
  "far_pa_12",
  "far_pa_13",
  "far_pa_17",
  "far_pa_19",
  "far_pa_20",
  "far_pa_21",
  "far_pa_24",
];

const allFarAreas = parkingAreas.features
  .map((feature) => feature.properties.id)
  .filter((id) => id.startsWith("far_"));

const lotF2Areas = allFarAreas.filter(
  (id) => !parkingStructure1Areas.includes(id),
);

const config = {
  lots: {
    J: {
      name: "Parking Lot J",
      sumoParkingAreas: lotJAreas,
      enabled: true,
    },
    M: {
      name: "Parking Lot M",
      sumoParkingAreas: lotMAreas,
      enabled: true,
    },
    PS1: {
      name: "Parking Structure 1",
      sumoParkingAreas: parkingStructure1Areas,
      enabled: true,
    },
    F2: {
      name: "Parking Lot F2",
      sumoParkingAreas: lotF2Areas,
      enabled: true,
    },
  },
};

fs.mkdirSync(path.dirname(outputPath), {
  recursive: true,
});

fs.writeFileSync(outputPath, JSON.stringify(config, null, 2));

console.log(`Lot J: ${lotJAreas.length} parking areas`);
console.log(`Lot M: ${lotMAreas.length} parking areas`);
console.log(
  `Parking Structure 1: ${parkingStructure1Areas.length} parking areas`,
);
console.log(`Lot F2: ${lotF2Areas.length} parking areas`);
