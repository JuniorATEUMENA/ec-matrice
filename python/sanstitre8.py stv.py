# -*- coding: utf-8 -*-
"""
Created on Fri Jun  6 14:29:56 2025

@author: junio
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import multivariate_normal

# 1. Paramètres initiaux
pays = "es"
nsim = 100
w = 20
maturity = 5

# 2. Chargement des données
chemin_fichier = "C:/Users/junio/Documents/M1 DATA Semester2/Capstone/ultime/convertFile.xlsx"
df = pd.read_excel(chemin_fichier, sheet_name="Sheet1")
df['date'] = pd.to_datetime(df['dateid01'])
df.set_index('date', inplace=True)

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

# 5. Simulation des chocs via Monte Carlo
ann_results = {var: np.zeros((nsim, 5)) for var in groups}
ann_ltn_10y = np.zeros((nsim, 5))
matrix_test = np.zeros((nsim, 5))

np.random.seed(123456)
for j in range(nsim):
    epsn = multivariate_normal.rvs(mean=np.zeros(4), cov=cov, size=w)
    eps_df = pd.DataFrame(epsn, columns=[f"eps_{v}" for v in groups])

    for i_var, var in enumerate(groups):
        acc_eps = eps_df[f"eps_{var}"].cumsum().values
        ann_results[var][j, 0] = acc_eps[3]
        if var == "ltn_10y":
            ann_ltn_10y[j, 0] = acc_eps[3] / maturity
        for i in range(1, 5):
            ann_results[var][j, i] = acc_eps[4*(i+1)-1] - acc_eps[4*i-1]
            if var == "ltn_10y":
                ann_ltn_10y[j, i] = acc_eps[4*(i+1)-1] * (i+1) / maturity

    matrix_test[j, :] = [eps_df["eps_ltn_10y"].iloc[:4*(k+1)].sum() * (k+1) / maturity for k in range(5)]

ann_ltn_10y = matrix_test.copy()

# 6. Données annuelles observées (baseline)
annual_data = {}
variables_to_load = ["soldep_p", "stn_3m", "ltn_10y", "g_v_yoy", "iir", "mal_p", "dda"]

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

# Alpha fixés
annual_data[f"alphact_{pays}"] = np.array([0.25])
annual_data[f"alphalt_{pays}"] = np.array([0.75])

# 🔍 Vérifie longueurs
print("\n✅ Vérification des longueurs des séries annuelles :")
for var in variables_to_load:
    key = f"{var}_bkcom_000_{pays}"
    if key in annual_data:
        print(f"{key} : {len(annual_data[key])} valeurs")

# Allonge si nécessaire
for key in annual_data:
    if len(annual_data[key]) < 6:
        last_val = annual_data[key][-1]
        repeat = 6 - len(annual_data[key])
        print(f"⚠️ Série étendue : {key} (ajout de {repeat} valeurs)")
        annual_data[key] = np.concatenate([annual_data[key], [last_val]*repeat])

# 7. Simulation trajectoires
groups2 = ["soldep_p", "stn_3m", "ltn_10y", "g_v_yoy", "tx_moy", "dette_iir"]
sim_results = {var: np.zeros((nsim, 5)) for var in groups2}

for j in range(nsim):
    for k in range(5):
        sim_results["soldep_p"][j, k] = annual_data[f"soldep_p_bkcom_000_{pays}"][k+1] + ann_results["soldep_p"][j, k]
        sim_results["stn_3m"][j, k] = annual_data[f"stn_3m_bkcom_000_{pays}"][k+1] + ann_results["stn_3m"][j, k]
        sim_results["ltn_10y"][j, k] = annual_data[f"ltn_10y_bkcom_000_{pays}"][k+1] + ann_ltn_10y[j, k]
        sim_results["g_v_yoy"][j, k] = annual_data[f"g_v_yoy_bkcom_000_{pays}"][k+1] + ann_results["g_v_yoy"][j, k]
        tx_moy = (
            annual_data[f"iir_bkcom_000_{pays}"][k+1] +
            annual_data[f"alphalt_{pays}"][0] * ann_ltn_10y[j, k] +
            annual_data[f"alphact_{pays}"][0] * ann_results["stn_3m"][j, k]
        )
        sim_results["tx_moy"][j, k] = max(tx_moy, 0)

# 8. Calcul dette simulée
dettem1 = annual_data[f"mal_p_bkcom_000_{pays}"][0]

for j in range(nsim):
    sim_results["dette_iir"][j, 0] = dettem1 * (1 + sim_results["tx_moy"][j, 0]) / (1 + sim_results["g_v_yoy"][j, 0]) - sim_results["soldep_p"][j, 0]
    for k in range(1, 5):
        sim_results["dette_iir"][j, k] = (
            sim_results["dette_iir"][j, k-1] * (1 + sim_results["tx_moy"][j, k]) / 
            (1 + sim_results["g_v_yoy"][j, k]) - sim_results["soldep_p"][j, k] +
            annual_data[f"dda_bkcom_000_{pays}"][k] / 100
        )

# 9. Quantiles pour fan charts
quantiles = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
quantile_results = {}
for var in groups2:
    quantile_results[var] = {
        f"q{int(q*100)}": np.quantile(sim_results[var], q=q, axis=0)
        for q in quantiles
    }

# 10. Fan charts
def create_fan_chart(var_name, baseline=None):
    plt.figure(figsize=(12, 6))
    years = np.arange(2023, 2028)

    plt.fill_between(years, quantile_results[var_name]["q5"], quantile_results[var_name]["q95"], color="#b9b9ff", label="5%-95%")
    plt.fill_between(years, quantile_results[var_name]["q10"], quantile_results[var_name]["q90"], color="#8888ff", label="10%-90%")
    plt.fill_between(years, quantile_results[var_name]["q20"], quantile_results[var_name]["q80"], color="#4444ff", label="20%-80%")
    plt.fill_between(years, quantile_results[var_name]["q30"], quantile_results[var_name]["q70"], color="#2121ff", label="30%-70%")
    plt.fill_between(years, quantile_results[var_name]["q40"], quantile_results[var_name]["q60"], color="#1414ff", label="40%-60%")
    plt.plot(years, quantile_results[var_name]["q50"], color="black", linewidth=2, label="Médiane")

    if baseline is not None:
        plt.plot(years, baseline[:5], color="green", linestyle="--", linewidth=2, label="Baseline")

    plt.title(f"Fan Chart - {var_name.upper()} ({pays.upper()})", fontsize=14)
    plt.xlabel("Année")
    plt.ylabel("Valeur")
    plt.legend(loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# Affiche les fan charts
create_fan_chart("dette_iir", annual_data[f"mal_p_bkcom_000_{pays}"])
create_fan_chart("soldep_p", annual_data[f"soldep_p_bkcom_000_{pays}"])
create_fan_chart("g_v_yoy", annual_data[f"g_v_yoy_bkcom_000_{pays}"])
create_fan_chart("ltn_10y", annual_data[f"ltn_10y_bkcom_000_{pays}"])
create_fan_chart("tx_moy", annual_data[f"iir_bkcom_000_{pays}"])

print("✅ Analyse terminée. Tous les fan charts ont été générés.")

