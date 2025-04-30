from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

# Excel beolvasása
excel_data = pd.read_excel("Takarmany_kalkulator.xlsx", sheet_name="KALKULÁTOR", skiprows=32, nrows=30)

# Alapanyagnevek az N–O–P oszlopokban (index: 12, 13, 14)
name_columns = excel_data.iloc[:, [12, 13, 14]]
name_columns = name_columns.astype(str).apply(lambda col: col.str.strip())
all_names_flat = pd.Series(pd.unique(name_columns.values.ravel()))
all_names_flat = all_names_flat[all_names_flat != "nan"].reset_index(drop=True)

# Tápanyagadatok az első 13 oszlopból
ingredient_data = excel_data.iloc[:, :13]
ingredient_data.columns = [
    "Ingredient", "Price_per_kg", "Currency", "ME_MJkg", "Protein", "Fat", "Fiber",
    "Calcium", "Phosphorus", "Lysine", "Methionine", "NaN1", "NaN2"
]
ingredient_data = ingredient_data.drop(columns=["NaN1", "NaN2"])
ingredient_data = ingredient_data.dropna(subset=["Ingredient"])

# Konverzió számra
for col in ["ME_MJkg", "Protein", "Fat", "Fiber", "Calcium", "Phosphorus", "Lysine", "Methionine"]:
    ingredient_data[col] = pd.to_numeric(ingredient_data[col], errors="coerce")

# Sorazonosító hozzárendelése
ingredient_data["RowID"] = ingredient_data.index
name_columns["RowID"] = name_columns.index

# Alapanyag nevek hosszú formában (RowID + név)
melted_names = name_columns.melt(id_vars="RowID", value_name="Name").drop(columns=["variable"])
melted_names["Name"] = melted_names["Name"].astype(str).str.strip()
melted_names = melted_names[melted_names["Name"] != "nan"]

# Fajspecifikus célértékek
specs = {
    "fürj": {"Protein": 23.85, "Fat": 3.44, "Fiber": 3.96, "ME_MJkg": 11.5, "Calcium": 2.75, "Phosphorus": 0.5, "Lysine": 1.2, "Methionine": 0.5},
    "tyúk": {"Protein": 17.0, "Fat": 4.0, "Fiber": 4.5, "ME_MJkg": 11.5, "Calcium": 3.5, "Phosphorus": 0.4, "Lysine": 0.9, "Methionine": 0.4},
    "kacsa": {"Protein": 17.0, "Fat": 4.0, "Fiber": 5.5, "ME_MJkg": 11.5, "Calcium": 1.1, "Phosphorus": 0.45, "Lysine": 0.8, "Methionine": 0.35},
    "liba": {"Protein": 16.0, "Fat": 3.5, "Fiber": 6.5, "ME_MJkg": 10.5, "Calcium": 0.9, "Phosphorus": 0.4, "Lysine": 0.75, "Methionine": 0.3},
    "pulyka": {"Protein": 25.0, "Fat": 4.0, "Fiber": 4.5, "ME_MJkg": 12.5, "Calcium": 1.5, "Phosphorus": 0.5, "Lysine": 1.3, "Methionine": 0.55}
}

# Részleges egyezés
def matches_any(name, search_terms):
    name_lower = str(name).lower()
    return any(term.lower() in name_lower for term in search_terms)

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    species = data.get("species", "").lower()
    user_ingredients = data.get("ingredients", [])

    if species not in specs:
        return jsonify({"error": "Érvénytelen faj!"}), 400

    target = specs[species]

    # Szűrés részleges egyezéssel
    if user_ingredients:
        matching_rows = melted_names[melted_names["Name"].apply(lambda x: matches_any(x, user_ingredients))]
        matched_row_ids = matching_rows["RowID"].unique()
        df = ingredient_data[ingredient_data["RowID"].isin(matched_row_ids)]
    else:
        df = ingredient_data.copy()

    if df.empty:
        return jsonify({"error": "Nem találhatóak megfelelő alapanyagok."}), 400

    # Top 4 legfehérjésebb alapanyag
    top_ingredients = df.sort_values(by="Protein", ascending=False).head(4)
    top_ingredients["Ratio"] = 1 / len(top_ingredients)

    def scale_mix(amount_kg):
        mix = []
        for _, row in top_ingredients.iterrows():
            mix.append({
                "ingredient": row["Ingredient"],
                "amount_kg": round(amount_kg * row["Ratio"], 2),
                "protein": round(float(row["Protein"]), 2) if pd.notna(row["Protein"]) else 0,
                "energy": round(float(row["ME_MJkg"]), 2) if pd.notna(row["ME_MJkg"]) else 0
            })
        return mix

    result = {}
    for size in [10, 20, 30, 50, 100]:
        result[f"{size}_kg_mix"] = scale_mix(size)

    return jsonify({
        "species": species,
        "target_nutrition": target,
        "recommendation": result
    })

# Render-kompatibilis indítás
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
