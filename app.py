from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from scipy.optimize import linprog
from pdf_generator import generate_pdf
import base64

app = Flask(__name__)
CORS(app)

excel_path = "Takarmány kalkulátor programhoz.xlsx"
sheet_name = "Adatbázis"

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.json
        species = data.get("species")
        ingredients = data.get("ingredients", [])
        constraints = data.get("constraints", {})
        exclude = data.get("exclude", [])
        prices = data.get("prices", {})

        if not species or not ingredients:
            return jsonify({"error": "Hiányzó faj vagy alapanyagok."}), 400

        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        melted_names = df[["RowID", "N", "O", "P"]].melt(id_vars="RowID", value_name="Name").dropna()
        melted_names["Name"] = melted_names["Name"].astype(str).str.strip().str.lower()
        name_map = dict(zip(melted_names["Name"], melted_names["RowID"]))

        # Kiválasztott alapanyagok szűrése
        selected_ids = []
        for name in ingredients:
            key = name.strip().lower()
            if key in name_map:
                selected_ids.append(name_map[key])
            else:
                return jsonify({"error": f"Nincs adat ehhez az alapanyaghoz: {name}"}), 400

        if len(selected_ids) == 0:
            return jsonify({"error": "Nem találhatóak megfelelő alapanyagok."}), 400

        df_selected = df[df["RowID"].isin(selected_ids)].copy()

        # Tápanyagcélok beállítása faj alapján (egyszerűsített példa)
        nutrition_targets = {
            "tyúk": {"ME MJ/kg": 11, "Nyers fehérje": 16, "Nyers rost": 5},
            "kacsa": {"ME MJ/kg": 11.5, "Nyers fehérje": 17, "Nyers rost": 5},
            "liba": {"ME MJ/kg": 11.8, "Nyers fehérje": 18, "Nyers rost": 6}
        }

        target = nutrition_targets.get(species.lower())
        if not target:
            return jsonify({"error": "Ismeretlen faj"}), 400

        nutrients = ["ME MJ/kg", "Nyers fehérje", "Nyers rost"]

        A = []
        b = []
        for nutrient in nutrients:
            A.append(df_selected[nutrient].values)
            b.append(target[nutrient])

        A_eq = [np.ones(len(df_selected))]
        b_eq = [1.0]

        bounds = []
        for idx, row in df_selected.iterrows():
            min_amount = 0
            max_amount = 1
            fajta = str(row["O"]).strip().lower()
            if fajta in constraints.get("max_amount", {}):
                max_amount = float(constraints["max_amount"][fajta])
            if fajta in constraints.get("min_amount", {}):
                min_amount = float(constraints["min_amount"][fajta])
            if fajta in exclude:
                max_amount = 0
            bounds.append((min_amount, max_amount))

        cost = []
        for idx, row in df_selected.iterrows():
            fajta = str(row["O"]).strip().lower()
            cost.append(float(prices.get(fajta, 0)))

        res = linprog(
            c=cost,
            A_eq=A_eq,
            b_eq=b_eq,
            A_ub=A,
            b_ub=b,
            bounds=bounds,
            method='highs'
        )

        if not res.success:
            return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

        proportions = res.x
        result = []
        for i, val in enumerate(proportions):
            if val > 0:
                row = df_selected.iloc[i]
                result.append({
                    "name": row["O"],
                    "percentage": round(val * 100, 2),
                    "amount_kg": round(val * 100, 2)
                })

        pdf_bytes = generate_pdf(result, species, target)
        encoded_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

        return jsonify({
            "species": species,
            "recommendation": result,
            "target_nutrition": target,
            "pdf_base64": encoded_pdf
        })

    except Exception as e:
        return jsonify({"error": f"Hiba: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
