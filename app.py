from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from scipy.optimize import linprog

app = Flask(__name__)
CORS(app)

# Excel betöltése
excel_path = "Takarmány kalkulátor programhoz.xlsx"
sheet_name = "Adatbázis"
ingredient_data = pd.read_excel(excel_path, sheet_name=sheet_name)
ingredient_data = ingredient_data.dropna(subset=["N", "O", "P"], how="all").copy()

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json()
        species = data.get("species", "")
        ingredients = data.get("ingredients", [])
        constraints = data.get("constraints", {})
        max_amount = constraints.get("max_amount", {})
        exclude = constraints.get("exclude", [])
        prices = constraints.get("prices", {})

        # Csak a kiválasztott alapanyagok
        df = ingredient_data[ingredient_data["O"].isin(ingredients)].copy()

        if df.empty:
            return jsonify({"error": "A megadott alapanyagokkal nem érhető el az optimális keverék."}), 400

        if exclude:
            df = df[~df["O"].isin(exclude)]

        if df.empty:
            return jsonify({"error": "Minden alapanyag ki van zárva. Kérlek, adj meg legalább egy használható alapanyagot."}), 400

        # Ár mező
        df["ár"] = df["C"]

        # Tápérték cél
        target = {
            "fehérje": 16,
            "rost": 5,
            "energia": 10
        }

        A_eq = [
            df["F"].tolist(),  # nyers fehérje
            df["H"].tolist(),  # nyers rost
            df["E"].tolist(),  # ME MJ/kg
        ]
        b_eq = [
            target["fehérje"],
            target["rost"],
            target["energia"]
        ]

        bounds = []
        for i, row in df.iterrows():
            max_kg = max_amount.get(row["O"], None)
            if max_kg is not None:
                bounds.append((0, float(max_kg)))
            else:
                bounds.append((0, None))

        # Ár célfüggvény
        c = df["ár"].tolist()

        res = linprog(c=c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

        if res.success:
            amounts = res.x
            results = {}
            for i, row in df.iterrows():
                results[row["O"]] = round(amounts[i], 3)

            return jsonify({
                "recommendation": results,
                "species": species,
                "target_nutrition": target
            })
        else:
            return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

    except Exception as e:
        return jsonify({"error": f"Hiba: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
