import { useEffect, useState } from "react";
import socket from "../services/socket";
import "./ParkingLotDashboard.css";

function ParkingLotDashboard() {
  const [lots, setLots] = useState([]);
  const [totals, setTotals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchOccupancy() {
      try {
        const response = await fetch("http://localhost:5000/api/occupancy", {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Failed to load parking occupancy");
        }

        const data = await response.json();

        setLots(data.lots);
        setTotals({
          capacity: data.totalCapacity,
          occupied: data.totalOccupied,
          available: data.totalAvailable,
        });
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

    function handleOccupancyUpdate(data) {
      setLots(data.lots);

      setTotals((previous) => ({
        capacity: previous?.capacity ?? 5975,
        occupied: data.totalOccupied,
        available: data.totalAvailable,
      }));
    }

    // Register the listener before fetching initial state.
    socket.on("parking-occupancy-updated", handleOccupancyUpdate);

    fetchOccupancy();

    return () => {
      controller.abort();
      socket.off("parking-occupancy-updated", handleOccupancyUpdate);
    };
  }, []);

  if (loading) return <p>Loading parking information...</p>;
  if (error) return <p role="alert">{error}</p>;

  return (
    <section className="parking-dashboard">
      <h2>Campus Parking Occupancy</h2>

      {totals && (
        <p className="parking-campus-summary">
          {totals.occupied.toLocaleString()} occupied /{" "}
          {totals.capacity.toLocaleString()} total spaces
        </p>
      )}

      <div className="parking-dashboard-grid">
        {lots.map((lot) => (
          <article className="parking-lot-card" key={lot.id}>
            <h3>{lot.name}</h3>

            <p className="parking-lot-capacity">
              {lot.available.toLocaleString()}
            </p>

            <span>Available spaces</span>

            <div
              className="parking-occupancy-track"
              role="progressbar"
              aria-label={`${lot.name} occupancy`}
              aria-valuenow={lot.occupied}
              aria-valuemin={0}
              aria-valuemax={lot.capacity}
            >
              <div
                className="parking-occupancy-fill"
                style={{
                  width: `${lot.occupancyRate}%`,
                }}
              />
            </div>

            <small>
              {lot.occupied.toLocaleString()} occupied of{" "}
              {lot.capacity.toLocaleString()}
            </small>

            <small>{lot.occupancyRate.toFixed(1)}% occupied</small>
          </article>
        ))}
      </div>
    </section>
  );
}

export default ParkingLotDashboard;
