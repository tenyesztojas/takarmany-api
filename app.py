from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
from fpdf import FPDF
import os

app = Flask(__name__)
CORS(app)

EXCEL_PATH = "Takarmany_kalkulator.xlsx"
SHEET_NAME = "adatbazis"

# Egyszerű fajspecifikus célértékek (bővíthető CSV-ből is)
CELERTEKEK = {
    "Fürj": {"Fehérje": 23.85, "Energia": 11.5},
    "Tyúk": {"Fehérje": 17, "Energia": 11.5},
    "Pulyka": {"Fehérje": 25, "Energia": 12.5},
    "Kacsa": {"Fehérje": 17, "Energia": 11.5},
    "Liba": {"Fehérje": 16, "Energia": 10.5},
}

@app.route('/kalkulal', methods=['POST'])
def kalkulal():
    try:
        adatok = request.json
        faj = adatok.get("faj")
        alapanyagok = adatok.get("alapanyagok")  # lista

        if not faj or faj not in CELERTEKEK:
            return jsonify({"error": "Ismeretlen vagy hiányzó faj."}), 400

        if not alapanyagok:
            return jsonify({"error": "Nem adtál meg egy alapanyagot sem!"}), 400

        # Excel beolvasás
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
        df = df[df["Takarmány alapanyag"].isin(alapanyagok)]

        if df.empty:
            return jsonify({"error": "Egyik megadott alapanyag sem található az adatbázisban."}), 400

        df["Arány"] = 1 / len(df)

        # Átlag tápanyagértékek számítása
        eredmeny = {
            "Fehérje": round((df["Nyers fehérje"] * df["Arány"]).sum(), 2),
            "Energia": round((df["ME MJ/kg"] * df["Arány"]).sum(), 2)
        }

        # Recept mennyiségek kg-ban
        mennyisegek = [10, 20, 30, 50, 100]
        receptek = {}

        for m in mennyisegek:
            keverek = {
                sor["Takarmány alapanyag"]: round(sor["Arány"] * m, 2)
                for _, sor in df.iterrows()
            }
            receptek[f"{m} kg"] = keverek

        # PDF generálás
        pdf_path = create_pdf(faj, eredmeny, receptek)

        return jsonify({
            "faj": faj,
            "celertekek": CELERTEKEK[faj],
            "elert_ertekek": eredmeny,
            "receptek": receptek,
            "pdf_url": "/pdf"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/pdf')
def letolt_pdf():
    return send_file("recept.pdf", as_attachment=True)

def create_pdf(faj, eredmeny, receptek):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=f"{faj} - Takarmányrecept", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Elért fehérje: {eredmeny['Fehérje']}%, Energia: {eredmeny['Energia']} MJ/kg", ln=True)

    for mennyiseg, keverek in receptek.items():
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt=f"{mennyiseg} recept:", ln=True)
        pdf.set_font("Arial", size=12)
        for alapanyag, kg in keverek.items():
            pdf.cell(200, 10, txt=f"{alapanyag}: {kg} kg", ln=True)

    pdf.output("recept.pdf")
    return "recept.pdf"

@app.route('/')
def index():
    return jsonify({"message": "Takarmánykalkulátor API működik. Küldj POST-ot a /kalkulal végpontra."})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
