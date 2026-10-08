const express = require("express");
const cors = require("cors");
const http = require("http");
const { Server } = require("socket.io");
const spacesRoutes = require("./routes/spaces.routes");
const parkingAreasRoutes = require("./routes/parkingAreas.routes");

require("dotenv").config();

const app = express();

app.use(cors());
app.use(express.json());
app.use("/api/spaces", spacesRoutes);
app.use("/api/parking-areas", parkingAreasRoutes);

app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    service: "smart-parking-backend",
  });
});

const server = http.createServer(app);

const io = new Server(server, {
  cors: {
    origin: "http://localhost:5173",
    methods: ["GET", "POST"],
  },
});

app.set("io", io);

io.on("connection", (socket) => {
  console.log(`Client connected: ${socket.id}`);

  socket.on("disconnect", () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
});

const PORT = process.env.PORT || 5000;

server.listen(PORT, () => {
  console.log(`Backend running on port ${PORT}`);
});
