# app.py
from flask import Flask, request, render_template
import pandas as pd
import numpy as np
from scipy.optimize import minimize

app = Flask(__name__)

targets = {
    'tojó tyúk': {
        'Nyers fehérje': (16, 18),
        'Nyers zsír min.': (3, 5),
        'Nyers rost': (4, 5),
        'Lizin': (0.7, 0.8),
        'Metionin': (0.3, 0.35),
        'Kalcium': (3.5, 3.5),
        'Foszfor': (0.35, 0.45),
        'ME MJ/kg': (11, 12)
    },
    'tojó fürj': {
        'Nyers fehérje': (23, 25),
        'Nyers zsír min.': (3, 5),
        'Nyers rost': (3, 4),
        'Lizin': (1.4, 1.5),
        'Metionin': (0.35, 0.4),
        'Kalcium': (2.5, 3.0),
        'Foszfor': (0.6, 0.8),
        'ME MJ/kg': (11, 12)
    }
}

# Alapanyag-adatbázis betöltése
feed_data = pd.read_excel("Takarmany_kalkulator.xlsx")
feed_data.fillna(0, inplace=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        faj = request.form['faj']
        alapanyagok = request.form['alapanyagok'].lower().split(',')
        szójamentes = 'szójamentes' in request.form

        # Szűrés a megadott alapanyagokra
        df = feed_data[feed_data['Takarmány alapanyag'].str.lower().apply(
            lambda x: any(ingredient.strip() in x for ingredient in alapanyagok)
        )].copy()

        if szójamentes:
            df = df[~df['Takarmány alapanyag'].str.lower().str.contains('szója')]

        if df.empty:
            result = 'Nincs elérhető alapanyag a megadott listából.'
        else:
            nutrient_cols = list(targets[faj].keys())
            A = df[nutrient_cols].to_numpy().T
            maxima = df['Maximum mennyiség takarmánykeverékben'].values * 100
            bounds = [(0, max_v) for max_v in maxima]
            x0 = np.ones(len(df)) * (100 / len(df))

            def objective(x):
                total_weight = np.sum(x)
                blend = A @ x / total_weight
                error = 0
                for i, (low, high) in enumerate(targets[faj].values()):
                    target = (low + high) / 2
                    error += (blend[i] - target) ** 2
                return error

            constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 100}]
            res = minimize(objective, x0, bounds=bounds, constraints=constraints)

            if res.success:
                df_result = pd.DataFrame({
                    'Alapanyag': df['Takarmány alapanyag'],
                    'Mennyiség (kg)': res.x
                })
                result = df_result[df_result['Mennyiség (kg)'] > 0.1].round(2).to_html(index=False)
            else:
                result = 'Nem sikerült optimális keveréket számolni.'

    return render_template('index.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
