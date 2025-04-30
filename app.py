from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
from scipy.optimize import linprog
from pdf_generator import generate_pdf

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return 'Takarmány API működik'

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        species = data.get('species')
        ingredients = data.get('ingredients', [])
        constraints = data.get('constraints', {})
        max_amount = constraints.get('max_amount', {})
        exclude = constraints.get('exclude', [])
        prices = data.get('prices', {})
        soy_free = data.get('soy_free', False)

        # Excel beolvasása
        excel_path = 'Takarmány kalkulátor programhoz.xlsx'
        sheet_name = 'Adatbázis'
        ingredient_data = pd.read_excel(excel_path, sheet_name=sheet_name)

        # Csak a 'Fajta' nevű alapanyagokra szűrjük a táblát
        ingredient_data = ingredient_data.dropna(subset=["Fajta"], how="all").copy()

        # Alapanyagok szűrése
        ingredient_data = ingredient_data[ingredient_data["Fajta"].isin(ingredients)]

        if soy_free:
            ingredient_data = ingredient_data[~ingredient_data["Fajta"].str.contains("szója", case=False, na=False)]

        if exclude:
            ingredient_data = ingredient_data[~ingredient_data["Fajta"].isin(exclude)]

        if ingredient_data.empty:
            return jsonify({"error": "Nem találhatók megfelelő alapanyagok."}), 400

        nutrients = ["ME MJ/kg", "Nyers fehérje", "Nyers zsír min.", "Nyers rost", "Ca", "P", "Lizin", "Metionin"]
        nutrient_matrix = ingredient_data[nutrients].fillna(0).to_numpy().T
        bounds = []

        for name in ingredient_data["Fajta"]:
            min_val = 0
            max_val = max_amount.get(name, None)
            if max_val is not None:
                bounds.append((min_val, max_val))
            else:
                bounds.append((min_val, None))

        target = {
            "ME MJ/kg": 11,
            "Nyers fehérje": 17,
            "Nyers zsír min.": 3.5,
            "Nyers rost": 4.5,
            "Ca": 3.6,
            "P": 0.33,
            "Lizin": 0.68,
            "Metionin": 0.25,
        }

        target_array = np.array([target[n] for n in nutrients])
        cost = np.array([prices.get(name, 0) for name in ingredient_data["Fajta"]])

        result = linprog(
            c=cost,
            A_eq=nutrient_matrix,
            b_eq=target_array,
            bounds=bounds,
            method='highs'
        )

        if result.success:
            optimized_mix = {
                name: round(val, 2)
                for name, val in zip(ingredient_data["Fajta"], result.x)
                if val > 0
            }

            total_nutrients = nutrient_matrix @ result.x
            total_nutrients_dict = {
                nutrient: round(val, 2)
                for nutrient, val in zip(nutrients, total_nutrients)
            }

            return jsonify({
                "recommendation": optimized_mix,
                "species": species,
                "target_nutrition": target,
                "calculated_nutrition": total_nutrients_dict,
            })
        else:
            return jsonify({
                "error": "A megadott alapanyagokkal nem érhető el az optimális keverék. Próbáljon meg több vagy más alapanyagot."
            }), 400

    except Exception as e:
        return jsonify({"error": f"Hiba: {str(e)}"}), 500


@app.route('/download', methods=['POST'])
def download_pdf():
    try:
        data = request.get_json()
        filename = generate_pdf(data)
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"PDF generálási hiba: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
