# -*- coding: utf-8 -*-
"""
Created on Sun Jun  1 23:19:40 2025

@author: junio
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import multivariate_normal
import os

# 1. Paramètres initiaux
startdate = "1999Q4"
endsmpl = "2045Q4"
endate = "2023Q4"  # fin observations trim
startsim0m1 = "2021"  # année fin observations et debut fancharts - 2
startsim0 = "2023"  # année fin observations et debut fancharts
startsim1 = "2024"  # année début projection
endsim = "2028Q4"  # fin projections trim
endadjust = "2028"  # fin période d'ajustement
endeval = "2033"  # five years after endadjust
pays = "es"
nsim = 100
w = 20  # 5-year projections (5 ans * 4 trimestres)

# 2. Chargement des données
# -------------------------
# Chemin vers le fichier de données
chemin_fichier = "C:/Users/junio/Documents/M1 DATA Semester2/Capstone/ultime/convertFile.xlsx"

# Vérification que le fichier existe
if not os.path.exists(chemin_fichier):
    raise FileNotFoundError(f"Le fichier {chemin_fichier} n'a pas été trouvé. Veuillez vérifier le chemin.")

# Fonction pour charger les données
def load_data():
    try:
        # Charger les données trimestrielles
        df = pd.read_excel(chemin_fichier,
                          sheet_name="source",
                          index_col=0,
                          parse_dates=True)
        
        # Vérifier les colonnes nécessaires
        required_cols = [f"soldep_p_{pays}", f"stn_3m_{pays}", 
                        f"ltn_10y_{pays}", f"g_v_yoy_{pays}", 
                        f"maturity_{pays}"]
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Colonnes manquantes: {missing_cols}")
            
        print("Données trimestrielles chargées avec succès")
        
        # Charger les données annuelles
        annual_df = pd.read_excel(chemin_fichier,
                                sheet_name="annual")
        
        # Colonnes requises pour les données annuelles
        annual_cols = [f"dda_bkcom_000_{pays}", f"g_v_yoy_bkcom_000_{pays}",
                      f"ltn_10y_bkcom_000_{pays}", f"soldep_p_bkcom_000_{pays}",
                      f"stn_3m_bkcom_000_{pays}", f"tx_moy_bkcom_000_{pays}",
                      f"dette_iir_bkcom_000_{pays}", f"alphact_{pays}", f"alphalt_{pays}"]
        
        missing_annual = [col for col in annual_cols if col not in annual_df.columns]
        if missing_annual:
            raise ValueError(f"Colonnes annuelles manquantes: {missing_annual}")
            
        print("Données annuelles chargées avec succès")
        
        return df, annual_df
        
    except Exception as e:
        print(f"Erreur lors du chargement des données: {str(e)}")
        exit()

# Chargement des données
df, annual_df = load_data()

# 3. Winsorize les séries (5% et 95% quantiles)
groups = ["soldep_p", "stn_3m", "ltn_10y", "g_v_yoy"]
trimmed_series = {}

for var in groups:
    col = f"{var}_{pays}"
    q5 = df[col].quantile(0.05)
    q95 = df[col].quantile(0.95)
    
    # Application de la winsorization
    trimmed = df[col].copy()
    trimmed[trimmed < q5] = q5
    trimmed[trimmed > q95] = q95
    trimmed_series[f"{var}_trimmed"] = trimmed

# Conversion des taux en proportions
trimmed_series["stn_3m_trimmed"] = trimmed_series["stn_3m_trimmed"] / 100
trimmed_series["ltn_10y_trimmed"] = trimmed_series["ltn_10y_trimmed"] / 100

# 4. Construction des chocs historiques
shock_hist = {}
for var in groups:
    shock_hist[f"shock_hist_{var}"] = trimmed_series[f"{var}_trimmed"].diff().dropna()

shock_df = pd.DataFrame(shock_hist).loc["2000-01-01":"2023-10-01"]
cov = shock_df.cov(ddof=1)  # Matrice de covariance

# 5. Simulations des chocs aléatoires
np.random.seed(123456)
ann_results = {var: np.zeros((nsim, 5)) for var in groups}
ann_ltn_10y = np.zeros((nsim, 5))
matrix_test = np.zeros((nsim, 5))

maturity = df[f'maturity_{pays}'].iloc[-1]  # Dernière valeur de la maturité

for j in range(nsim):
    np.random.seed(123456 + j + 1)
    epsn = multivariate_normal.rvs(mean=np.zeros(4), cov=cov, size=w)
    eps_df = pd.DataFrame(epsn, columns=[f"eps_{var}" for var in groups])
    
    for i_var, var in enumerate(groups):
        acc_eps = eps_df[f"eps_{var}"].cumsum().values
        ann_results[var][j, 0] = acc_eps[3]
        if var == "ltn_10y":
            ann_ltn_10y[j, 0] = acc_eps[3] * 1 / maturity
        
        for i in range(1, 5):
            ann_results[var][j, i] = acc_eps[4*(i+1)-1] - acc_eps[4*i-1]
            if var == "ltn_10y":
                ann_ltn_10y[j, i] = acc_eps[4*(i+1)-1] * (i+1) / maturity
    
    # Traitement spécial pour ltn_10y
    testi = np.zeros(5)
    for k in range(5):
        testi[k] = eps_df["eps_ltn_10y"].iloc[:4*(k+1)].sum() * (k+1) / maturity
    matrix_test[j, :] = testi

ann_ltn_10y = matrix_test.copy()

# 6. Préparation des données annuelles de référence
annual_data = {}
for var in ["soldep_p", "stn_3m", "ltn_10y", "g_v_yoy", "tx_moy", "dette_iir"]:
    annual_data[f"{var}_bkcom_000_{pays}"] = annual_df[f"{var}_bkcom_000_{pays}"].values / 100

annual_data["dda_bkcom_000_es"] = annual_df[f"dda_bkcom_000_{pays}"].values
annual_data[f"alphact_{pays}"] = annual_df[f"alphact_{pays}"].values
annual_data[f"alphalt_{pays}"] = annual_df[f"alphalt_{pays}"].values

dettem1 = annual_data[f"dette_iir_bkcom_000_{pays}"][0]

# 7. Simulation des trajectoires avec chocs
groups2 = ["soldep_p", "stn_3m", "ltn_10y", "g_v_yoy", "tx_moy", "dette_iir"]
sim_results = {var: np.zeros((nsim, 5)) for var in groups2}

for j in range(nsim):
    for k in range(5):
        sim_results["soldep_p"][j, k] = annual_data[f"soldep_p_bkcom_000_{pays}"][k+1] + ann_results["soldep_p"][j, k]
        sim_results["stn_3m"][j, k] = annual_data[f"stn_3m_bkcom_000_{pays}"][k+1] + ann_results["stn_3m"][j, k]
        sim_results["ltn_10y"][j, k] = annual_data[f"ltn_10y_bkcom_000_{pays}"][k+1] + ann_ltn_10y[j, k]
        sim_results["g_v_yoy"][j, k] = annual_data[f"g_v_yoy_bkcom_000_{pays}"][k+1] + ann_results["g_v_yoy"][j, k]
        
        tx_moy = (annual_data[f"tx_moy_bkcom_000_{pays}"][k+1] + 
                 annual_data[f"alphalt_{pays}"][0] * ann_ltn_10y[j, k] + 
                 annual_data[f"alphact_{pays}"][0] * ann_results["stn_3m"][j, k])
        sim_results["tx_moy"][j, k] = tx_moy if tx_moy > 0 else 0

# 8. Calcul des trajectoires de dette
for j in range(nsim):
    sim_results["dette_iir"][j, 0] = (dettem1 * (1 + sim_results["tx_moy"][j, 0]) / (1 + sim_results["g_v_yoy"][j, 0]) - sim_results["soldep_p"][j, 0]
    
    for k in range(1, 5):
        sim_results["dette_iir"][j, k] = (sim_results["dette_iir"][j, k-1] * 
                                         (1 + sim_results["tx_moy"][j, k]) / 
                                         (1 + sim_results["g_v_yoy"][j, k]) - 
                                         sim_results["soldep_p"][j, k] + 
                                         annual_data[f"dda_bkcom_000_{pays}"][k] / 100)

# 9. Calcul des quantiles pour les fan charts
quantiles = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
quantile_results = {}

for var in groups2:
    quantile_results[var] = {}
    for q in quantiles:
        quantile_results[var][f"q{int(q*100)}"] = np.quantile(sim_results[var], q=q, axis=0)

# 10. Création des fan charts
def create_fan_chart(var_name, baseline_values=None):
    plt.figure(figsize=(12, 7))
    years = np.arange(2023, 2028)
    
    # Bandes du fan chart
    plt.fill_between(years, quantile_results[var_name]["q5"], quantile_results[var_name]["q95"], 
                    color=(185/255, 185/255, 255/255), alpha=0.7, label='5%-95%')
    plt.fill_between(years, quantile_results[var_name]["q10"], quantile_results[var_name]["q90"], 
                    color=(136/255, 136/255, 255/255), alpha=0.7, label='10%-90%')
    plt.fill_between(years, quantile_results[var_name]["q20"], quantile_results[var_name]["q80"], 
                    color=(66/255, 66/255, 255/255), alpha=0.7, label='20%-80%')
    plt.fill_between(years, quantile_results[var_name]["q30"], quantile_results[var_name]["q70"], 
                    color=(33/255, 33/255, 255/255), alpha=0.7, label='30%-70%')
    plt.fill_between(years, quantile_results[var_name]["q40"], quantile_results[var_name]["q60"], 
                    color=(20/255, 20/255, 255/255), alpha=0.7, label='40%-60%')
    
    plt.plot(years, quantile_results[var_name]["q50"], 'b--', linewidth=2.5, label='Median')
    
    if baseline_values is not None:
        plt.plot(years, baseline_values[:5], 'r-', linewidth=2.5, label=f'{var_name} baseline')
    
    plt.title(f"Fan Chart - {var_name.upper()} ({pays.upper()})", fontsize=14)
    plt.xlabel("Year", fontsize=12)
    plt.ylabel("Value (% GDP)" if var_name == "dette_iir" else "Value", fontsize=12)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f"fan_chart_{var_name}_{pays}.png", dpi=300, bbox_inches='tight')
    plt.show()

# Génération des graphiques
print("\nGénération des fan charts...")
create_fan_chart("dette_iir", annual_data[f"dette_iir_bkcom_000_{pays}"])
create_fan_chart("soldep_p", annual_data[f"soldep_p_bkcom_000_{pays}"])
create_fan_chart("g_v_yoy", annual_data[f"g_v_yoy_bkcom_000_{pays}"])
create_fan_chart("ltn_10y", annual_data[f"ltn_10y_bkcom_000_{pays}"])
create_fan_chart("tx_moy", annual_data[f"tx_moy_bkcom_000_{pays}"])

print("Analyse terminée. Les graphiques ont été sauvegardés.")