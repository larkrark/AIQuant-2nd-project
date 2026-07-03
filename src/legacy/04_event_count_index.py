from pathlib import Path
import pandas as pd
import numpy as np


PROJECT_DIR = Path(__file__).resolve().parents[2]
PRICE_PATH = PROJECT_DIR / "data" / "processed" / "korea_etf_price_clean.csv"
EVENT_CALENDAR_PATH = PROJECT_DIR / "data" / "reference" / "event_calendar_us_kr.csv"

OUTPUT_TABLE_DIR = PROJECT_DIR / "output" / "tables"
OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)


LOOKBACK_DAYS = 60
SMALL_Q = 0.60
LARGE_Q = 0.90


def load_price_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"가격 전처리 파일이 없습니다: {path}")

    price = pd.read_csv(path, encoding="utf-8-sig", index_col=0)
    price.index = pd.to_datetime(price.index, errors="coerce")
    price = price.dropna(axis=0, how="all")
    price = price.sort_index()
    price = price.apply(pd.to_numeric, errors="coerce")

    return price


def classify_events(returns: pd.DataFrame) -> pd.DataFrame:
    """
    일별 수익률을 작은 등락, 의미 있는 등락, 큰 사건으로 분류한다.

    기준:
    - 과거 60거래일 절대수익률의 60분위 이하: small
    - 60분위 초과 ~ 90분위 이하: medium
    - 90분위 초과: large

    주의:
    rolling 기준은 shift(1)을 사용하여 오늘 수익률을 판단할 때
    오늘 값을 기준 계산에 포함하지 않는다.
    """
    abs_ret = returns.abs()

    q60 = abs_ret.rolling(LOOKBACK_DAYS, min_periods=LOOKBACK_DAYS).quantile(SMALL_Q).shift(1)
    q90 = abs_ret.rolling(LOOKBACK_DAYS, min_periods=LOOKBACK_DAYS).quantile(LARGE_Q).shift(1)

    rows = []

    for date in returns.index:
        for ticker in returns.columns:
            r = returns.at[date, ticker]

            if pd.isna(r):
                continue

            threshold_small = q60.at[date, ticker]
            threshold_large = q90.at[date, ticker]

            if pd.isna(threshold_small) or pd.isna(threshold_large):
                continue

            abs_value = abs(r)

            if abs_value <= threshold_small:
                size_label = "small"
            elif abs_value <= threshold_large:
                size_label = "medium"
            else:
                size_label = "large"

            if r > 0:
                direction = "up"
            elif r < 0:
                direction = "down"
            else:
                direction = "flat"

            event_label = f"{size_label}_{direction}"

            rows.append({
                "Date": date,
                "Ticker": ticker,
                "Return": r,
                "AbsReturn": abs_value,
                "Q60": threshold_small,
                "Q90": threshold_large,
                "SizeLabel": size_label,
                "Direction": direction,
                "EventLabel": event_label
            })

    return pd.DataFrame(rows)


def make_monthly_counts(daily_events: pd.DataFrame) -> pd.DataFrame:
    if daily_events.empty:
        return pd.DataFrame()

    df = daily_events.copy()
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    count_table = (
        df
        .groupby(["Month", "Ticker", "EventLabel"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    expected_cols = [
        "small_up", "small_down",
        "medium_up", "medium_down",
        "large_up", "large_down",
        "small_flat", "medium_flat", "large_flat"
    ]

    for col in expected_cols:
        if col not in count_table.columns:
            count_table[col] = 0

    count_table["risk_event_count"] = (
        count_table["medium_down"] +
        2 * count_table["large_down"]
    )

    count_table["overheat_event_count"] = (
        count_table["medium_up"] +
        2 * count_table["large_up"]
    )

    count_table["event_balance"] = (
        count_table["overheat_event_count"] -
        count_table["risk_event_count"]
    )

    return count_table.sort_values(["Month", "Ticker"])


def summarize_by_ticker(daily_events: pd.DataFrame) -> pd.DataFrame:
    if daily_events.empty:
        return pd.DataFrame()

    summary = (
        daily_events
        .groupby("Ticker")
        .agg(
            FirstDate=("Date", "min"),
            LastDate=("Date", "max"),
            ObsCount=("Return", "count"),
            MeanReturn=("Return", "mean"),
            StdReturn=("Return", "std"),
            LargeUpCount=("EventLabel", lambda x: (x == "large_up").sum()),
            LargeDownCount=("EventLabel", lambda x: (x == "large_down").sum()),
            MediumUpCount=("EventLabel", lambda x: (x == "medium_up").sum()),
            MediumDownCount=("EventLabel", lambda x: (x == "medium_down").sum()),
        )
        .reset_index()
    )

    summary["LargeEventBalance"] = summary["LargeUpCount"] - summary["LargeDownCount"]
    summary["TotalLargeEvents"] = summary["LargeUpCount"] + summary["LargeDownCount"]

    return summary


def load_event_calendar(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    cal = pd.read_csv(path, encoding="utf-8-sig")
    cal["StartDate"] = pd.to_datetime(cal["StartDate"], errors="coerce")
    cal["EndDate"] = pd.to_datetime(cal["EndDate"], errors="coerce")
    return cal


def summarize_event_calendar_overlap(
    daily_events: pd.DataFrame,
    event_calendar: pd.DataFrame
) -> pd.DataFrame:
    if daily_events.empty or event_calendar.empty:
        return pd.DataFrame()

    rows = []

    for _, event in event_calendar.iterrows():
        start = event["StartDate"]
        end = event["EndDate"]

        if pd.isna(start) or pd.isna(end):
            continue

        mask = (daily_events["Date"] >= start) & (daily_events["Date"] <= end)
        sub = daily_events.loc[mask].copy()

        if sub.empty:
            rows.append({
                "Market": event.get("Market", ""),
                "EventName": event.get("EventName", ""),
                "StartDate": start.date().isoformat(),
                "EndDate": end.date().isoformat(),
                "EventType": event.get("EventType", ""),
                "ExpectedHSIDirection": event.get("ExpectedHSIDirection", ""),
                "OverlapStatus": "no_overlap",
                "ObsCount": 0,
                "AssetCount": 0,
                "MeanReturn": np.nan,
                "LargeUpCount": 0,
                "LargeDownCount": 0,
                "MediumUpCount": 0,
                "MediumDownCount": 0,
            })
            continue

        rows.append({
            "Market": event.get("Market", ""),
            "EventName": event.get("EventName", ""),
            "StartDate": start.date().isoformat(),
            "EndDate": end.date().isoformat(),
            "EventType": event.get("EventType", ""),
            "ExpectedHSIDirection": event.get("ExpectedHSIDirection", ""),
            "OverlapStatus": "overlap",
            "ObsCount": len(sub),
            "AssetCount": sub["Ticker"].nunique(),
            "MeanReturn": sub["Return"].mean(),
            "LargeUpCount": int((sub["EventLabel"] == "large_up").sum()),
            "LargeDownCount": int((sub["EventLabel"] == "large_down").sum()),
            "MediumUpCount": int((sub["EventLabel"] == "medium_up").sum()),
            "MediumDownCount": int((sub["EventLabel"] == "medium_down").sum()),
        })

    return pd.DataFrame(rows)


def main() -> None:
    price = load_price_data(PRICE_PATH)
    returns = price.pct_change()

    daily_events = classify_events(returns)
    monthly_counts = make_monthly_counts(daily_events)
    ticker_summary = summarize_by_ticker(daily_events)

    event_calendar = load_event_calendar(EVENT_CALENDAR_PATH)
    event_overlap = summarize_event_calendar_overlap(daily_events, event_calendar)

    daily_events.to_csv(OUTPUT_TABLE_DIR / "daily_event_labels.csv", index=False, encoding="utf-8-sig")
    monthly_counts.to_csv(OUTPUT_TABLE_DIR / "monthly_event_counts.csv", index=False, encoding="utf-8-sig")
    ticker_summary.to_csv(OUTPUT_TABLE_DIR / "event_count_summary.csv", index=False, encoding="utf-8-sig")
    event_overlap.to_csv(OUTPUT_TABLE_DIR / "event_calendar_overlap_summary.csv", index=False, encoding="utf-8-sig")

    print("[완료] 하인리히식 사건 카운트 계산")
    print(f"- 가격 데이터: {PRICE_PATH}")
    print(f"- 기준 기간: 과거 {LOOKBACK_DAYS}거래일")
    print(f"- 작은 등락 기준: 과거 절대수익률 {int(SMALL_Q * 100)}분위 이하")
    print(f"- 큰 사건 기준: 과거 절대수익률 {int(LARGE_Q * 100)}분위 초과")
    print()
    print("[생성 파일]")
    print(f"- {OUTPUT_TABLE_DIR / 'daily_event_labels.csv'}")
    print(f"- {OUTPUT_TABLE_DIR / 'monthly_event_counts.csv'}")
    print(f"- {OUTPUT_TABLE_DIR / 'event_count_summary.csv'}")
    print(f"- {OUTPUT_TABLE_DIR / 'event_calendar_overlap_summary.csv'}")

    if not event_overlap.empty:
        print()
        print("[사건 달력 연결 요약]")
        print(event_overlap[["Market", "EventName", "OverlapStatus", "ObsCount", "LargeUpCount", "LargeDownCount"]].to_string(index=False))


if __name__ == "__main__":
    main()
