
from fpdf import FPDF

class FeedPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Takarmánykeverék Ajánlás", border=False, ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Oldal {self.page_no()}", align="C")

    def add_mix_table(self, mix, amount_kg):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, f"{amount_kg} kg keverék", ln=True)
        self.set_font("Arial", "", 10)
        self.cell(60, 8, "Alapanyag", border=1)
        self.cell(30, 8, "Mennyiség (kg)", border=1)
        self.cell(30, 8, "Arány (%)", border=1)
        self.cell(30, 8, "Fehérje (%)", border=1)
        self.cell(30, 8, "Energia (MJ)", border=1)
        self.ln()

        for item in mix:
            self.cell(60, 8, item["ingredient"], border=1)
            self.cell(30, 8, f'{item["amount_kg"]}', border=1)
            self.cell(30, 8, f'{round(item["ratio"] * 100, 1)}', border=1)
            self.cell(30, 8, f'{item["protein"]}', border=1)
            self.cell(30, 8, f'{item["energy"]}', border=1)
            self.ln()
        self.ln(5)

def create_pdf(recommendation, species, target_nutrition, output_path="takarmany_ajanlas.pdf"):
    pdf = FeedPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Faj: {species.title()}", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Cél tápértékek: {target_nutrition}", ln=True)
    pdf.ln(5)

    for key, mix in recommendation.items():
        amount = int(key.split("_")[0])
        pdf.add_mix_table(mix, amount)

    pdf.output(output_path)
    return output_path
