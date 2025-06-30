import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

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
    """
    Plot investment dividend growth and cumulative investment value.
    If n>0 and g_S given: two-stage growth (g_S for n years, then g).
    If n=0: constant growth at rate g.
    """
    max_years = 20  # max years to plot for illustration
    years = np.arange(1, max_years + 1)
    dividends = []
    investment_value = []

    for t in years:
        if n > 0 and g_S is not None:
            # Two-stage growth: g_S for first n years, then g
            if t <= n:
                div_growth = g_S
                year_idx = t - 1
                dividend = D0 * (1 + div_growth) ** year_idx
            else:
                # growth at g after stage n
                # dividend at year n * (1 + g)^(t - n)
                dividend_n = D0 * (1 + g_S) ** n
                dividend = dividend_n * (1 + g) ** (t - n - 1)
        else:
            # Constant growth
            dividend = D0 * (1 + g) ** (t - 1)

        dividends.append(dividend)
        cumulative = investment_value[-1] + dividend if investment_value else dividend
        investment_value.append(cumulative)

    # Plotting
    plt.figure(figsize=(12, 7))

    plt.bar(years, dividends, alpha=0.6, label='Dividends')
    plt.plot(years, investment_value, marker='o', color='darkblue', label='Cumulative Investment Value')

    plt.title("Investment Dividend Growth and Cumulative Value")
    plt.xlabel("Year")
    plt.ylabel("Amount ($)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# Parameters
D0 = 1000    # initial dividend
r = 0.05     # interest rate (not directly used here but could be)
g = 0.04     # long-term dividend growth rate
n = 5        # years of short-term growth
g_S = 0.10   # short-term dividend growth rate

# Plot constant growth
print("Constant Growth Model:")
plot_investment_growth(D0, r, g, n=0)

# Plot two-stage changing growth
print("Two-Stage Changing Growth Model:")
plot_investment_growth(D0, r, g, n, g_S)



def implied_returns_visualizations():
    # Yield Curve example (years vs yield %)
    maturities = np.array([1, 2, 3, 5, 7, 10, 20, 30])
    yields = np.array([0.5, 0.75, 1.0, 1.5, 1.75, 2.0, 2.5, 3.0])
    
    plt.figure(figsize=(10, 5))
    sns.lineplot(x=maturities, y=yields, marker='o')
    plt.title("Yield Curve")
    plt.xlabel("Maturity (Years)")
    plt.ylabel("Yield (%)")
    plt.grid(True)
    plt.show()
    
    # Bond price calculation function for coupon bond
    def bond_price(face=1000, coupon_rate=0.05, years=5, yield_rate=0.05):
        coupons = np.full(years, coupon_rate * face)
        price = sum([c / ((1 + yield_rate) ** t) for t, c in enumerate(coupons, 1)])
        price += face / ((1 + yield_rate) ** years)
        return price

    # Bond Price vs Yield for 5-year bond with 5% coupon
    yields_range = np.linspace(0.001, 0.15, 100)
    prices = [bond_price(yield_rate=y) for y in yields_range]
    
    plt.figure(figsize=(10, 5))
    plt.plot(yields_range * 100, prices)
    plt.title("Bond Price vs Yield (5-year, 5% coupon)")
    plt.xlabel("Yield (%)")
    plt.ylabel("Price ($)")
    plt.grid(True)
    plt.show()

    # Return components over 10 years for coupon bond
    years = 10
    face = 1000
    coupon_rate = 0.04
    yield_rate = 0.05
    
    coupons = np.full(years, coupon_rate * face)
    price_start = bond_price(face, coupon_rate, years, yield_rate)
    
    prices = [bond_price(face, coupon_rate, years - t, yield_rate) if years - t > 0 else face for t in range(years + 1)]
    
    coupon_returns = []
    price_returns = []
    total_returns = []
    
    for t in range(years):
        coupon_returns.append(coupons[t])
        price_change = prices[t+1] - prices[t]
        price_returns.append(price_change)
        total_returns.append(coupons[t] + price_change)
    
    plt.figure(figsize=(12, 6))
    plt.bar(range(years), coupon_returns, label='Coupon Payment', alpha=0.7)
    plt.bar(range(years), price_returns, bottom=coupon_returns, label='Price Change', alpha=0.7)
    plt.plot(range(years), total_returns, color='black', marker='o', label='Total Return')
    plt.title("Coupon Bond Return Components Over Time")
    plt.xlabel("Year")
    plt.ylabel("Return ($)")
    plt.legend()
    plt.grid(True)
    plt.show()

# Run the function
implied_returns_visualizations()



