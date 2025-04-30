from flask import Flask, request, jsonify
import pandas as pd
from scipy.optimize import linprog
import numpy as np

app = Flask(__name__)

# Excel betöltése
excel_data = pd.read_excel("Takarmany_kalkulator.xlsx", sheet_name="KALKULÁTOR", skiprows=32, nrows=30)

# Alapanyag nevek (N, O, P oszlop)
name_columns = excel_data.iloc[:, [12, 13, 14]].astype(str).apply(lambda col: col.str.strip())
name_columns["RowID"] = name_columns.index

# Tápanyagadatok
ingredient_data = excel_data.iloc[:, :13]
ingredient_data.columns = [
    "Ingredient", "Price_per_kg", "Currency", "ME_MJkg", "Protein", "Fat", "Fiber",
    "Calcium", "Phosphorus", "Lysine", "Methionine", "NaN1", "NaN2"
]
ingredient_data = ingredient_data.drop(columns=["NaN1", "NaN2"])
ingredient_data = ingredient_data.dropna(subset=["Ingredient"])
for col in ["ME_MJkg", "Protein", "Fat", "Fiber", "Calcium", "Phosphorus", "Lysine", "Methionine"]:
    ingredient_data[col] = pd.to_numeric(ingredient_data[col], errors="coerce")
ingredient_data["RowID"] = ingredient_data.index

# "Hosszú" formára alakítás
melted_names = name_columns.melt(id_vars="RowID", value_name="Name").drop(columns=["variable"])
melted_names = melted_names[melted_names["Name"] != "nan"]
melted_names["Name"] = melted_names["Name"].astype(str).str.strip()

# Faj-specifikus célértékek
specs = {
    "fürj": {"Protein": 23.85, "Fat": 3.44, "Fiber": 3.96, "ME_MJkg": 11.5, "Calcium": 2.75, "Phosphorus": 0.5, "Lysine": 1.2, "Methionine": 0.5},
    "tyúk": {"Protein": 17.0, "Fat": 4.0, "Fiber": 4.5, "ME_MJkg": 11.5, "Calcium": 3.5, "Phosphorus": 0.4, "Lysine": 0.9, "Methionine": 0.4},
    "kacsa": {"Protein": 17.0, "Fat": 4.0, "Fiber": 5.5, "ME_MJkg": 11.5, "Calcium": 1.1, "Phosphorus": 0.45, "Lysine": 0.8, "Methionine": 0.35},
    "liba": {"Protein": 16.0, "Fat": 3.5, "Fiber": 6.5, "ME_MJkg": 10.5, "Calcium": 0.9, "Phosphorus": 0.4, "Lysine": 0.75, "Methionine": 0.3},
    "pulyka": {"Protein": 25.0, "Fat": 4.0, "Fiber": 4.5, "ME_MJkg": 12.5, "Calcium": 1.5, "Phosphorus": 0.5, "Lysine": 1.3, "Methionine": 0.55}
}

# Segédfüggvény a részleges kereséshez
def matches_any(name, search_terms):
    name = str(name).lower()
    return any(term.lower() in name for term in search_terms)

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json()
    species = data.get("species", "").lower()
    ingredients = data.get("ingredients", [])

    if species not in specs:
        return jsonify({"error": "Érvénytelen faj!"}), 400

    if not ingredients:
        return jsonify({"error": "Nem adott meg alapanyagot."}), 400

    # Megfelelő sorok keresése
    matched_ids = melted_names[melted_names["Name"].apply(lambda x: matches_any(x, ingredients))]["RowID"].unique()
    df = ingredient_data[ingredient_data["RowID"].isin(matched_ids)].copy()

    if df.empty:
        return jsonify({"error": "Nem találhatók megfelelő alapanyagok."}), 400

    nutrients = ["Protein", "Fat", "Fiber", "ME_MJkg", "Calcium", "Phosphorus", "Lysine", "Methionine"]
    target = specs[species]

    A = df[nutrients].fillna(0).to_numpy().T  # (nutrient x ingredient)
    b = np.array([target[n] for n in nutrients])
    n = A.shape[1]

    # Minimalizáljuk az összes eltérés négyzetét: min ||Ax - b||^2
    # átalakítjuk LP-re: min sum |Ax - b|
    # trükk: minimalizáljuk a célfüggvényt z = 0 (mert a cél a közelítés), a constraint pedig Ax ≈ b

    bounds = [(0, 1) for _ in range(n)]
    constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}

    # Közelítés linprog-pal: Ax = b -> optimalizáljuk az eltérést
    try:
        res = linprog(
            c=np.zeros(n),  # nincs konkrét költség, csak constraint
            A_eq=A,
            b_eq=b,
            bounds=bounds,
            method="highs"
        )
    except Exception as e:
        return jsonify({"error": f"Optimalizációs hiba: {str(e)}"}), 500

    if not res.success:
        return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

    ratios = res.x
    df["Ratio"] = ratios

    def generate_mix(amount_kg):
        mix = []
        for _, row in df.iterrows():
            mix.append({
                "ingredient": row["Ingredient"],
                "amount_kg": round(row["Ratio"] * amount_kg, 2),
                "ratio": round(row["Ratio"], 4),
                "protein": round(float(row["Protein"]), 2),
                "energy": round(float(row["ME_MJkg"]), 2)
            })
        return mix

    result = {}
    for kg in [10, 20, 30, 50, 100]:
        result[f"{kg}_kg_mix"] = generate_mix(kg)

    return jsonify({
        "species": species,
        "target_nutrition": target,
        "recommendation": result
    })

# Render kompatibilis indítás
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
