from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

# Excel beolvasás
excel_path = "Takarmany_kalkulator.xlsx"
sheet_name = "Adatbazis"  # győződj meg róla, hogy ez a lapnév létezik
ingredient_data = pd.read_excel(excel_path, sheet_name=sheet_name)

@app.route("/calculate", methods=["POST"])
def calculate_feed():
    try:
        data = request.get_json()
        animal_type = data["species"]
        ingredients = data["ingredients"]
        constraints = data.get("constraints", {})
        exclude = data.get("exclude", [])

        available = ingredient_data[ingredient_data["Van"] == 1].copy()
        available = available[~available["Fajta"].isin(exclude)]
        available = available[available["Fajta"].isin(ingredients)]

        if available.empty:
            return jsonify({"error": "A megadott alapanyagokkal nem érhető el az optimális keverék. Próbálj meg több vagy más alapanyagot."}), 400

        # Egyszerű aránykiosztás - fejleszthető optimalizálással
        available["Arány"] = 1 / len(available)
        available["Arány"] = available["Arány"].round(2)

        nutrient_totals = {
            "ME MJ/kg": np.dot(available["Arány"], available["ME MJ/kg"]),
            "Nyers fehérje": np.dot(available["Arány"], available["Nyers fehérje"]),
            "Nyers zsír min.": np.dot(available["Arány"], available["Nyers zsír min."]),
            "Nyers rost": np.dot(available["Arány"], available["Nyers rost"]),
            "Ca": np.dot(available["Arány"], available["Ca"]),
            "P": np.dot(available["Arány"], available["P"]),
            "Lizin": np.dot(available["Arány"], available["Lizin"]),
            "Metionin": np.dot(available["Arány"], available["Metionin"])
        }

        response = {
            "mix": available[["Fajta", "Arány"]].to_dict(orient="records"),
            "nutrition": nutrient_totals
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Hiba: {str(e)}"}), 500
