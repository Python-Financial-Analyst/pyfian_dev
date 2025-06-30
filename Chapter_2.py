import numpy as np
import matplotlib.pyplot as plt

def plot_future_value(D0, r, periods):
    years = np.arange(1, periods + 1)
    future_values = np.zeros(periods)
    total_value = 0

    for t in range(periods):
        future_value = D0 * (1 + r) ** (periods - t - 1)
        future_values[t] = future_value
        total_value += future_value

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.bar(years, future_values, color='lightcoral', label='Future Value of Each $100')
    plt.axhline(y=total_value, color='darkblue', linestyle='--', label=f'Total Future Value: ${total_value:,.2f}')
    plt.title("Future Value of $100 Invested Each Year Over Time")
    plt.xlabel("Year")
    plt.ylabel("Future Value ($)")
    plt.xticks(years)
    plt.legend()
    plt.tight_layout()
    plt.show()

# Parameters
D0 = 100  # Annual investment
r = 0.05  # Annual interest rate (5%)
periods = 5  # Number of periods (years)

# Plot future value of $100 invested each year
plot_future_value(D0, r, periods)



def plot_investment_growth(D0, r, g, n=0, g_S=None):
    years = np.arange(1, n + 1) if n > 0 else np.array([1])
    dividends = []
    investment_value = []

    if n == 0:  # Constant Growth Model
        for t in years:
            dividend = D0 * (1 + g) ** t
            dividends.append(dividend)
            investment_value.append(investment_value[-1] + dividend if investment_value else dividend)
    else:  # Changing Growth Model (Two-Stage)
        for t in years:
            dividend = D0 * (1 + g_S) ** t
            dividends.append(dividend)
            investment_value.append(investment_value[-1] + dividend if investment_value else dividend)

    # Plotting
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Plot initial investment as a negative bar
    ax1.bar(0, -D0, width=0.4, label='Initial Investment', color='lightcoral', align='center')

    # Plot dividends
    ax1.bar(years, dividends, width=0.4, label='Dividends', color='lightgreen', align='center')

    # Create a second y-axis to plot investment value
    ax2 = ax1.twinx()
    ax2.plot(years, investment_value, label='Investment Value', color='darkblue', marker='o')
    ax2.set_ylabel("Investment Value ($)", color='darkblue')
    ax2.tick_params(axis='y', labelcolor='darkblue')

    # Title and layout
    plt.xlabel("Year")
    plt.ylabel("Dividends ($)", color='lightgreen')
    ax1.tick_params(axis='y', labelcolor='lightgreen')
    plt.title("Investment Growth and Dividends Over Time")
    fig.tight_layout()
    plt.legend()
    plt.show()

# Parameters
D0 = 1000  # Initial investment
r = 0.05  # Annual interest rate (5%)
g = 0.04  # Dividend growth rate
n = 5  # Number of years
g_S = 0.10  # Short-term dividend growth rate

# Plot investment growth and dividends for Constant Growth Model
plot_investment_growth(D0, r, g)

# Plot investment growth and dividends for Changing Dividend Growth Model
plot_investment_growth(D0, r, g, n, g_S)
