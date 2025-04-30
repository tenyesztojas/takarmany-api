
from flask import send_file
from pdf_generator import create_pdf

@app.route("/download", methods=["GET"])
def download():
    path = "takarmany_ajanlas.pdf"
    return send_file(path, as_attachment=True)

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

    # PDF generálása
    pdf_path = create_pdf(result, species, target)

    return jsonify({
        "species": species,
        "target_nutrition": target,
        "recommendation": result,
        "pdf_url": "/download"
    })
