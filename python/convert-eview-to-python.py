import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import multivariate_normal
from matplotlib.ticker import FuncFormatter, FixedLocator
import os
import sys

# Configuration matplotlib for exact EViews match
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = [10, 6]
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.3

# Paramètres
pays = "es"
nsim = 100
w = 20
maturity = 5

try:
    # Chargement des données
    chemin = "C:/Users/junio/Documents/M1 DATA Semester2/Capstone/ultime/convertFile.xlsx"
    print(f"Loading data from: {chemin}")
    
    # Create output directory in current folder
    output_dir = "fan_charts"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    df = pd.read_excel(chemin, sheet_name="Sheet1")
    df["date"] = pd.to_datetime(df["dateid01"])
    df.set_index("date", inplace=True)
    df_country = df[[col for col in df.columns if col.endswith(f"_{pays}")]].copy()

    # Winsorisation exacte comme dans EViews (5-95ème percentiles)
    groups = ["soldep_p", "stn_3m", "ltn_10y", "g_v_yoy"]
    trimmed = {}
    for var in groups:
        col = f"{var}_bkcom_000_{pays}"
        q5, q95 = df_country[col].quantile([0.05, 0.95])
        series = df_country[col].clip(lower=q5, upper=q95)
        # Division par 100 pour les taux uniquement
        trimmed[f"{var}_trimmed"] = series / 100 if var in ["stn_3m", "ltn_10y"] else series

    # Chocs historiques et matrice de covariance
    shock_df = pd.DataFrame({
        f"shock_hist_{v}": trimmed[f"{v}_trimmed"].diff() 
        for v in groups
    }).dropna()
    cov = shock_df.cov()

    # Simulation Monte Carlo avec traitement spécial des taux longs
    ann_results = {v: np.zeros((nsim, 5)) for v in groups}
    ann_ltn_10y = np.zeros((nsim, 5))
    np.random.seed(123456)

    for j in range(nsim):
        # Génération des chocs
        epsn = multivariate_normal.rvs(mean=np.zeros(4), cov=cov, size=w)
        eps_df = pd.DataFrame(epsn, columns=[f"eps_{v}" for v in groups])
        
        # Traitement des chocs pour chaque variable
        for i, var in enumerate(groups):
            acc = eps_df[f"eps_{var}"].cumsum().values
            for y in range(5):
                if var == "ltn_10y":
                    # Traitement spécial EC pour les taux longs (cumul sur 5 ans)
                    ann_ltn_10y[j, y] = acc[4*(y+1)-1] * (y+1) / maturity
                else:
                    if y == 0:
                        ann_results[var][j, y] = acc[3]
                    else:
                        ann_results[var][j, y] = acc[4*(y+1)-1] - acc[4*y-1]

    # Préparation des données annuelles
    annual_data = {}
    resample = lambda k, div=1: df_country[k].resample("YE").last().dropna().values / div

    # Données de 2021 à 2027 (7 points)
    for var in ["soldep_p", "stn_3m", "ltn_10y", "g_v_yoy", "iir", "mal_p"]:
        key = f"{var}_bkcom_000_{pays}"
        div = 100 if var in ["stn_3m", "ltn_10y", "iir"] else 1
        annual_data[key] = resample(key, div)[-7:]

    annual_data[f"dda_bkcom_000_{pays}"] = resample(f"dda_bkcom_000_{pays}")[-7:]
    annual_data[f"alphalt_{pays}"] = np.array([0.75])
    annual_data[f"alphact_{pays}"] = np.array([0.25])

    # Simulation des trajectoires avec traitement correct des taux
    sim_results = {
        var: np.zeros((nsim, 5)) 
        for var in groups + ["tx_moy", "dette_iir"]
    }

    # Dette initiale (2022)
    dettem1 = annual_data[f"mal_p_bkcom_000_{pays}"][1]

    for j in range(nsim):
        for k in range(5):
            # Variables de base
            sim_results["soldep_p"][j, k] = annual_data[f"soldep_p_bkcom_000_{pays}"][k+2] + ann_results["soldep_p"][j, k]
            sim_results["stn_3m"][j, k] = annual_data[f"stn_3m_bkcom_000_{pays}"][k+2] + ann_results["stn_3m"][j, k]
            sim_results["ltn_10y"][j, k] = annual_data[f"ltn_10y_bkcom_000_{pays}"][k+2] + ann_ltn_10y[j, k]
            sim_results["g_v_yoy"][j, k] = annual_data[f"g_v_yoy_bkcom_000_{pays}"][k+2] + ann_results["g_v_yoy"][j, k]
            
            # Taux moyen avec contrainte de positivité
            tx_moy = (
                annual_data[f"iir_bkcom_000_{pays}"][k+2] +
                annual_data[f"alphalt_{pays}"][0] * ann_ltn_10y[j, k] +
                annual_data[f"alphact_{pays}"][0] * ann_results["stn_3m"][j, k]
            )
            sim_results["tx_moy"][j, k] = max(tx_moy, 0)
            
            # Calcul de la dette selon la formule EC
            if k == 0:
                sim_results["dette_iir"][j, k] = (
                    dettem1 * (1 + sim_results["tx_moy"][j, k]) / 
                    (1 + sim_results["g_v_yoy"][j, k]) - 
                    sim_results["soldep_p"][j, k]
                )
            else:
                sim_results["dette_iir"][j, k] = (
                    sim_results["dette_iir"][j, k-1] * 
                    (1 + sim_results["tx_moy"][j, k]) / 
                    (1 + sim_results["g_v_yoy"][j, k]) - 
                    sim_results["soldep_p"][j, k] +
                    annual_data[f"dda_bkcom_000_{pays}"][k+2] / 100
                )

    # Calcul des quantiles pour les fan charts
    quantiles = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
    quantile_results = {
        var: {f"q{int(q*100)}": np.percentile(sim_results[var], q=q*100, axis=0) 
              for q in quantiles}
        for var in sim_results.keys()
    }

    def create_fan_chart(var, baseline=None):
        """Create fan chart matching exactly the EViews format"""
        fig, ax = plt.subplots()
        
        # Years configuration
        proj_years = np.arange(2023, 2028)
        
        # EViews exact confidence bands with corrected opacity
        bands = [
            (95, 5, '#b9b9ff', 0.9),   # Lightest blue
            (90, 10, '#8888ff', 0.8),
            (80, 20, '#6666ff', 0.7),
            (70, 30, '#4444ff', 0.6),
            (60, 40, '#2222ff', 0.5)    # Darkest blue
        ]
        
        # Plot bands in reverse order (darker to lighter)
        for high, low, color, alpha in reversed(bands):
            upper = quantile_results[var][f"q{high}"]
            lower = quantile_results[var][f"q{low}"]
            plt.fill_between(proj_years, lower, upper, color=color, alpha=alpha, linewidth=0)
        
        # Historical and baseline with exact EViews styling
        if baseline is not None:
            hist_value = baseline[2]
            plt.plot([2023], [hist_value], 'ko', markersize=4, zorder=5)
            plt.plot([2023, 2024], [baseline[2], baseline[3]], 'r-', linewidth=1, zorder=4)
            plt.plot(proj_years[1:], baseline[3:], 'r--', linewidth=1, label=f'{var} bkcom', zorder=4)
        
        # Median line with exact EViews styling
        plt.plot(proj_years, quantile_results[var]["q50"], 'k-', linewidth=1.5, label='Median', zorder=6)
        
        # Exact EViews scales and formats
        if var == "dette_iir":
            plt.ylim(0.8, 1.3)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.2f}'))
        elif var in ["stn_3m", "ltn_10y", "tx_moy"]:
            plt.ylim(-0.01, 0.055)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.3f}'))
        elif var == "g_v_yoy":
            plt.ylim(-0.04, 0.12)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.2f}'))
        elif var == "soldep_p":
            plt.ylim(-0.06, 0.06)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.2f}'))
        
        # Exact EViews axis configuration
        ax.set_xlim(2023, 2027)
        ax.xaxis.set_major_locator(FixedLocator(proj_years))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: str(int(x))))

        # Remove top and right spines (EViews style)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Legend with exact EViews positioning
        if var == "dette_iir":
            ax.legend(loc='upper right', framealpha=0.9, ncol=1)
        else:
            ax.legend(loc='lower left', framealpha=0.9, ncol=1)
        
        # Save with exact EViews naming and format
        output_path = os.path.join(output_dir, f'FAN_BOOT_{var.upper()}_{pays.upper()}.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Saved: {output_path}")
        plt.close()

    # Generate all fan charts
    print("\nGenerating fan charts...")

    variables_to_plot = {
        "dette_iir": "mal_p_bkcom_000",
        "soldep_p": "soldep_p_bkcom_000",
        "stn_3m": "stn_3m_bkcom_000",
        "ltn_10y": "ltn_10y_bkcom_000",
        "g_v_yoy": "g_v_yoy_bkcom_000",
        "tx_moy": "iir_bkcom_000"
    }

    for var, base_var in variables_to_plot.items():
        print(f"Processing {var}...")
        baseline = annual_data[f"{base_var}_{pays}"]
        create_fan_chart(var, baseline)
        print(f"Generated fan chart for {var}")

    print("\nAll fan charts generated successfully")

    # Calculate and print statistics
    dette_2023 = annual_data[f"mal_p_bkcom_000_{pays}"][2]
    cone_width = np.percentile(sim_results["dette_iir"][:, -1], 90) - np.percentile(sim_results["dette_iir"][:, -1], 10)
    prob_increase = np.mean(sim_results["dette_iir"][:, -1] > dette_2023) * 100

    print("\nStatistics:")
    print(f"Cone Width (q90-q10): {cone_width:.1f}")
    print(f"P(debt ratio increases): {prob_increase:.1f}%")

except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)