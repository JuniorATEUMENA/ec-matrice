# -*- coding: utf-8 -*-
"""
Created on Thu May 29 15:15:26 2025

@author: junio
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Charger le fichier Excel contenant les données
file_path = "C:/Users/junio/Documents/M1 DATA Semester2/Capstone/ultime/convertFile.xlsx"  # ← Assure-toi que le fichier est dans le bon dossier
df = pd.read_excel(file_path)

# Afficher les premières lignes pour vérifier
print("Aperçu des données chargées :")
print(df.head())

# Extraire uniquement les colonnes pour le pays "es" (Espagne)
country = "es"
cols_es = [col for col in df.columns if col.endswith(f"_{country}")]
df_es = df[cols_es].copy()

# Afficher les colonnes retenues
print("\nColonnes sélectionnées pour le pays :", country)
print(df_es.columns.tolist())

# Conversion des taux en pourcentage (division par 100 si nécessaire)
for col in df_es.columns:
    if any(x in col for x in ["soldep_p", "g_v_yoy", "ltn_10y", "stn_3m", "iir"]):
        df_es[col] = df_es[col] / 100

# Aperçu des données converties
print("\nDonnées après conversion éventuelle des taux :")
print(df_es.head())

# ================================================================
# 🔧 2. Winsorisation des variables (5e et 95e percentiles)
# ================================================================

# Liste des variables concernées (groupes simulés dans le code EViews)
vars_to_winsorize = ['soldep_p', 'stn_3m', 'ltn_10y', 'g_v_yoy']

# Dictionnaire pour stocker les séries winsorisées
winsorized_data = {}

# Appliquer la winsorisation à 5% et 95% pour chaque variable
for var in vars_to_winsorize:
    col_name = f"{var}_bkcom_000_{country}"
    series = df_es[col_name].copy()

    # Calcul des quantiles
    q5 = series.quantile(0.05)
    q95 = series.quantile(0.95)

    # Winsorisation
    series_wins = np.where(series < q5, q5,
                   np.where(series > q95, q95, series))

    # Sauvegarde dans le dictionnaire
    winsorized_data[var] = pd.Series(series_wins, index=series.index)

    # Affichage rapide
    print(f"\n{var} winsorisé : q5 = {q5:.4f}, q95 = {q95:.4f}")
    print(winsorized_data[var].head())

# Conversion en DataFrame
df_trimmed = pd.DataFrame(winsorized_data)

# Affichage des premières lignes du dataframe trimé
print("\n✅ Aperçu du DataFrame winsorisé :")
print(df_trimmed.head())

# ================================================================
# 📉 3. Construction des chocs historiques et covariance
# ================================================================

# Calcul des chocs historiques (Δx = x_t - x_{t-1})
shock_data = df_trimmed.diff().dropna()

# Renommer les colonnes pour indiquer qu'il s'agit de chocs
shock_data.columns = [f"shock_{col}" for col in shock_data.columns]

# Aperçu des chocs historiques
print("\n✅ Chocs historiques (différences premières) :")
print(shock_data.head())

# Calcul de la matrice de variance-covariance empirique (corrigée des degrés de liberté)
cov_matrix = shock_data.cov()

# Affichage de la matrice de covariance
print("\n✅ Matrice de variance-covariance des chocs :")
print(cov_matrix)

# ================================================================
# 🎲 4. Simulation de chocs via tirages Monte Carlo
# ================================================================

# Paramètres de simulation
nsim = 1000        # Nombre de simulations
n_years = 5       # Nombre d'années projetées
n_quarters = n_years * 4  # Total de trimestres

# Extraire la moyenne des chocs (centrée sur 0 pour cette version)
mean_vector = np.zeros(len(cov_matrix))

# Simulation Monte Carlo : (nsim x n_quarters) tirages
# Résultat : tableau de taille (nsim, n_quarters, 4)
shock_simulations = np.random.multivariate_normal(
    mean=mean_vector,
    cov=cov_matrix.values,
    size=(nsim, n_quarters)
)

# Optionnel : noms des variables simulées (dans l’ordre des colonnes)
shock_variables = cov_matrix.columns.tolist()

# Vérification : dimensions et exemple
print(f"\n✅ Dimensions des chocs simulés : {shock_simulations.shape}")
print(f"Variables simulées : {shock_variables}")
print("\nExemple : chocs simulés pour la simulation 0, trimestre 0")
print(dict(zip(shock_variables, shock_simulations[0, 0, :])))

# ================================================================
# 📆 5. Agrégation des chocs trimestriels en chocs annuels
# ================================================================

# Paramètres
T_maturity = 5  # Maturité moyenne de la dette

# Initialisation des matrices
ann_shocks = {var: np.zeros((nsim, n_years)) for var in shock_variables}
ann_ltn_10y = np.zeros((nsim, n_years))  # Traitement spécial

# Boucle sur chaque simulation
for j in range(nsim):
    for i, var in enumerate(shock_variables):
        for year in range(n_years):
            q_start = year * 4
            q_end = (year + 1) * 4
            # Somme des 4 trimestres pour l’année
            annual_sum = np.sum(shock_simulations[j, q_start:q_end, i])
            ann_shocks[var][j, year] = annual_sum

            # Traitement spécial si variable = ltn_10y
            if var == 'shock_ltn_10y':
                # Application progressive du choc sur T années
                ann_ltn_10y[j, year] = annual_sum * ((year + 1) / T_maturity)

# Vérification
print("\n✅ Exemple de chocs annuels pour la 1ère simulation (sim 0) :")
for var in ann_shocks:
    print(f"{var}: {ann_shocks[var][0]}")
print(f"shock_ltn_10y (ajusté) : {ann_ltn_10y[0]}")

# 🔁 6. Génération des trajectoires simulées des variables
# ================================================================

# Hypothèses simplifiées pour les pondérations
alpha_lt = 0.75
alpha_ct = 0.25

# Liste des variables simulées dans le dictionnaire ann_shocks (sans 'shock_' pour éviter KeyError)
simulated_vars = ['soldep_p', 'stn_3m', 'g_v_yoy']

# Calcul des moyennes historiques comme baseline
baseline_means = {}
for var in simulated_vars + ['ltn_10y']:
    col_name = f"{var}_bkcom_000_{country}"
    baseline_means[var] = df_es[col_name].dropna().iloc[-20:].mean()
    print(f"🔹 Moyenne baseline de {var} : {baseline_means[var]:.4f}")

# Initialisation des matrices simulées
sim_results = {var: np.zeros((nsim, n_years)) for var in simulated_vars}
sim_tx_moy = np.zeros((nsim, n_years))

# Boucle de simulation
for j in range(nsim):
    for year in range(n_years):
        # Appliquer les chocs à la baseline
        for var in simulated_vars:
            shock_name = f"shock_{var}"
            sim_results[var][j, year] = baseline_means[var] + ann_shocks[shock_name][j, year]

        # Traitement du taux implicite avec ltn_10y
        ltn_adj = ann_ltn_10y[j, year]
        stn_shock = ann_shocks['shock_stn_3m'][j, year]
        ltn_sim = baseline_means['ltn_10y'] + ltn_adj
        stn_sim = baseline_means['stn_3m'] + stn_shock

        # Taux implicite simulé
        tx = alpha_lt * ltn_sim + alpha_ct * stn_sim
        sim_tx_moy[j, year] = max(tx, 0)  # Positivity constraint

# Vérification
print("\n✅ Exemple de trajectoires simulées (simulation 0) :")
for var in sim_results:
    print(f"{var}: {sim_results[var][0]}")
print(f"tx_moy: {sim_tx_moy[0]}")

# ================================================================
# 🧮 7. Simulation stochastique de la dette publique
# ================================================================

# Hypothèse : dette initiale à la fin de la période observée
b0 = 1.10  # dette initiale en pourcentage du PIB (ex: 110%)

# Ajustement stock-flux (dda) : ici on suppose zéro, sinon le charger depuis Excel
dda = np.zeros((nsim, n_years))

# Initialisation du tableau des trajectoires simulées de dette
sim_dette = np.zeros((nsim, n_years))

# Boucle de simulation
for j in range(nsim):
    for year in range(n_years):
        if year == 0:
            # Première année de projection
            sim_dette[j, year] = b0 * (1 + sim_tx_moy[j, year]) / (1 + sim_results['g_v_yoy'][j, year]) - sim_results['soldep_p'][j, year]
        else:
            # Années suivantes
            sim_dette[j, year] = (
                sim_dette[j, year-1]
                * (1 + sim_tx_moy[j, year]) / (1 + sim_results['g_v_yoy'][j, year])
                - sim_results['soldep_p'][j, year]
                + dda[j, year]
            )

# ✅ Vérification
print("\n✅ Exemple de trajectoire de dette (simulation 0) :")
print(sim_dette[0])

# ================================================================
# 📊 Fan charts pour les 6 variables simulées (comme dans EViews)
# ================================================================

# Reconstituer les 6 variables finales simulées
sim_all = {
    'dette_iir': sim_dette,
    'soldep_p': sim_results['soldep_p'],
    'stn_3m': sim_results['stn_3m'],
    'g_v_yoy': sim_results['g_v_yoy'],
    'tx_moy': sim_tx_moy,
    'ltn_10y': np.tile(baseline_means['ltn_10y'], (nsim, n_years)) + ann_ltn_10y
}

# Paramètres d’affichage
quantile_levels = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95]
fill_pairs = [(5, 95), (10, 90), (20, 80), (30, 70), (40, 60)]
blue_shades = ["#1414ff", "#2121ff", "#4444ff", "#8888ff", "#b9b9ff"]

for varname, sim_matrix in sim_all.items():
    # Calcul des quantiles
    q_dict = {f"q{q}": np.percentile(sim_matrix, q, axis=0) for q in quantile_levels}
    q_df = pd.DataFrame(q_dict)

    # Tracé du fan chart
    plt.figure(figsize=(10, 6))

    for (low, high), color in zip(fill_pairs, blue_shades):
        plt.fill_between(
            range(n_years),
            q_df[f"q{low}"],
            q_df[f"q{high}"],
            color=color,
            label=f"{100 - (high - low)}% intervalle"
        )

    # Courbe médiane
    plt.plot(q_df["q50"], color="black", linewidth=2, label="Médiane")

    # Baseline (si connue)
    if varname in baseline_means:
        plt.plot(
            range(n_years),
            [baseline_means[varname]] * n_years,
            color="green", linestyle="--", linewidth=2, label="Baseline"
        )

    # Titres
    plt.title(f"Fan Chart – {varname} simulé")
    plt.xlabel("Année de projection")
    plt.ylabel(varname)
    plt.xticks(range(n_years), [f"{2024 + i}" for i in range(n_years)])
    plt.grid(True)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
    plt.tight_layout()
    plt.show()


