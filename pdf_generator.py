from fpdf import FPDF
import tempfile
import os

def generate_pdf(recommendation, species, target_nutrition):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Takarmánykeverék ajánlás", ln=True, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Faj: {species}", ln=True)

    pdf.ln(5)
    pdf.cell(200, 10, txt="Cél tápanyagértékek:", ln=True)
    for key, value in target_nutrition.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)

    pdf.ln(5)
    pdf.cell(200, 10, txt="Ajánlott keverék (kg):", ln=True)
    for key, value in recommendation.items():
        pdf.cell(200, 10, txt=f"{key}: {round(value, 3)} kg", ln=True)

    # Ideiglenes fájl mentése
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name
