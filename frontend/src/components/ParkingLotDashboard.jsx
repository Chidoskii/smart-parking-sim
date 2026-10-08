import { useEffect, useState } from "react";
import "./ParkingLotDashboard.css";

function ParkingLotDashboard() {
  const [lots, setLots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchParkingLots() {
      try {
        const response = await fetch("http://localhost:5000/api/parking-lots", {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Failed to load parking lots");
        }

        const data = await response.json();
        setLots(data.lots);
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    fetchParkingLots();

    return () => controller.abort();
  }, []);

  if (loading) return <p>Loading parking information...</p>;
  if (error) return <p role="alert">{error}</p>;

  return (
    <section className="parking-dashboard">
      <h2>Campus Parking Capacity</h2>

      <div className="parking-dashboard-grid">
        {lots.map((lot) => (
          <article className="parking-lot-card" key={lot.id}>
            <h3>{lot.name}</h3>

            <p className="parking-lot-capacity">
              {lot.capacity.toLocaleString()}
            </p>

            <span>Declared parking spaces</span>
            <small>{lot.parkingAreaCount} SUMO parking areas</small>
          </article>
        ))}
      </div>
    </section>
  );
}

export default ParkingLotDashboard;
