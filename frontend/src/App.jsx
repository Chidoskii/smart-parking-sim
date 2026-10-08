import { useEffect, useState } from "react";
import { getHealth } from "./services/api";

import ParkingMap from "./components/Map/ParkingMap";
import ParkingLotDashboard from "./components/ParkingLotDashboard";

function App() {
  const [backendStatus, setBackendStatus] = useState("Checking...");
  const [error, setError] = useState("");

  useEffect(() => {
    async function checkBackend() {
      try {
        const data = await getHealth();
        setBackendStatus(data.status);
      } catch (err) {
        setError(err.message);
      }
    }

    checkBackend();
  }, []);

  return (
    <main>
      <h1>Smart Parking Simulation</h1>

      <ParkingLotDashboard />
      <ParkingMap />

      {error ? (
        <p>Backend error: {error}</p>
      ) : (
        <p>Backend status: {backendStatus}</p>
      )}
    </main>
  );
}

export default App;
