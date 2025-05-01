from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # Excel beolvasása kisbetűs munkalapról
        excel_path = 'Takarmany_kalkulator.xlsx'
        df = pd.read_excel(excel_path, sheet_name='adatbazis')

        # Csak a nem hiányzó kulcsoszlopokkal dolgozunk
        df = df.dropna(subset=[
            "ME MJ/kg", "Nyers fehérje", "Nyers zsír min.",
            "Nyers rost", "Kalcium", "Foszfor", "Lizin", "Metionin"
        ])

        response = {
            "message": "Sikeres Excel-beolvasás az 'adatbazis' munkalapról.",
            "sorok_szama": len(df)
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": f"Hiba: {str(e)}"}), 500


@app.route('/', methods=['GET'])
def home():
    return "Takarmány Kalkulátor API működik."

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=10000)
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # Excel beolvasása kisbetűs munkalapról
        excel_path = 'Takarmany_kalkulator.xlsx'
        df = pd.read_excel(excel_path, sheet_name='adatbazis')

        # Csak a nem hiányzó kulcsoszlopokkal dolgozunk
        df = df.dropna(subset=[
            "ME MJ/kg", "Nyers fehérje", "Nyers zsír min.",
            "Nyers rost", "Kalcium", "Foszfor", "Lizin", "Metionin"
        ])

        response = {
            "message": "Sikeres Excel-beolvasás az 'adatbazis' munkalapról.",
            "sorok_szama": len(df)
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": f"Hiba: {str(e)}"}), 500


@app.route('/', methods=['GET'])
def home():
    return "Takarmány Kalkulátor API működik."

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=10000)
