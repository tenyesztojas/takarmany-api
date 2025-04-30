from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from scipy.optimize import linprog

app = Flask(__name__)
CORS(app)

# Excel betöltése
excel_path = "Takarmány kalkulátor programhoz.xlsx"
sheet_name = "Adatbázis"
ingredient_data = pd.read_excel(excel_path, sheet_name=sheet_name)

# Átalakítás (N, O, P oszlopokból összevonás)
ingredient_data = ingredient_data.dropna(subset=["N", "O", "P"], how="all").copy()
ingredient_data["RowID"] = ingredient_data.index
melted = ingredient_data.melt(id_vars=["RowID"], value_vars=["N", "O", "P"], value_name="Name").dropna()
merged_data = melted.merge(ingredient_data, left_on="RowID", right_index=True)

# Egyszerűsített táblázat a nevek alapján
merged_data = merged_data.rename(columns={
    "Name": "ingredient_name",
    "ME MJ/kg": "me",
    "Nyers fehérje": "protein",
    "Nyers zsír min.": "fat",
    "Nyers rost": "fiber",
    "Ca": "ca",
    "P": "p",
    "Lizin": "lysine",
    "Metionin": "methionine"
})

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json()

        species = data.get("species")
        ingredients_input = data.get("ingredients", [])
        constraints = data.get("constraints", {})

        if not ingredients_input:
            return jsonify({"error": "Nem adtál meg egy alapanyagot sem."}), 400

        df = merged_data[merged_data["ingredient_name"].isin(ingredients_input)].copy()

        if df.empty:
            return jsonify({"error": "Nem találhatóak megfelelő alapanyagok."}), 400

        nutrient_columns = ["protein", "me", "fiber", "fat", "ca", "p", "lysine", "methionine"]

        A = df[nutrient_columns].fillna(0).to_numpy().T
        c = np.ones(len(df))  # minimalizáljuk az össztömeget

        # Cél: legalább ennyit teljesítsen a tápanyagokból
        target_nutrients = {
            "protein": 16,
            "me": 11,
            "fiber": 5,
            "fat": 2,
            "ca": 0.8,
            "p": 0.6,
            "lysine": 0.5,
            "methionine": 0.25
        }

        b = np.array([target_nutrients[n] for n in nutrient_columns])
        res = linprog(c=c, A_ub=-A, b_ub=-b, bounds=(0, None), method='highs')

        if res.success:
            result = {
                "species": species,
                "target_nutrition": target_nutrients,
                "recommendation": dict(zip(df["ingredient_name"], res.x.round(3).tolist()))
            }
            return jsonify(result)
        else:
            return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

    except Exception as e:
        return jsonify({"error": f"Hiba: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
