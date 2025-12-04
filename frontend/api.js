const API_BASE = "http://127.0.0.1:8000";

async function seedDemo() {
  const statusEl = document.getElementById("seed-status");
  statusEl.textContent = "Cargando datos de demo...";
  try {
    const res = await fetch(`${API_BASE}/demo/seed`, { method: "POST" });
    const data = await res.json();
    statusEl.textContent = `OK: ${data.message}`;
  } catch (err) {
    console.error(err);
    statusEl.textContent = "Error cargando datos de demo.";
  }
}

async function fetchRecommendations() {
  const userId = document.getElementById("user-id").value.trim();
  const kValue = document.getElementById("k").value.trim() || "5";
  const outputEl = document.getElementById("recs-output");

  if (!userId) {
    alert("Ingresá un user_id");
    return;
  }

  outputEl.textContent = "Buscando recomendaciones...";

  try {
    const res = await fetch(`${API_BASE}/recommendations/${encodeURIComponent(userId)}?k=${encodeURIComponent(kValue)}`);
    if (!res.ok) {
      const errData = await res.json();
      outputEl.textContent = `Error: ${res.status} - ${errData.detail || "error"}`;
      return;
    }
    const data = await res.json();
    outputEl.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    console.error(err);
    outputEl.textContent = "Error al obtener recomendaciones.";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("seed-btn").addEventListener("click", seedDemo);
  document.getElementById("recs-btn").addEventListener("click", fetchRecommendations);
});
