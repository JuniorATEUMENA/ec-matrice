
# RÉUNION AVANCEMENT DU PROJET SDSA

**Participants :**  
- BARET KÉA (DCPM/FIPU)  
- FRÉDÉRIQUE BEC (CONSULTANTE BDF, CY CERGY PARIS UNIVERSITY)  
**Date :** 6/02/2025

---

## ORGANIZATION

1. The European Commission SDSA approach  
2. The EU's new Economic Governance Framework  
3. Implementation  
4. Projects for BdF SDSA  

---

## 1. THE EUROPEAN COMMISSION SDSA APPROACH

### 1.1 The Debt Drivers Considered in the SDSA

\[
b_t = \frac{1 + i_t}{1 + g_t} b_{t-1} - pb_t + \Delta CoA_t + ddat
\]

**Simulated variables :**
- \( b_t \): debt to GDP ratio
- \( i_t \): implicit nominal interest rate
- \( g_t \): nominal GDP y-o-y growth rate
- \( pb_t \): primary balance to GDP ratio

**Variables not considered :**
- \( \Delta CoA_t \): ageing costs
- \( ddat \): deficit-debt (stock-flow) adjustment

Stochastic shocks simulated for:
- primary balance-to-GDP ratio \( pb_t \)
- nominal short- and long-term interest rates \( i_t \)
- nominal GDP growth rate \( g_t \)

### 1.2 The Key Principles of the EC Approach

**The data:**
- Quarterly data from Eurostat, OECD, ECB
- Sample from 2000Q1
- Primary balance = headline balance (B9) + interest payments (D41PAY)
- Seasonally adjusted using Census X-12-ARIMA
- Outliers treated with winsorising (5th–95th percentiles)

**Driver shocks:**
- First difference: \( \delta^q x = x_q - x_{q-1} \)
- Covariance matrix:  
\[
\hat{\Sigma} = E[(\delta_q - \bar{\delta_q})(\delta_q - \bar{\delta_q})']
\]
- Monte-Carlo simulations:  
\[
\epsilon_q^s \sim N(0, \hat{\Sigma})
\] for \( s = 1,… , 10000 \)

**Annual aggregation and long-term interest shock persistence:**
- Aggregation: \( \epsilon_t^x = \sum_{q=1}^{4} \epsilon_{q}^{x_s} \)
- Long-term rates: aggregated with rolling-over debt adjustment
- Implicit interest: \( \epsilon_t^i = \alpha_{ST} \epsilon_i^{ST} + \alpha_{LT} \epsilon_i^{LT} \)

**Final simulations:**
- \( x_t = \bar{x}_t + \epsilon_t^x \)
- Repeated 10,000 times
- Fan charts based on debt trajectory distribution

---

## 2. THE EU'S NEW ECONOMIC GOVERNANCE FRAMEWORK

- Adopted in April 2024
- By end of adjustment period (4 or 7 years), targets:
  - Debt ratio on downward path or <60%
  - Deficit <3%
  - Debt ratio declines with at least 70% probability (SDSA)

---

## 3. IMPLEMENTATION

**Risk classification criteria:**
- Cone width (q90–q10) at 5th projection year
- P(debt ratio 5th year > current debt ratio)
- NEW: P(debt ratio decreases over 5 years post-adjustment)

**Example – France 2000Q1–2023Q4 (winsorised, 7-year adjustment 2025–2031):**
- Cone width: 18.8 pps
- P(debt ratio 2028 > 2023): 89.4%

**Shock impact table:**

| Scenario | q90-q10 | % change | Prob | % change |
|----------|---------|----------|------|----------|
| All shocks | 18.8 | - | 89.9 | - |
| No iir | 19.0 | +1.1% | 89.7 | -0.2% |
| No i_LT | 18.9 | +0.5% | 89.7 | -0.2% |
| No i_ST | 18.8 | 0 | 89.9 | 0.0% |
| No pb | 14.2 | -24.5% | 96.1 | +6.9% |
| No g | 8.2 | -56.4% | 99.7 | +10.9% |

**New criterium options:**
- Option 1: simulate 10,000 sequences over 52 quarters (13 years)
  - P(2036 debt ratio < 2031) = 82.5%
- Option 2: transpose fanchart to deterministic path
  - P(2036 debt ratio < 2031) = 92%

---

## 4. PROJECTS FOR BDF SDSA

- Implementation of SDSA version COM:
  - Data collection and Monte-Carlo simulations
  - Long-term interest shock processing
- Extension to DE, ES, IT, NL:
  - Data collection (ongoing)
  - (B-)VAR and EC Monte-Carlo simulations
