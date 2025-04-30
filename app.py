from flask import Flask, request, jsonify, send_file
import pandas as pd
import numpy as np
from scipy.optimize import linprog
from pdf_generator import create_pdf

app = Flask(__name__)

# Adatok betöltése
ingredient_data = pd.read_excel("Takarmány kalkulátor programhoz.xlsx", sheet_name="Adatbázis")
ingredient_data["RowID"] = ingredient_data.index
ingredient_data.fillna(0, inplace=True)

melted_names = ingredient_data[["RowID", "N", "O", "P"]].melt(id_vars="RowID", value_name="Name").dropna()

specs = pd.read_csv("Faj-Fehrje-Zsr-Rost-MetabolizlhatenergiaMJkg-Kalcium-Foszfor-Lizin-Metionin.csv")
specs = specs.set_index("Faj").T.to_dict()

def matches_any(text, terms):
    return any(term.lower() in str(text).lower() for term in terms)

@app.route("/download", methods=["GET"])
def download():
    return send_file("takarmany_ajanlas.pdf", as_attachment=True)

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json()
    species = data.get("species", "").lower()
    ingredients = data.get("ingredients", [])
    constraints = data.get("constraints", {})

    if species not in specs:
        return jsonify({"error": "Érvénytelen faj!"}), 400
    if not ingredients:
        return jsonify({"error": "Nem adott meg alapanyagot."}), 400

    matched_ids = melted_names[melted_names["Name"].apply(lambda x: matches_any(x, ingredients))]["RowID"].unique()
    df = ingredient_data[ingredient_data["RowID"].isin(matched_ids)].copy()

    if df.empty:
        return jsonify({"error": "Nem találhatók megfelelő alapanyagok."}), 400

    exclude = constraints.get("exclude", [])
    if exclude:
        exclude_ids = melted_names[melted_names["Name"].apply(lambda x: matches_any(x, exclude))]["RowID"].unique()
        df = df[~df["RowID"].isin(exclude_ids)]

    if df.empty:
        return jsonify({"error": "Minden alapanyag kizárásra került."}), 400

    nutrients = ["Protein", "Fat", "Fiber", "ME_MJkg", "Calcium", "Phosphorus", "Lysine", "Methionine"]
    target = specs[species]
    A = df[nutrients].fillna(0).to_numpy().T
    b = np.array([target[n] for n in nutrients])
    n = A.shape[1]

    bounds = []
    max_amount = constraints.get("max_amount_kg", {})
    min_amount = constraints.get("min_amount_kg", {})
    for _, row in df.iterrows():
        name = row["Ingredient"]
        min_val = min_amount.get(name, 0) / 100
        max_val = max_amount.get(name, 1) / 100
        bounds.append((min_val, max_val))

    try:
        res = linprog(
            c=np.zeros(n),
            A_eq=A,
            b_eq=b,
            bounds=bounds,
            method="highs"
        )
    except Exception as e:
        return jsonify({"error": f"Optimalizációs hiba: {str(e)}"}), 500

    if not res.success:
        return jsonify({
            "error": "A megadott alapanyagokkal nem érhető el az optimális keverék. Próbáljon meg több vagy más alapanyagot."
        }), 400

    ratios = res.x
    df["Ratio"] = ratios

    def generate_mix(amount_kg):
        return [{
            "ingredient": row["Ingredient"],
            "amount_kg": round(row["Ratio"] * amount_kg, 2),
            "ratio": round(row["Ratio"], 4),
            "protein": round(float(row["Protein"]), 2),
            "energy": round(float(row["ME_MJkg"]), 2)
        } for _, row in df.iterrows()]

    result = {f"{kg}_kg_mix": generate_mix(kg) for kg in [10, 20, 30, 50, 100]}

    pdf_path = create_pdf(result, species, target)

    return jsonify({
        "species": species,
        "target_nutrition": target,
        "recommendation": result,
        "pdf_url": "/download"
    })

if __name__ == "__main__":
    app.run(debug=True)
