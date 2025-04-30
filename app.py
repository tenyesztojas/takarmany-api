from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

# Betöltjük az Excel-táblát
excel_data = pd.read_excel("Takarmany_kalkulator.xlsx", sheet_name="KALKULÁTOR", skiprows=32, nrows=30)

# O, P, Q oszlopokból kivesszük az alapanyagneveket (index: 13, 14, 15)
combined_ingredients = excel_data.iloc[:, [13, 14, 15]]
all_ingredient_names = pd.Series(pd.unique(combined_ingredients.values.ravel()))
all_ingredient_names = all_ingredient_names.dropna().astype(str).str.strip().reset_index(drop=True)

# Eredeti tápérték táblázat (M oszloptól balra): 0–12 oszlopok
ingredient_data = excel_data.iloc[:, :13]
ingredient_data.columns = [
    "Ingredient", "Price_per_kg", "Currency", "ME_MJkg", "Protein", "Fat", "Fiber",
    "Calcium", "Phosphorus", "Lysine", "Methionine", "NaN"
]
ingredient_data = ingredient_data.drop(columns=["NaN"])
ingredient_data = ingredient_data.dropna(subset=["Ingredient"])
for col in ["ME_MJkg", "Protein", "Fat", "Fiber", "Calcium", "Phosphorus", "Lysine", "Methionine"]:
    ingredient_data[col] = pd.to_numeric(ingredient_data[col], errors="coerce")

# Faj-specifikus tápanyagcélértékek
specs = {
    "fürj": {"Protein": 23.85, "Fat": 3.44, "Fiber": 3.96, "ME_MJkg": 11.5, "Calcium": 2.75, "Phosphorus": 0.5, "Lysine": 1.2, "Methionine": 0.5},
    "tyúk": {"Protein": 17.0, "Fat": 4.0, "Fiber": 4.5, "ME_MJkg": 11.5, "Calcium": 3.5, "Phosphorus": 0.4, "Lysine": 0.9, "Methionine": 0.4},
    "kacsa": {"Protein": 17.0, "Fat": 4.0, "Fiber": 5.5, "ME_MJkg": 11.5, "Calcium": 1.1, "Phosphorus": 0.45, "Lysine": 0.8, "Methionine": 0.35},
    "liba": {"Protein": 16.0, "Fat": 3.5, "Fiber": 6.5, "ME_MJkg": 10.5, "Calcium": 0.9, "Phosphorus": 0.4, "Lysine": 0.75, "Methionine": 0.3},
    "pulyka": {"Protein": 25.0, "Fat": 4.0, "Fiber": 4.5, "ME_MJkg": 12.5, "Calcium": 1.5, "Phosphorus": 0.5, "Lysine": 1.3, "Methionine": 0.55}
}

# Részleges szövegegyezés
def matches_any(ingredient, search_terms):
    if pd.isnull(ingredient):
        return False
    ingredient_str = str(ingredient).lower()
    return any(term.lower() in ingredient_str for term in search_terms)

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    species = data.get("species", "").lower()
    user_ingredients = data.get("ingredients", [])

    if species not in specs:
        return jsonify({"error": "Érvénytelen faj!"}), 400

    target = specs[species]

    # Szűrés a részleges egyezés alapján az O, P, Q oszlopból származó nevek között
    if user_ingredients:
        matching_names = all_ingredient_names[all_ingredient_names.apply(lambda x: matches_any(x, user_ingredients))]
        df = ingredient_data[ingredient_data["Ingredient"].isin(matching_names)]
    else:
        df = ingredient_data.copy()

    if df.empty:
        return jsonify({"error": "Nem találhatóak megfelelő alapanyagok."}), 400

    # Top 4 legfehérjésebb alapanyagból keverék
    top_ingredients = df.sort_values(by="Protein", ascending=False).head(4)
    top_ingredients["Ratio"] = 1 / len(top_ingredients)

    def scale_mixture(amount_kg):
        mix = []
        for _, row in top_ingredients.iterrows():
            mix.append({
                "ingredient": row["Ingredient"],
                "amount_kg": round(amount_kg * row["Ratio"], 2),
                "protein": round(row["Protein"], 2),
                "energy": round(row["ME_MJkg"], 2)
            })
        return mix

    output = {}
    for size in [10, 20, 30, 50, 100]:
        output[f"{size}_kg_mix"] = scale_mixture(size)

    return jsonify({
        "species": species,
        "target_nutrition": target,
        "recommendation": output
    })

# Render-specifikus indítás
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
