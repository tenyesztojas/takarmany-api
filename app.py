from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from scipy.optimize import linprog
import numpy as np

app = Flask(__name__)
CORS(app)

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        # Excel betöltése
        excel_path = "Takarmany_kalkulator.xlsx"
        df = pd.read_excel(excel_path)

        # Hiányzó értékek kiszűrése
        required_cols = ["ME MJ/kg", "Nyers fehérje", "Nyers zsír min.", "Nyers rost", "Kalcium", "Foszfor", "Lizin", "Metionin"]
        df_clean = df.dropna(subset=required_cols).copy()

        # Alapanyagok listája
        ingredients = df_clean["Takarmány alapanyag"].tolist()

        # Tápanyag mátrix (egy sor: 1kg adott alapanyag tápanyagtartalma)
        nutrition_matrix = df_clean[required_cols].values.T

        # Cél tápanyagértékek (pl. egy tojótyúk számára – igény szerint állítható)
        target_nutrition = {
            "ME MJ/kg": 11.5,
            "Nyers fehérje": 17,
            "Nyers zsír min.": 2.5,
            "Nyers rost": 5,
            "Kalcium": 3.5,
            "Foszfor": 0.5,
            "Lizin": 0.75,
            "Metionin": 0.25
        }

        b = np.array([target_nutrition[nutrient] for nutrient in required_cols])

        # Költségvektor (egységár helyett itt egyenlő súlyozást használunk, később cserélhető)
        c = np.ones(len(df_clean))

        # Egyenlőtlenségi feltételek: minden tápanyag legalább a célérték legyen
        A = -nutrition_matrix
        b_ub = -b

        # Korlátozások: nemnegatív tömegek, összsúly = 100kg
        bounds = [(0, None) for _ in range(len(df_clean))]

        # Egyenlőségfeltétel: össztömeg = 100kg
        A_eq = [np.ones(len(df_clean))]
        b_eq = [100]

        # Lineáris programozás futtatása
        result = linprog(c=c, A_ub=A, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

        if result.success:
            quantities = result.x
            response = {
                "recommendation": {
                    ingredients[i]: round(quantities[i], 2) for i in range(len(ingredients)) if quantities[i] > 0
                },
                "target_nutrition": target_nutrition,
            }
            return jsonify(response)
        else:
            return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

    except Exception as e:
        return jsonify({"error": f"Hiba: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
