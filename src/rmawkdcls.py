import pandas as pd

path = "data/processed/main_final_baseline_backtest_timeseries.csv"
df = pd.read_csv(path)

print(df.isna().sum())
print(df.tail(20))

check_cols = [
    "strategy_return",
    "cumulative_return",
    "drawdown",
    "turnover"
]

print(df[check_cols].isna().sum())
print(df[check_cols].describe())

print(df["strategy_return"].min(), df["strategy_return"].max())
print(df["cumulative_return"].min(), df["cumulative_return"].max())
print(df["drawdown"].min(), df["drawdown"].max())

bad = df[
    (df["strategy_return"] < -1) |
    (df["cumulative_return"] <= 0) |
    (df["drawdown"] < -1) |
    (df["drawdown"] > 0)
]

print(bad)