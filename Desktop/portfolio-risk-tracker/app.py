
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# Fix path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.portfolio_analysis import (
    download_data,
    calculate_returns,
    monte_carlo_simulation,
    monte_carlo_simulation_individual,
    optimize_portfolio,
)
from src.metrics import sharpe_ratio, calculate_beta, calculate_var

st.set_page_config(page_title="Portfolio Risk Tracker", layout="wide")
st.title("📈 Portfolio Risk Tracker")

# User Inputs
tickers = st.text_input("Enter comma-separated tickers (e.g., AAPL, MSFT, GOOG):", "AAPL,MSFT,GOOG")
tickers = [t.strip().upper() for t in tickers.split(',') if t.strip() != '']

start_date = st.date_input("Start Date", pd.to_datetime("2020-01-01"))
end_date = st.date_input("End Date", pd.to_datetime("2024-12-31"))

n_simulations = st.slider("Number of Simulations", 100, 1000, 300, 100)
n_days = st.slider("Number of Days to Simulate", 30, 365, 252, 10)

# Analyze Portfolio
if st.button("Analyze Portfolio"):
    try:
        prices = download_data(tickers, start_date, end_date)
        returns = calculate_returns(prices)

        st.subheader("📈 Price Chart")
        st.line_chart(prices)

        st.subheader("📊 Return Chart")
        st.line_chart(returns)

        # Equal weights for base metrics
        weights = np.array([1 / len(tickers)] * len(tickers))
        avg_ret = returns.mean()
        port_return = np.dot(weights, avg_ret) * 252
        port_volatility = returns.cov().mul(252).dot(weights).dot(weights.T)**0.5
        port_sharpe = sharpe_ratio(returns.mean())
        port_beta = calculate_beta(returns[tickers[0]], returns.mean(axis=1))
        port_var = calculate_var(returns.mean())

        st.subheader("📌 Portfolio Metrics")
        st.write(f"🔹 Annualized Return: `{port_return:.2%}`")
        st.write(f"🔹 Annualized Volatility: `{port_volatility:.2%}`")
        st.write(f"🔹 Sharpe Ratio: `{port_sharpe:.2f}`")
        st.write(f"🔹 Beta: `{port_beta:.2f}`")
        st.write(f"🔹 Value at Risk (95%): `{port_var:.4f}`")

        # 🔷 Portfolio Optimization
        opt_weights = optimize_portfolio(returns)
        st.subheader("📈 Optimal Portfolio Weights (Sharpe Maximized)")
        for ticker, weight in zip(tickers, opt_weights):
            st.write(f"{ticker}: {weight:.2%}")

        # 🔷 Portfolio-Level Monte Carlo Simulation
        simulations = monte_carlo_simulation(prices, n_simulations=n_simulations, n_days=n_days)
        fig, ax = plt.subplots(figsize=(10, 4))
        for i in range(simulations.shape[0]):
            ax.plot(simulations[i], color='blue', alpha=0.01)
        ax.set_title("Monte Carlo Simulation (Portfolio Price Paths)")
        st.pyplot(fig)

        # 🔷 Individual Stock Simulations
        sim_dict = monte_carlo_simulation_individual(prices, n_simulations=n_simulations, n_days=n_days)
        st.subheader("📉 Individual Stock Monte Carlo Simulations")
        for ticker in tickers:
            fig, ax = plt.subplots(figsize=(8, 3))
            sim = sim_dict[ticker]
            for i in range(sim.shape[0]):
                ax.plot(sim[i], color='purple', alpha=0.02)
            ax.set_title(f"Monte Carlo Simulation: {ticker}")
            st.pyplot(fig)

    except Exception as e:
        st.error(f"❌ Error: {e}")
