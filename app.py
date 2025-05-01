from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

EXCEL_PATH = "Takarmany_kalkulator.xlsx"
SHEET_NAME = 0  # első munkalap

# Célértékek fajonként
CELERTEKEK = {
    "Fürj": {"Fehérje": 23.85, "Zsír": 3.44, "Rost_max": 3.96, "Lizin": 1.42, "Metionin": 0.35, "Kalcium_min": 2.5, "Kalcium_max": 3.0, "Foszfor_min": 0.6, "Foszfor_max": 0.8, "Energia_min": 11, "Energia_max": 12},
    "Tyúk": {"Fehérje": 17, "Zsír": 4, "Rost_max": 5, "Lizin": 0.75, "Metionin": 0.325, "Kalcium_min": 3.5, "Kalcium_max": 3.5, "Foszfor_min": 0.35, "Foszfor_max": 0.45, "Energia_min": 11, "Energia_max": 12},
    "Pulyka": {"Fehérje": 25, "Zsír": 4, "Rost_max": 5, "Lizin": 1.55, "Metionin": 0.5, "Kalcium_min": 1.2, "Kalcium_max": 2.0, "Foszfor_min": 0.7, "Foszfor_max": 0.8, "Energia_min": 12, "Energia_max": 13},
    "Kacsa": {"Fehérje": 17, "Zsír": 4, "Rost_max": 6, "Lizin": 0.75, "Metionin": 0.325, "Kalcium_min": 1.0, "Kalcium_max": 1.2, "Foszfor_min": 0.4, "Foszfor_max": 0.5, "Energia_min": 11, "Energia_max": 12},
    "Liba": {"Fehérje": 16, "Zsír": 3.5, "Rost_max": 7, "Lizin": 0.75, "Metionin": 0.325, "Kalcium_min": 0.8, "Kalcium_max": 1.0, "Foszfor_min": 0.4, "Foszfor_max": 0.5, "Energia_min": 10, "Energia_max": 11}
}

@app.route('/kalkulal', methods=['POST'])
def kalkulal():
    try:
        faj = request.json.get("faj")
        if faj not in CELERTEKEK:
            return jsonify({"error": "Ismeretlen faj!"}), 400

        c = CELERTEKEK[faj]
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
        df = df.dropna(subset=["ME MJ/kg", "Nyers fehérje", "Nyers zsír min.", "Nyers rost", "Kalcium", "Foszfor", "Lizin", "Metionin"])

        # Egyszerű arány: egyenlő mennyiségből (1 kg) számolunk
        df["Mennyiség_kg"] = 1

        osszes = {
            "Fehérje": np.sum(df["Nyers fehérje"]),
            "Zsír": np.sum(df["Nyers zsír min."]),
            "Rost": np.sum(df["Nyers rost"]),
            "Lizin": np.sum(df["Lizin"]),
            "Metionin": np.sum(df["Metionin"]),
            "Kalcium": np.sum(df["Kalcium"]),
            "Foszfor": np.sum(df["Foszfor"]),
            "Energia": np.sum(df["ME MJ/kg"]),
        }

        total_kg = len(df)
        atlag = {k: round(v / total_kg, 2) for k, v in osszes.items()}

        return jsonify({
            "faj": faj,
            "celertekek": c,
            "eredmeny": atlag,
            "alapanyagok_szama": total_kg
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return jsonify({"message": "Takarmánykalkulátor API él."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
