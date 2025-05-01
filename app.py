from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        excel_path = "Takarmany_kalkulator.xlsx"
        sheet_name = "Adatbázis"  # ékezetes Á-val!
        ingredient_data = pd.read_excel(excel_path, sheet_name=sheet_name)

        # Minta számítás (pl. csak a nem üres sorokat listázza)
        ingredient_data = ingredient_data.dropna(subset=["ME MJ/kg", "Nyers fehérje"], how="all").copy()
        result = ingredient_data.head(5).to_dict(orient='records')

        return jsonify({"eredmény": result})

    except Exception as e:
        return jsonify({"error": f"Hiba: {str(e)}"}), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
