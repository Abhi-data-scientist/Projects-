const form = document.querySelector("#train-form");
const loading = document.querySelector("#loading");
const results = document.querySelector("#results");
const errorBox = document.querySelector("#error");
const submitButton = document.querySelector("#submit-button");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function formatValue(value) {
  if (typeof value === "number") return Number.isInteger(value) ? value : value.toFixed(4);
  return value ?? "—";
}

function renderTable(rows) {
  const table = document.querySelector("#leaderboard");
  const columns = [...new Set(rows.flatMap(Object.keys))];
  table.innerHTML = `
    <thead><tr>${columns.map(column => `<th>${column.replaceAll("_", " ")}</th>`).join("")}</tr></thead>
    <tbody>${rows.map(row => `<tr>${columns.map(column => `<td>${formatValue(row[column])}</td>`).join("")}</tr>`).join("")}</tbody>`;
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  errorBox.classList.add("hidden");
  results.classList.add("hidden");
  loading.classList.remove("hidden");
  submitButton.disabled = true;

  const formData = new FormData(form);
  formData.set("use_pca", document.querySelector("#use-pca").checked ? "true" : "false");
  try {
    const response = await fetch("/train", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Training failed.");

    document.querySelector("#best-model").textContent = `Best model: ${data.best_model}`;
    document.querySelector("#model-id").textContent = `Model ID: ${data.model_id}`;
    document.querySelector("#process-list").innerHTML = data.process.map(step => `<li>${step}</li>`).join("");
    renderTable(data.leaderboard);
    results.classList.remove("hidden");
  } catch (error) {
    showError(error.message);
  } finally {
    loading.classList.add("hidden");
    submitButton.disabled = false;
  }
});
