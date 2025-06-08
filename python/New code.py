# -*- coding: utf-8 -*-
"""
Created on Thu Jun  5 15:50:11 2025

@author: junio
"""



import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import multivariate_normal
import os

# 1. Paramètres initiaux
startdate = "1999Q4"
endsmpl = "2045Q4"
endate = "2023Q4"
startsim0m1 = "2021"
startsim0 = "2023"
startsim1 = "2024"
endsim = "2028Q4"
endadjust = "2028"
endeval = "2033"
pays = "es"
nsim = 100
w = 20  # horizon projection (5 ans * 4 trimestres)

# 2. Chargement des données
chemin_fichier = "C:/Users/junio/Documents/M1 DATA Semester2/Capstone/ultime/convertFile.xlsx"

# Charger les données
df = pd.read_excel(chemin_fichier, sheet_name="Sheet1")
df['date'] = pd.to_datetime(df['dateid01'])
df.set_index('date', inplace=True)

# Sélection des colonnes pour le pays
df_country = df[[col for col in df.columns if col.endswith(f"_{pays}")]].copy()

# 3. Winsorisation
groups = ["soldep_p", "stn_3m", "ltn_10y", "g_v_yoy"]
trimmed = {}

for var in groups:
    col = f"{var}_bkcom_000_{pays}"
    q5 = df_country[col].quantile(0.05)
    q95 = df_country[col].quantile(0.95)
    trimmed_series = df_country[col].clip(lower=q5, upper=q95)
    trimmed[f"{var}_trimmed"] = trimmed_series

# Conversion des taux en proportions
trimmed["stn_3m_trimmed"] /= 100
trimmed["ltn_10y_trimmed"] /= 100

# 4. Chocs historiques
shock_hist = {}
for var in groups:
    shock_hist[f"shock_hist_{var}"] = trimmed[f"{var}_trimmed"].diff()

shock_df = pd.DataFrame(shock_hist).dropna()
cov = shock_df.cov(ddof=1)

if np.isnan(cov.values).any() or np.isinf(cov.values).any():
    raise ValueError("❌ Matrice de covariance invalide : contient des NaNs ou des Infs.")

# 5. Simulation des chocs via Monte Carlo - Version corrigée
ann_results = {var: np.zeros((nsim, 5)) for var in groups}
ann_ltn_10y = np.zeros((nsim, 5))
matrix_test = np.zeros((nsim, 5))
maturity = 5  # constante fixée

np.random.seed(123456)
for j in range(nsim):
    epsn = multivariate_normal.rvs(mean=np.zeros(4), cov=cov, size=w)
    eps_df = pd.DataFrame(epsn, columns=[f"eps_{v}" for v in groups])
    
    for i_var, var in enumerate(groups):
        acc_eps = eps_df[f"eps_{var}"].cumsum().values
        ann_results[var][j, 0] = acc_eps[3]
        if var == "ltn_10y":
            ann_ltn_10y[j, 0] = acc_eps[3] * 1 / maturity
        for i in range(1, 5):
            ann_results[var][j, i] = acc_eps[4*(i+1)-1] - acc_eps[4*i-1]
            if var == "ltn_10y":
                ann_ltn_10y[j, i] = acc_eps[4*(i+1)-1] * (i+1) / maturity
    
    # Calcul exact comme dans Eviews
    test = eps_df["eps_ltn_10y"].cumsum().values
    for k in range(5):
        matrix_test[j, k] = test[4*(k+1)-1] * (k+1) / maturity

ann_ltn_10y = matrix_test.copy()

# 6. Préparation des données annuelles - Version corrigée
annual_data = {}

# Liste complète des variables à charger
variables_to_load = [
    "soldep_p", "stn_3m", "ltn_10y", "g_v_yoy",
    "iir", "mal_p", "dda"
]

for var in variables_to_load:
    key = f"{var}_bkcom_000_{pays}"
    if key in df_country.columns:
        resampled = df_country[key].resample("YE").last()
        if var in ["iir", "mal_p"]:
            annual_data[key] = resampled.values / 100
        elif var == "dda":
            annual_data[key] = resampled.values
        else:
            annual_data[key] = resampled.values / 100

# Initialisation explicite des variables alpha (absentes du fichier)
annual_data[f"alphact_{pays}"] = np.array([0.25])  # Valeur par défaut
annual_data[f"alphalt_{pays}"] = np.array([0.75])  # Valeur par défaut

# Vérification des données chargées
print("\nVariables chargées :")
for key in annual_data:
    print(f"{key}: {annual_data[key][:5]}...")  # Affiche les 5 premières valeurs
    
    
# # --- BLOC 7 - Simulation des trajectoires --- (Version Corrigée)

# Initialisation des résultats
groups2 = ["soldep_p", "stn_3m", "ltn_10y", "g_v_yoy", "tx_moy", "dette_iir"]
sim_results = {var: np.zeros((nsim, 5)) for var in groups2}

# Vérification des données requises
required_data = [
    f"soldep_p_bkcom_000_{pays}",
    f"stn_3m_bkcom_000_{pays}",
    f"ltn_10y_bkcom_000_{pays}",
    f"g_v_yoy_bkcom_000_{pays}",
    f"iir_bkcom_000_{pays}",
    f"alphact_{pays}",
    f"alphalt_{pays}"
]

for key in required_data:
    if key not in annual_data:
        raise ValueError(f"Donnée manquante: {key}")

# Simulation principale
for j in range(nsim):
    for k in range(5):
        try:
            # Calcul des variables de base
            sim_results["soldep_p"][j, k] = annual_data[f"soldep_p_bkcom_000_{pays}"][k] + ann_results["soldep_p"][j, k]
            sim_results["stn_3m"][j, k] = annual_data[f"stn_3m_bkcom_000_{pays}"][k] + ann_results["stn_3m"][j, k]
            sim_results["ltn_10y"][j, k] = annual_data[f"ltn_10y_bkcom_000_{pays}"][k] + ann_ltn_10y[j, k]
            sim_results["g_v_yoy"][j, k] = annual_data[f"g_v_yoy_bkcom_000_{pays}"][k] + ann_results["g_v_yoy"][j, k]
            
            # Calcul du taux moyen avec vérification de positivité
            tx_moy = (
                annual_data[f"iir_bkcom_000_{pays}"][k] +
                annual_data[f"alphalt_{pays}"][0] * ann_ltn_10y[j, k] +
                annual_data[f"alphact_{pays}"][0] * ann_results["stn_3m"][j, k]
            )
            sim_results["tx_moy"][j, k] = max(tx_moy, 0)
            
        except IndexError as e:
            print(f"Erreur d'indice - Année {2023+k}: {str(e)}")
            print("Vérifiez que vos données couvrent bien 2023-2028")
            raise

# 8. Calcul de la dette - Version corrigée
dettem1 = annual_data[f"mal_p_bkcom_000_{pays}"][0]  # valeur initiale

for j in range(nsim):
    sim_results["dette_iir"][j, 0] = dettem1 * (1 + sim_results["tx_moy"][j, 0]) / (1 + sim_results["g_v_yoy"][j, 0]) - sim_results["soldep_p"][j, 0]
    for k in range(1, 5):
        sim_results["dette_iir"][j, k] = (
            sim_results["dette_iir"][j, k-1] * (1 + sim_results["tx_moy"][j, k]) / 
            (1 + sim_results["g_v_yoy"][j, k]) - sim_results["soldep_p"][j, k] +
            annual_data[f"dda_bkcom_000_{pays}"][k] / 100
        )

# 9. Quantiles pour Fan Charts - Version corrigée
quantiles = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
quantile_results = {}

for var in groups2:
    quantile_results[var] = {f"q{int(q*100)}": np.quantile(sim_results[var], q=q, axis=0) for q in quantiles}

# 10. Génération des fan charts - Version améliorée
def create_fan_chart(var_name, baseline=None):
    plt.figure(figsize=(12, 6))
    years = np.arange(2023, 2028)
    
    # Ordre inverse pour un meilleur rendu visuel
    plt.fill_between(years, quantile_results[var_name]["q5"], quantile_results[var_name]["q95"], 
                     color="#b9b9ff", alpha=0.7, label="5%-95%")
    plt.fill_between(years, quantile_results[var_name]["q10"], quantile_results[var_name]["q90"], 
                     color="#8888ff", alpha=0.7, label="10%-90%")
    plt.fill_between(years, quantile_results[var_name]["q20"], quantile_results[var_name]["q80"], 
                     color="#4444ff", alpha=0.7, label="20%-80%")
    plt.fill_between(years, quantile_results[var_name]["q30"], quantile_results[var_name]["q70"], 
                     color="#2121ff", alpha=0.7, label="30%-70%")
    plt.fill_between(years, quantile_results[var_name]["q40"], quantile_results[var_name]["q60"], 
                     color="#1414ff", alpha=0.7, label="40%-60%")
    
    # Ligne médiane
    plt.plot(years, quantile_results[var_name]["q50"], color="black", 
             linewidth=2, label="Médiane")
    
    # Baseline si fournie
    if baseline is not None:
        plt.plot(years, baseline[:5], color="green", linestyle="--", 
                 linewidth=2, label="Baseline")
    
    plt.title(f"Fan Chart - {var_name.upper()} ({pays.upper()})", fontsize=14)
    plt.xlabel("Année", fontsize=12)
    plt.ylabel("Valeur", fontsize=12)
    
    # Légende améliorée
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # Sauvegarde automatique
    plt.savefig(f"fan_chart_{var_name}_{pays}.png", dpi=300, bbox_inches='tight')
    plt.show()