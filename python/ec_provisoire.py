# -*- coding: utf-8 -*-
"""
Created on Sat Jun  7 15:36:15 2025

@author: junio
"""


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import multivariate_normal

# Paramètres
pays = "es"
nsim = 100
w = 20  # 5 ans * 4 trimestres
maturity = 5

# Chargement des données
chemin = "C:/Users/junio/Documents/M1 DATA Semester2/Capstone/ultime/convertFile.xlsx"
df = pd.read_excel(chemin, sheet_name="Sheet1")
df["date"] = pd.to_datetime(df["dateid01"])
df.set_index("date", inplace=True)
df_country = df[[col for col in df.columns if col.endswith(f"_{pays}")]].copy()

# Winsorisation
groups = ["soldep_p", "stn_3m", "ltn_10y", "g_v_yoy"]
trimmed = {}
for var in groups:
    col = f"{var}_bkcom_000_{pays}"
    q5, q95 = df_country[col].quantile([0.05, 0.95])
    series = df_country[col].clip(lower=q5, upper=q95)
    trimmed[f"{var}_trimmed"] = series / 100 if var in ["stn_3m", "ltn_10y"] else series

# Chocs historiques
shock_df = pd.DataFrame({f"shock_hist_{v}": trimmed[f"{v}_trimmed"].diff() for v in groups}).dropna()
cov = shock_df.cov()

# Simulation Monte Carlo
ann_results = {v: np.zeros((nsim, 5)) for v in groups}
ann_ltn_10y = np.zeros((nsim, 5))
np.random.seed(123456)
for j in range(nsim):
    epsn = multivariate_normal.rvs(mean=np.zeros(4), cov=cov, size=w)
    eps_df = pd.DataFrame(epsn, columns=[f"eps_{v}" for v in groups])
    
    for i, v in enumerate(groups):
        acc = eps_df[f"eps_{v}"].cumsum().values
        
        # Annualisation des chocs (corrigée pour correspondre à EViews)
        for y in range(5):  # années 1 à 5 (2023-2027)
            if v == "ltn_10y":
                # Traitement spécial pour les taux longs (cumul sur 5 ans)
                ann_ltn_10y[j, y] = acc[4*(y+1)-1] * (y+1) / maturity
            else:
                if y == 0:  # première année (4 premiers trimestres)
                    ann_results[v][j, y] = acc[3]  # Q4 de la première année
                else:
                    ann_results[v][j, y] = acc[4*(y+1)-1] - acc[4*y-1]  # différence entre années

# Préparation des données annuelles (corrigée pour l'alignement temporel)
annual_data = {}
resample = lambda k, div=1: df_country[k].resample("YE").last().dropna().values / div

# On prend les données de 2021 à 2027 (7 points pour correspondre à EViews)
annual_data[f"soldep_p_bkcom_000_{pays}"] = resample(f"soldep_p_bkcom_000_{pays}", 100)[-7:]
annual_data[f"stn_3m_bkcom_000_{pays}"] = resample(f"stn_3m_bkcom_000_{pays}", 100)[-7:]
annual_data[f"ltn_10y_bkcom_000_{pays}"] = resample(f"ltn_10y_bkcom_000_{pays}", 100)[-7:]
annual_data[f"g_v_yoy_bkcom_000_{pays}"] = resample(f"g_v_yoy_bkcom_000_{pays}", 100)[-7:]
annual_data[f"iir_bkcom_000_{pays}"] = resample(f"iir_bkcom_000_{pays}", 100)[-7:]
annual_data[f"mal_p_bkcom_000_{pays}"] = resample(f"mal_p_bkcom_000_{pays}", 100)[-7:]
annual_data[f"dda_bkcom_000_{pays}"] = resample(f"dda_bkcom_000_{pays}", 1)[-7:]
annual_data[f"alphalt_{pays}"] = np.array([0.75])
annual_data[f"alphact_{pays}"] = np.array([0.25])

# Simulation des trajectoires (corrigée pour l'alignement temporel)
sim_results = {v: np.zeros((nsim, 5)) for v in groups + ["tx_moy", "dette_iir"]}
dettem1 = annual_data[f"mal_p_bkcom_000_{pays}"][1]  # valeur de 2022 (dette initiale)

for j in range(nsim):
    for k in range(5):  # années 1 à 5 (2023-2027)
        # Indice k+2 car les données commencent en 2021
        sim_results["soldep_p"][j, k] = annual_data[f"soldep_p_bkcom_000_{pays}"][k+2] + ann_results["soldep_p"][j, k]
        sim_results["stn_3m"][j, k] = annual_data[f"stn_3m_bkcom_000_{pays}"][k+2] + ann_results["stn_3m"][j, k]
        sim_results["ltn_10y"][j, k] = annual_data[f"ltn_10y_bkcom_000_{pays}"][k+2] + ann_ltn_10y[j, k]
        sim_results["g_v_yoy"][j, k] = annual_data[f"g_v_yoy_bkcom_000_{pays}"][k+2] + ann_results["g_v_yoy"][j, k]
        
        # Calcul du taux moyen avec contrainte de positivité
        tx_moy = (
            annual_data[f"iir_bkcom_000_{pays}"][k+2] +
            annual_data[f"alphalt_{pays}"][0] * ann_ltn_10y[j, k] +
            annual_data[f"alphact_{pays}"][0] * ann_results["stn_3m"][j, k]
        )
        sim_results["tx_moy"][j, k] = max(tx_moy, 0)

# Calcul de la dette (corrigé pour correspondre à EViews)
for j in range(nsim):
    # Première année (2023)
    sim_results["dette_iir"][j, 0] = (
        dettem1 * (1 + sim_results["tx_moy"][j, 0]) / (1 + sim_results["g_v_yoy"][j, 0]) -
        sim_results["soldep_p"][j, 0]
    )
    
    # Années suivantes (2024-2027)
    for k in range(1, 5):
        sim_results["dette_iir"][j, k] = (
            sim_results["dette_iir"][j, k-1] * (1 + sim_results["tx_moy"][j, k]) / 
            (1 + sim_results["g_v_yoy"][j, k]) - 
            sim_results["soldep_p"][j, k] +
            annual_data[f"dda_bkcom_000_{pays}"][k+2] / 100
        )

# Calcul des quantiles
quantiles = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
quantile_results = {var: {f"q{int(q*100)}": np.quantile(sim_results[var], q=q, axis=0) for q in quantiles} for var in sim_results}

# Fonction de fan chart améliorée
def create_fan_chart(var, baseline=None):
    years = np.arange(2023, 2028)
    plt.figure(figsize=(10, 6))
    
    # Ajout du point de départ historique
    if baseline is not None:
        hist_value = baseline[2]  # valeur de 2023
        plt.plot([2022], [hist_value], 'ko', label='Départ historique')
    
    # Bandes de confiance
    for qlow, qhigh, color in [(5, 95, '#b9b9ff'), (10, 90, '#8888ff'), 
                              (20, 80, '#6666ff'), (30, 70, '#4444ff'), 
                              (40, 60, '#2222ff')]:
        lower = quantile_results[var][f"q{qlow}"]
        upper = quantile_results[var][f"q{qhigh}"]
        plt.fill_between(years, lower, upper, color=color, alpha=0.7)
    
    # Médiane
    plt.plot(years, quantile_results[var]["q50"], color="black", label="Médiane")
    
    # Baseline (si fournie)
    if baseline is not None:
        plt.plot(years, baseline[2:7], linestyle="--", color="green", label="Baseline")
    
    plt.title(f"Fan Chart - {var.upper()} ({pays.upper()})")
    plt.xlabel("Année")
    plt.ylabel("Valeur")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# Lancer les graphiques avec le point de départ correct
create_fan_chart("dette_iir", annual_data[f"mal_p_bkcom_000_{pays}"])
create_fan_chart("soldep_p", annual_data[f"soldep_p_bkcom_000_{pays}"])
create_fan_chart("stn_3m", annual_data[f"stn_3m_bkcom_000_{pays}"])
create_fan_chart("ltn_10y", annual_data[f"ltn_10y_bkcom_000_{pays}"])
create_fan_chart("g_v_yoy", annual_data[f"g_v_yoy_bkcom_000_{pays}"])
create_fan_chart("tx_moy", annual_data[f"iir_bkcom_000_{pays}"])

print("\u2705 Simulation terminée et fan charts générés.")