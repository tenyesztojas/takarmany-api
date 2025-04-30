from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from scipy.optimize import linprog
from pdf_generator import generate_pdf

app = Flask(__name__)

@app.route("/")
def home():
    return "Tenyésztojás takarmánykalkulátor API"

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.json
        species = data.get("species")
        ingredients = data.get("ingredients", [])
        constraints = data.get("constraints", {})
        prices = data.get("prices", {})
        exclude = data.get("exclude", [])

        if not species or not ingredients:
            return jsonify({"error": "Hiányzó faj vagy alapanyaglista."}), 400

        # Excel fájl betöltése (új fájlnév!)
        excel_path = "Takarmany_kalkulator.xlsx"
        sheet_name = "Adatbázis"
        ingredient_data = pd.read_excel(excel_path, sheet_name=sheet_name)

        # Alapanyagnevek beolvasása az N-O-P oszlopból
        melted_names = ingredient_data[["RowID", "N", "O", "P"]].melt(id_vars="RowID", value_name="Name").dropna()
        valid_names = melted_names["Name"].astype(str).str.lower().tolist()

        # Részleges egyezés alapján kiválasztott alapanyagok
        selected = []
        for user_input in ingredients:
            match = next((n for n in valid_names if user_input.lower() in n), None)
            if match:
                selected.append(match)

        if not selected:
            return jsonify({"error": "Nem találhatóak megfelelő alapanyagok."}), 400

        df = ingredient_data.copy()
        df["Name"] = (
            df[["N", "O", "P"]]
            .astype(str)
            .agg(" ".join, axis=1)
            .str.lower()
        )

        df = df[df["Name"].apply(lambda name: any(term.lower() in name for term in selected))]
        if df.empty:
            return jsonify({"error": "Nincs kiválasztott alapanyag."}), 400

        # Tápanyagcélok fajonként
        target_nutrition = {
            "tyúk": {"protein": 16, "energy": 11.5, "fiber": 5},
            "kacsa": {"protein": 17, "energy": 11.7, "fiber": 6},
        }

        if species not in target_nutrition:
            return jsonify({"error": "Ismeretlen faj."}), 400

        protein = df["Nyers fehérje"]
        energy = df["ME MJ/kg"]
        fiber = df["Nyers rost"]
        cost = df["Ft/Kg"].fillna(9999)

        num_vars = len(df)
        c = cost.to_numpy()
        A = [
            -protein.to_numpy(),
            -energy.to_numpy(),
            fiber.to_numpy()
        ]
        b = [
            -target_nutrition[species]["protein"],
            -target_nutrition[species]["energy"],
            target_nutrition[species]["fiber"]
        ]

        bounds = [(0, None)] * num_vars

        # Felhasználói korlátozások
        if "max_amount" in constraints:
            for name, max_kg in constraints["max_amount"].items():
                for i, row in df.iterrows():
                    if name.lower() in row["Name"]:
                        bounds[i] = (0, float(max_kg))

        if "exclude" in data:
            for name in exclude:
                for i, row in df.iterrows():
                    if name.lower() in row["Name"]:
                        bounds[i] = (0, 0)

        if "prices" in data:
            for name, price in prices.items():
                for i, row in df.iterrows():
                    if name.lower() in row["Name"]:
                        c[i] = float(price)

        res = linprog(c, A_ub=A, b_ub=b, bounds=bounds, method="highs")
        if res.success:
            df["Mennyiség (kg)"] = res.x.round(2)
            df = df[df["Mennyiség (kg)"] > 0]

            összes = df["Mennyiség (kg)"].sum()
            fehérje = (df["Nyers fehérje"] * df["Mennyiség (kg)"]).sum() / összes
            energia = (df["ME MJ/kg"] * df["Mennyiség (kg)"]).sum() / összes
            rost = (df["Nyers rost"] * df["Mennyiség (kg)"]).sum() / összes

            pdf = generate_pdf(df, species, fehérje, energia, rost)
            return jsonify({
                "recommendation": df[["Name", "Mennyiség (kg)"]].to_dict(orient="records"),
                "target_nutrition": {
                    "protein": round(fehérje, 2),
                    "energy": round(energia, 2),
                    "fiber": round(rost, 2)
                },
                "pdf_base64": pdf
            })

        return jsonify({"error": "Nem sikerült optimalizálni az arányokat."}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
