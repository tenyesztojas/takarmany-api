from flask import Flask, request, jsonify, send_file
import pandas as pd
from scipy.optimize import linprog
from pdf_generator import generate_pdf

app = Flask(__name__)

excel_path = "TakarMány kalkulátor programhoz.xlsx"
sheet_name = "Adatbázis"

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json()

        species = data.get("species")
        ingredients = data.get("ingredients", [])
        constraints = data.get("constraints", {})
        exclude = data.get("exclude", [])
        prices = data.get("prices", {})

        ingredient_data = pd.read_excel(excel_path, sheet_name=sheet_name)
        ingredient_data = ingredient_data[["N", "O", "P", "ME MJ/kg", "Nyers fehérje", "Nyers rost", "Nyers zsír",
                                           "Ca", "P", "Lizin", "Metionin"]].copy()
        ingredient_data["Name"] = ingredient_data[["N", "O", "P"]].bfill(axis=1).iloc[:, 0]
        ingredient_data = ingredient_data.dropna(subset=["Name"])
        ingredient_data = ingredient_data.reset_index(drop=True)

        available = ingredient_data[ingredient_data["Name"].isin(ingredients) & ~ingredient_data["Name"].isin(exclude)]

        if available.empty:
            return jsonify({"error": "Nem találhatók megfelelő alapanyagok."}), 400

        A = []
        b = []

        target_nutrients = {
            "ME MJ/kg": 11.5,
            "Nyers fehérje": 16,
            "Nyers rost": 5,
            "Nyers zsír": 3,
            "Ca": 3.5,
            "P": 0.45,
            "Lizin": 0.7,
            "Metionin": 0.35
        }

        if species == "tyúk":
            target_nutrients.update({
                "ME MJ/kg": 11.5,
                "Nyers fehérje": 16,
                "Ca": 3.5,
                "P": 0.45
            })

        for nutrient, target in target_nutrients.items():
            row = available[nutrient].values
            A.append(row)
            b.append(target)

        bounds = []
        for name in available["Name"]:
            min_val = constraints.get("min_amount", {}).get(name, 0)
            max_val = constraints.get("max_amount", {}).get(name, None)
            bounds.append((min_val, max_val))

        c = []
        for name in available["Name"]:
            c.append(prices.get(name, 0))

        res = linprog(c=c, A_eq=A, b_eq=b, bounds=bounds, method="highs")

        if res.success:
            amounts = res.x
            result = {}
            for i, name in enumerate(available["Name"]):
                result[name] = round(amounts[i], 3)

            total = sum(amounts)
            nutrients_result = {}
            for i, (nutrient, target) in enumerate(target_nutrients.items()):
                actual = sum(available.iloc[:, 3 + i] * amounts) / total
                nutrients_result[nutrient] = round(actual, 2)

            # PDF generálása
            pdf_path = generate_pdf(result, nutrients_result, species)
            return send_file(pdf_path, as_attachment=True)

        return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
