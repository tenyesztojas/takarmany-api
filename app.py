from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from scipy.optimize import linprog
from pdf_generator import generate_pdf  # külső fájlból importálva

app = Flask(__name__)

# Excel betöltés
excel_path = "TakarMány kalkulátor programhoz.xlsx"
sheet_name = "Adatbázis"
ingredient_data = pd.read_excel(excel_path, sheet_name=sheet_name)

# N, O, P oszlopok egyesítése alapanyagnévhez
ingredient_data["RowID"] = ingredient_data.index
melted_names = ingredient_data[["RowID", "N", "O", "P"]].melt(
    id_vars="RowID", value_name="Name"
).dropna()

# Tápanyagoszlopok
nutrients = ["ME MJ/kg", "Nyers fehérje", "Nyers zsír", "Nyers rost", "Ca", "P", "Lizin", "Metionin"]
nutrient_columns = ["E", "F", "G", "H", "I", "J", "K", "L"]  # Opcionális, ha oszlopnevek lennének

# Tápanyag-értékek
nutrient_matrix = ingredient_data[nutrients].values.T  # shape: (8, N)
target_values = {
    "ME MJ/kg": 11,
    "Nyers fehérje": 17,
    "Nyers zsír": 3,
    "Nyers rost": 5,
    "Ca": 1,
    "P": 0.6,
    "Lizin": 0.65,
    "Metionin": 0.3,
}


@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json()
        species = data.get("species")
        ingredients = data.get("ingredients", [])
        constraints = data.get("constraints", {})
        max_amounts = constraints.get("max_amount", {})
        exclude = constraints.get("exclude", [])
        prices = data.get("prices", {})

        if not ingredients:
            return jsonify({"error": "Nem találhatók megfelelő alapanyagok."}), 400

        # Az engedélyezett sorok kiszűrése a felhasználói nevek alapján
        selected_indices = []
        for name in ingredients:
            rows = melted_names[melted_names["Name"].str.lower() == name.lower()]
            selected_indices.extend(rows["RowID"].values.tolist())

        if not selected_indices:
            return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

        selected_df = ingredient_data.loc[selected_indices].copy()
        selected_df["Name"] = melted_names.set_index("RowID").loc[selected_indices]["Name"].values

        # Kizárt alapanyagok kiszűrése
        if exclude:
            selected_df = selected_df[~selected_df["Name"].isin(exclude)]

        if selected_df.empty:
            return jsonify({"error": "A megadott alapanyagokkal nem érhető el az optimális keverék. Próbáljon meg több vagy más alapanyagot."}), 400

        # Célérték vektor
        b = np.array([target_values[n] for n in nutrients])
        A = selected_df[nutrients].T.values  # (8 x N)
        c = [prices.get(name, 0.0) for name in selected_df["Name"]]

        bounds = []
        for name in selected_df["Name"]:
            max_val = max_amounts.get(name, 100)
            bounds.append((0, max_val))

        # Optimalizálás
        result = linprog(c=c, A_eq=A, b_eq=b, bounds=bounds, method="highs")

        if result.success:
            quantities = result.x
            recommendation = []
            for name, qty in zip(selected_df["Name"], quantities):
                if qty > 0.0001:
                    recommendation.append({"name": name, "quantity": round(qty, 2)})

            response = {
                "recommendation": recommendation,
                "species": species,
                "target_nutrition": target_values,
            }

            # PDF generálás
            if data.get("generate_pdf", False):
                pdf_bytes = generate_pdf(response)
                response["pdf_base64"] = pdf_bytes.decode("utf-8")

            return jsonify(response)
        else:
            return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
