from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from scipy.optimize import linprog
from pdf_generator import generate_pdf

app = Flask(__name__)

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json()
        species = data.get("species", "").lower()
        ingredients = data.get("ingredients", [])
        constraints = data.get("constraints", {})
        exclude = data.get("exclude", [])
        prices = data.get("prices", {})

        # Excel beolvasás (fejléc a 32. sor = header=31)
        ingredient_data = pd.read_excel(
            "Takarmány kalkulátor programhoz.xlsx",
            sheet_name="Adatbázis",
            header=31
        )

        # Alapanyagok beolvasása az N-O-P oszlopokból
        melted_names = ingredient_data[["RowID", "N", "O", "P"]].melt(
            id_vars=["RowID"],
            value_name="Name"
        ).dropna(subset=["Name"])
        melted_names["Name"] = melted_names["Name"].str.strip().str.lower()

        # Elérhető alapanyagok szűrése
        available = melted_names[melted_names["Name"].isin([i.lower() for i in ingredients])]
        if available.empty:
            return jsonify({"error": "Nem találhatók megfelelő alapanyagok."}), 400

        rows = available["RowID"].unique()
        subset = ingredient_data[ingredient_data["RowID"].isin(rows)].copy()
        subset["Name"] = subset["N"].combine_first(subset["O"]).combine_first(subset["P"])
        subset["Name"] = subset["Name"].str.strip()

        if subset.empty:
            return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

        # Tápanyag mátrix és célfüggvény
        nutrients = ["ME MJ/kg", "Nyers fehérje", "Nyers rost", "Nyers zsír", "Ca", "P", "Lizin", "Metionin"]
        A = subset[nutrients].fillna(0).values.T
        b = get_target_values(species, nutrients)

        bounds = []
        for _, row in subset.iterrows():
            name = row["Name"].strip().lower()
            if name in exclude:
                bounds.append((0, 0))
            else:
                min_val = constraints.get("max_amount", {}).get(name, 0)
                max_val = constraints.get("max_limit", {}).get(name, None)
                bounds.append((min_val, max_val if max_val is not None else None))

        c = np.array([prices.get(name.lower(), 0) for name in subset["Name"]])

        res = linprog(c, A_eq=A, b_eq=b, bounds=bounds, method="highs")

        if not res.success:
            return jsonify({
                "error": "A megadott alapanyagokkal nem érhető el az optimális keverék. Próbáljon meg több vagy más alapanyagot."
            }), 400

        result = {
            "recommendation": dict(zip(subset["Name"], res.x.round(3))),
            "species": species,
            "target_nutrition": dict(zip(nutrients, b.tolist()))
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_target_values(species, nutrients):
    if species == "tyúk":
        return np.array([11.5, 17, 5, 4, 3.5, 0.5, 0.75, 0.35])
    elif species == "kacsa":
        return np.array([12, 16, 4, 5, 3, 0.6, 0.7, 0.3])
    else:
        return np.array([11, 16, 5, 3, 3, 0.5, 0.6, 0.3])

if __name__ == "__main__":
    app.run(debug=True)
