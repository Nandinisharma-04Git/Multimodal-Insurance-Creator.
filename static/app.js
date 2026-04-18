const promptEl = document.getElementById("prompt");
const btnEl = document.getElementById("generateBtn");
const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const textOutEl = document.getElementById("textOut");
const imgOutEl = document.getElementById("imgOut");
const imgSkeletonEl = document.getElementById("imgSkeleton");
const chartsSectionEl = document.getElementById("chartsSection");
let barChartInstance = null, pieChartInstance = null, lineChartInstance = null;

const mRatingEl = document.getElementById("mRating");
const mPremiumEl = document.getElementById("mPremium");
const mCoverageEl = document.getElementById("mCoverage");
const mRiskEl = document.getElementById("mRisk");

function formatINR(n) {
  const x = Number(n);
  if (!Number.isFinite(x)) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(x);
}

function renderMetrics(metrics) {
  if (!metrics) return;
  if (mRatingEl) mRatingEl.textContent = metrics.rating ? `${metrics.rating} / 5` : "—";
  if (mPremiumEl) mPremiumEl.textContent = metrics.monthly_premium_est != null ? `₹ ${formatINR(metrics.monthly_premium_est)}` : "—";
  if (mCoverageEl) mCoverageEl.textContent = metrics.coverage_est != null ? `₹ ${formatINR(metrics.coverage_est)}` : "—";
  if (mRiskEl) mRiskEl.textContent = metrics.risk_score != null ? `${metrics.risk_score} / 100` : "—";
}

async function loadCharts(prompt) {
  const res = await fetch("/charts-data", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt })
  });
  const d = await res.json();

  chartsSectionEl.classList.remove("hidden");

  // Destroy old charts if re-generating
  if (barChartInstance) barChartInstance.destroy();
  if (pieChartInstance) pieChartInstance.destroy();
  if (lineChartInstance) lineChartInstance.destroy();

  // --- BAR CHART: Premium vs Coverage ---
  barChartInstance = new Chart(document.getElementById("barChart"), {
    type: "bar",
    data: {
      labels: d.premium_coverage.labels,
      datasets: [
        { label: "Annual Premium (₹)", data: d.premium_coverage.premium, backgroundColor: "#4f8ef7" },
        { label: "Coverage (₹)", data: d.premium_coverage.coverage, backgroundColor: "#34c98a" }
      ]
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } }
  });

  // --- PIE CHART: Type Breakdown ---
  pieChartInstance = new Chart(document.getElementById("pieChart"), {
    type: "pie",
    data: {
      labels: d.type_breakdown.labels,
      datasets: [{
        data: d.type_breakdown.values,
        backgroundColor: ["#4f8ef7","#f7914f","#34c98a","#f7d44f","#c084fc"]
      }]
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } }
  });

  // --- LINE CHART: Cost Over Time ---
  lineChartInstance = new Chart(document.getElementById("lineChart"), {
    type: "line",
    data: {
      labels: d.cost_over_time.years,
      datasets: [
        { label: "Basic", data: d.cost_over_time.basic, borderColor: "#4f8ef7", tension: 0.4, fill: false },
        { label: "Standard", data: d.cost_over_time.standard, borderColor: "#34c98a", tension: 0.4, fill: false },
        { label: "Premium", data: d.cost_over_time.premium, borderColor: "#f7914f", tension: 0.4, fill: false }
      ]
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } }
  });
}

function setStatus(message, kind = "ok") {
  statusEl.textContent = message || "";
  statusEl.classList.remove("ok", "error");
  if (message) statusEl.classList.add(kind);
}

function setLoading(isLoading) {
  btnEl.disabled = isLoading;
  btnEl.textContent = isLoading ? "Generating..." : "Generate";

  if (isLoading) {
    outputEl.classList.add("hidden");
    imgOutEl.classList.add("hidden");
    imgSkeletonEl.classList.remove("hidden");
  }
}

async function generate() {
  const prompt = (promptEl.value || "").trim();

  if (!prompt) {
    setStatus("Please enter an insurance-related prompt.", "error");
    return;
  }

  setStatus("Generating... please wait.", "ok");
  setLoading(true);

  try {
    const res = await fetch("/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(data.error || "Generation failed.");
    }

    // ✅ TEXT
    textOutEl.textContent = data.text || "";
    renderMetrics(data.metrics);
    await loadCharts(prompt);

    // ✅ IMAGE (HF + FALLBACK GUARANTEED)
    let imageUrl;

    if (data.image && data.image.startsWith("data:image")) {
      // HuggingFace success
      imageUrl = data.image;
      setStatus("Using AI generated image.", "ok");
    } else {
      // 🔥 ALWAYS WORKING FALLBACK
      imageUrl = `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}`;
      setStatus("Using fallback image (free API).", "ok");
    }

    imgOutEl.onload = () => {
      imgSkeletonEl.classList.add("hidden");
      imgOutEl.classList.remove("hidden");
    };

    imgOutEl.onerror = () => {
      imgSkeletonEl.classList.add("hidden");
      imgOutEl.classList.add("hidden");
      setStatus("Image failed to load.", "error");
    };

    imgOutEl.src = imageUrl;

    outputEl.classList.remove("hidden");

  } catch (err) {
    setStatus(err?.message || "Something went wrong.", "error");
  } finally {
    setLoading(false);
  }
}

// Button click
btnEl.addEventListener("click", generate);

// Enter key
promptEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") generate();
});

// Example chips
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    promptEl.value = chip.getAttribute("data-example") || "";
    promptEl.focus();
  });
});