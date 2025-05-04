from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import os

app = Flask(__name__)

# Tápanyagcélok
FAJOK = {
    'tojó tyúk': {
        'Nyers fehérje': (16, 18),
        'Nyers zsír min.': (3, 5),
        'Nyers rost': (4, 5),
        'Lizin': (0.7, 0.8),
        'Metionin': (0.3, 0.35),
        'Kalcium': (3.5, 3.5),
        'Foszfor': (0.35, 0.45),
        'ME MJ/kg': (11, 12)
    },
    'tojó fürj': {
        'Nyers fehérje': (23.5, 24.5),
        'Nyers zsír min.': (3.4, 4),
        'Nyers rost': (0, 4),
        'Lizin': (1.4, 1.5),
        'Metionin': (0.35, 0.4),
        'Kalcium': (2.5, 3),
        'Foszfor': (0.6, 0.8),
        'ME MJ/kg': (11, 12)
    }
    # Bővíthető tovább
}

@app.route("/api/kalkulacio", methods=["POST"])
def kalkulacio():
    data = request.get_json()

    faj = data.get("faj", "").lower()
    alapanyagok_input = data.get("alapanyagok", "")
    szojamentes = data.get("szojamentes", False)

    if not faj or faj not in FAJOK:
        return jsonify({"error": "Ismeretlen vagy hiányzó faj."}), 400

    alapanyag_lista = [a.strip().lower() for a in alapanyagok_input.split(",") if a.strip()]
    if not alapanyag_lista:
        return jsonify({"error": "Nem adtál meg alapanyagokat."}), 400

    df = pd.read_excel("Takarmany_kalkulator.xlsx")
    nutrient_cols = list(FAJOK[faj].keys())

    for col in nutrient_cols:
        df[col] = df[col].fillna(0)
    df['Maximum mennyiség takarmánykeverékben'] = df['Maximum mennyiség takarmánykeverékben'].fillna(0).astype(float)

    df_filtered = df[df['Takarmány alapanyag'].str.lower().apply(
        lambda x: any(kw in x for kw in alapanyag_lista)
    )].copy()

    if szojamentes:
        df_filtered = df_filtered[~df_filtered['Takarmány alapanyag'].str.lower().str.contains("szója")]

    if df_filtered.empty:
        return jsonify({"error": "Nem található megfelelő alapanyag az adatbázisban."}), 400

    df_filtered = df_filtered.drop_duplicates(subset="Takarmány alapanyag", keep="first")
    A = df_filtered[nutrient_cols].to_numpy().T
    maxima = df_filtered["Maximum mennyiség takarmánykeverékben"].values * 100
    bounds = [(0, max_v) for max_v in maxima]
    x0 = np.ones(len(df_filtered)) * (100 / len(df_filtered))

    def objective(x):
        total_weight = np.sum(x)
        blend = A @ x / total_weight
        error = 0
        for i, (low, high) in enumerate(FAJOK[faj].values()):
            target = (low + high) / 2
            error += (blend[i] - target) ** 2
        return error

    constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 100}]
    result = minimize(objective, x0, bounds=bounds, constraints=constraints)

    if result.success:
        df_result = pd.DataFrame({
            "Alapanyag": df_filtered["Takarmány alapanyag"],
            "Mennyiség (kg)": result.x
        })
        keverek = df_result[df_result["Mennyiség (kg)"] > 0.1].to_dict(orient="records")
        return jsonify({"keverek": keverek})
    else:
        return jsonify({"error": "Nem sikerült érvényes keveréket találni."}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
