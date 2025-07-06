# -*- coding: utf-8 -*-
import math
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle

mplstyle.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"figure.figsize": (10, 6), "figure.dpi": 150})

def load_and_process():
    df = pd.DataFrame({
        "year": [2020, 2021, 2022, 2023],
        "nominal_rate": [1.5, 2.0, 3.0, 4.0],
        "inflation_rate": [1.0, 5.0, 6.0, 4.0],
    }).assign(real_rate=lambda d: d.nominal_rate - d.inflation_rate)
    return df

def plot_rates(df):
    df.plot(x="year", y=["nominal_rate", "inflation_rate", "real_rate"], marker="o")
    plt.title("Nominal vs Real Interest & Inflation")
    plt.xlabel("Year")
    plt.ylabel("Rate (%)")
    plt.legend(["Nominal", "Inflation", "Real"])
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def geometric_mean(returns):
    r = pd.to_numeric(returns, errors="coerce").dropna() / 100
    prod = np.prod(1 + r)
    return prod**(1 / len(r)) - 1 if len(r) else 0.0

def harmonic_mean(x):
    arr = pd.to_numeric(x, errors="coerce").dropna()
    return len(arr) / np.sum(1 / arr) if len(arr) else 0.0

def compute_cash_metrics(df):
    geo_nom = geometric_mean(df.nominal_rate)
    geo_real = geometric_mean(df.real_rate)
    harm_nom = harmonic_mean(df.nominal_rate)
    harm_real = harmonic_mean(df.real_rate)
    return geo_nom, geo_real, harm_nom, harm_real

def compute_irr(cash_flows):
    try:                                        
        return npf.irr(cash_flows)
    except ValueError:
        return None

def continuous_compounding(pv, r, t):
    fv = pv * math.exp(r * t)
    return fv, math.log(fv / pv) / t

def main():
    df = load_and_process()
    print(df)
    plot_rates(df)

    geo_nom, geo_real, harm_nom, harm_real = compute_cash_metrics(df)
    print(f"Geometric nominal return: {geo_nom:.4%}")
    print(f"Geometric real return:    {geo_real:.4%}")
    print(f"Harmonic nominal mean:    {harm_nom:.4f}")
    print(f"Harmonic real mean:       {harm_real:.4f}")

    cf = [-1000, 300, 400, 500]
    irr = compute_irr(cf)
    print(f"IRR: {irr:.4%}" if irr is not None else "IRR could not be calculated")

    fv, annual_cont = continuous_compounding(1000, 0.05, 3)
    print(f"FV (continuous): ${fv:.2f}")
    print(f"Annual continuously compounded return: {annual_cont:.4%}")

if __name__ == "__main__":
    main()



