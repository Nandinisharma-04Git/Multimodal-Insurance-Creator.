import os
import json
import random
import time
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from image_generation import HuggingFaceImageError, generate_insurance_image_data_uri
from llm_integration import GroqError, generate_insurance_explanation

load_dotenv()

app = Flask(__name__)

def _insurance_category(prompt: str) -> str:
    p = (prompt or "").lower()
    if any(k in p for k in ["health", "medical", "hospital", "family floater"]):
        return "health"
    if any(k in p for k in ["life", "term", "mortgage", "income protection"]):
        return "life"
    if any(k in p for k in ["car", "auto", "vehicle", "bike", "motor"]):
        return "motor"
    if any(k in p for k in ["home", "house", "property", "renters"]):
        return "home"
    if any(k in p for k in ["travel", "trip", "flight", "visa"]):
        return "travel"
    return "general"


def _fresh_metrics(prompt: str) -> dict:
    """
    Generates fresh (non-deterministic) metrics for UI visuals.
    These values are illustrative only.
    """
    rng = random.Random()
    rng.seed(time.time_ns() ^ os.getpid() ^ random.getrandbits(64))

    cat = _insurance_category(prompt)
    if cat == "health":
        premium = rng.randint(800, 4500)
        deductible = rng.choice([0, 500, 1000, 2000, 5000])
        coverage = rng.randint(3, 25) * 100000
    elif cat == "life":
        premium = rng.randint(300, 2500)
        deductible = 0
        coverage = rng.randint(25, 150) * 100000
    elif cat == "motor":
        premium = rng.randint(600, 6000)
        deductible = rng.choice([500, 1000, 2000, 5000])
        coverage = rng.randint(2, 20) * 100000
    elif cat == "home":
        premium = rng.randint(500, 5000)
        deductible = rng.choice([1000, 2000, 5000, 10000])
        coverage = rng.randint(10, 80) * 100000
    elif cat == "travel":
        premium = rng.randint(150, 1800)
        deductible = rng.choice([0, 200, 500, 1000])
        coverage = rng.randint(1, 8) * 100000
    else:
        premium = rng.randint(300, 4000)
        deductible = rng.choice([0, 500, 1000, 2000, 5000])
        coverage = rng.randint(2, 40) * 100000

    rating = round(rng.uniform(3.2, 4.9), 1)
    risk_score = rng.randint(18, 88)  # 0-100, higher means riskier
    coverage_score = rng.randint(45, 96)  # 0-100
    claim_readiness = rng.randint(40, 95)  # 0-100

    return {
        "category": cat,
        "rating": rating,
        "monthly_premium_est": premium,
        "deductible_est": deductible,
        "coverage_est": coverage,
        "risk_score": risk_score,
        "coverage_score": coverage_score,
        "claim_readiness": claim_readiness,
        "disclaimer": "Estimates are illustrative, not a quote.",
    }


def _random_chart_fallback(prompt: str) -> dict:
    m = _fresh_metrics(prompt)
    rng = random.Random()
    rng.seed(time.time_ns() ^ random.getrandbits(64))

    # Create 3 plan tiers around the premium/coverage estimates.
    base_p = max(150, int(m["monthly_premium_est"]) * 12)
    base_c = max(100000, int(m["coverage_est"]))
    labels = ["Basic", "Standard", "Premium"]
    premium = [
        int(base_p * rng.uniform(0.65, 0.85)),
        int(base_p * rng.uniform(0.95, 1.20)),
        int(base_p * rng.uniform(1.35, 1.80)),
    ]
    coverage = [
        int(base_c * rng.uniform(0.45, 0.75)),
        int(base_c * rng.uniform(0.85, 1.20)),
        int(base_c * rng.uniform(1.30, 2.10)),
    ]

    cats = ["Health", "Life", "Car", "Home", "Travel"]
    focus = m["category"]
    focus_map = {"health": "Health", "life": "Life", "motor": "Car", "home": "Home", "travel": "Travel"}
    focus_label = focus_map.get(focus, "Health")

    # Give higher weight to the prompt category, but keep variation.
    weights = []
    for c in cats:
        w = rng.uniform(5, 20)
        if c == focus_label:
            w += rng.uniform(25, 45)
        weights.append(w)
    s = sum(weights) or 1
    values = [round(w * 100 / s, 1) for w in weights]
    # fix rounding drift
    drift = round(100 - sum(values), 1)
    values[0] = round(values[0] + drift, 1)

    years = [str(y) for y in range(2020, 2026)]
    def series(mult: float):
        v = []
        cur = base_p * mult
        for _ in years:
            cur = cur * rng.uniform(1.03, 1.12)
            v.append(int(cur))
        return v

    return {
        "premium_coverage": {"labels": labels, "premium": premium, "coverage": coverage},
        "type_breakdown": {"labels": cats, "values": values},
        "cost_over_time": {"years": years, "basic": series(0.75), "standard": series(1.05), "premium": series(1.55)},
    }

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/generate")
def generate():
    try:
        data = request.get_json(silent=True) or {}
        prompt = (data.get("prompt") or "").strip()

        if not prompt:
            return jsonify({"error": "Please enter an insurance-related prompt."}), 400

        # ✅ TEXT (always try)
        generated_text = generate_insurance_explanation(prompt)
        #generated_text = "Text generation paused temporarily."

        # ✅ IMAGE (safe try-catch)
        try:
            image_data_uri = generate_insurance_image_data_uri(prompt)
        except Exception as e:
            print("Image error:", e)
            image_data_uri = ""  # fallback

        return jsonify({
            "prompt": prompt,
            "text": generated_text,
            "image": image_data_uri,
            "metrics": _fresh_metrics(prompt),
        })

    except GroqError as e:
        return jsonify({"error": f"Text generation failed: {str(e)}"}), 502

    except Exception as e:
        print("Server error:", e)
        return jsonify({"error": "Something went wrong. Please try again."}), 500


@app.post("/charts-data")
def charts_data():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()

    system = """You are an insurance data expert.
Given a user's insurance prompt, return ONLY a valid JSON object (no explanation, no markdown, no backticks) with this exact structure:

{
  "premium_coverage": {
    "labels": ["Plan A", "Plan B", "Plan C"],
    "premium": [3000, 6000, 12000],
    "coverage": [100000, 300000, 600000]
  },
  "type_breakdown": {
    "labels": ["Health", "Life", "Car", "Home", "Travel"],
    "values": [35, 30, 20, 10, 5]
  },
  "cost_over_time": {
    "years": ["2020", "2021", "2022", "2023", "2024", "2025"],
    "basic": [3000, 3200, 3500, 3800, 4100, 4500],
    "standard": [6000, 6500, 7100, 7800, 8400, 9000],
    "premium": [12000, 13000, 14000, 15000, 16000, 17000]
  }
}

Rules:
- Make ALL numbers realistic and specific to the prompt topic
- For type_breakdown, give higher percentage to the insurance type in the prompt
- Labels in premium_coverage should reflect actual plan names for that insurance
- Return ONLY raw JSON, nothing else, no markdown, no backticks"""

    try:
        import requests as req
        resp = req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 600,
            },
            timeout=30
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if model adds them
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        chart_data = json.loads(raw)
        return jsonify(chart_data)

    except Exception as e:
        print("Chart data error:", e)
        # Fallback that still changes every request
        return jsonify(_random_chart_fallback(prompt))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "0") == "1")