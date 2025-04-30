from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from scipy.optimize import linprog

app = Flask(__name__)
CORS(app)  # <- Engedélyezi a külső kéréseket, pl. a frontendről

# Excel fájl és munkalap
excel_path = "Takarmány kalkulátor programhoz.xlsx"
sheet_name = "Adatbázis"

# Kalkulációs végpont
@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        species = data.get("species", "").lower()
        ingredients = data.get("ingredients", [])
        constraints = data.get("constraints", {})
        exclude = data.get("exclude", [])
        prices = data.get("prices", {})

        if not species or not ingredients:
            return jsonify({"error": "Hiányzó faj vagy alapanyaglista."}), 400

        # Excel beolvasás
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        df["Név"] = df[["N", "O", "P"]].bfill(axis=1).iloc[:, 0]

        # Csak azokat az alapanyagokat használjuk, amik a kérésben szerepelnek
        df = df[df["Név"].isin(ingredients)]
        if df.empty:
            return jsonify({"error": "Nem találhatók megfelelő alapanyagok."}), 400

        # Paraméterek
        nutrient_cols = ["ME MJ/kg", "Nyers fehérje", "Nyers rost", "Nyers zsír", "Ca", "P", "Lizin", "Metionin"]
        A = df[nutrient_cols].to_numpy().T
        b_min = np.array([4, 16, 3, 2, 0.8, 0.6, 0.5, 0.4])  # cél minimum tápértékek
        b_max = np.array([12, 22, 8, 5, 1.2, 1.0, 1.0, 0.7])

        bounds = []
        names = df["Név"].tolist()
        for name in names:
            if name in exclude:
                bounds.append((0, 0))
            elif name in constraints.get("max_amount", {}):
                max_kg = constraints["max_amount"][name]
                bounds.append((0, max_kg))
            else:
                bounds.append((0, None))

        # Ár minimalizálás
        costs = []
        for name in names:
            costs.append(prices.get(name, 0))
        c = np.array(costs)

        # Lineáris programozás: két oldalra szedve
        A_ub = np.vstack([A, -A])
        b_ub = np.hstack([b_max, -b_min])

        result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")

        if not result.success:
            return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

        quantities = result.x.round(2)
        recommendation = {name: q for name, q in zip(names, quantities) if q > 0}

        return jsonify({
            "species": species,
            "recommendation": recommendation,
            "target_nutrition": {
                "min": b_min.tolist(),
                "max": b_max.tolist(),
                "fields": nutrient_cols
            }
        })

    except Exception as e:
        return jsonify({"error": f"Hiba: {str(e)}"}), 500

# Főoldal (opcionális teszt)
@app.route('/')
def index():
    return "<h1>Takarmány Kalkulátor API</h1><p>Használd a <code>/calculate</code> végpontot POST kérésekkel.</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
