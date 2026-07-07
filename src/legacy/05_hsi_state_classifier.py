from pathlib import Path
import pandas as pd
import numpy as np


PROJECT_DIR = Path(__file__).resolve().parents[2]

PRICE_PATH = PROJECT_DIR / "data" / "processed" / "korea_etf_price_clean.csv"
MONTHLY_EVENT_PATH = PROJECT_DIR / "output" / "tables" / "monthly_event_counts.csv"
EVENT_CALENDAR_PATH = PROJECT_DIR / "data" / "reference" / "event_calendar_us_kr.csv"

OUTPUT_TABLE_DIR = PROJECT_DIR / "output" / "tables"
OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)


def load_price_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"가격 파일이 없습니다: {path}")

    price = pd.read_csv(path, encoding="utf-8-sig", index_col=0)
    price.index = pd.to_datetime(price.index, errors="coerce")
    price = price.dropna(axis=0, how="all")
    price = price.sort_index()
    price = price.apply(pd.to_numeric, errors="coerce")

    return price


def load_monthly_events(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"월별 사건 카운트 파일이 없습니다: {path}")

    events = pd.read_csv(path, encoding="utf-8-sig")
    events["Month"] = events["Month"].astype(str)
    events["Ticker"] = events["Ticker"].astype(str).str.zfill(6)

    return events


def calculate_daily_indicators(price: pd.DataFrame) -> pd.DataFrame:
    """
    가격 데이터에서 수익률, 이동평균 이격도, 변동성, 상대강도를 계산한다.
    """
    returns = price.pct_change()

    ma20 = price.rolling(20, min_periods=20).mean()
    ma60 = price.rolling(60, min_periods=60).mean()

    ma20_gap = price / ma20 - 1
    ma60_gap = price / ma60 - 1

    vol20 = returns.rolling(20, min_periods=20).std() * np.sqrt(252)
    vol60 = returns.rolling(60, min_periods=60).std() * np.sqrt(252)

    ret21 = price.pct_change(21)
    ret63 = price.pct_change(63)

    universe_ret63 = ret63.mean(axis=1)
    rel_strength_63 = ret63.sub(universe_ret63, axis=0)

    # 과열 판단용: 과거 252일 기준 이동평균 이격도 상위 90% 기준
    ma20_gap_q90 = ma20_gap.rolling(252, min_periods=120).quantile(0.90).shift(1)

    frames = []

    for ticker in price.columns:
        temp = pd.DataFrame({
            "Date": price.index,
            "Ticker": ticker,
            "price": price[ticker].values,
            "daily_return": returns[ticker].values,
            "ret21": ret21[ticker].values,
            "ret63": ret63[ticker].values,
            "ma20_gap": ma20_gap[ticker].values,
            "ma60_gap": ma60_gap[ticker].values,
            "vol20": vol20[ticker].values,
            "vol60": vol60[ticker].values,
            "rel_strength_63": rel_strength_63[ticker].values,
            "ma20_gap_q90": ma20_gap_q90[ticker].values,
        })
        frames.append(temp)

    daily = pd.concat(frames, ignore_index=True)
    daily["Month"] = daily["Date"].dt.to_period("M").astype(str)

    return daily


def make_month_end_indicators(daily: pd.DataFrame) -> pd.DataFrame:
    """
    일별 지표를 월말 기준으로 정리한다.
    각 월·각 ETF에서 마지막으로 관측 가능한 값을 사용한다.
    """
    daily_sorted = daily.sort_values(["Ticker", "Date"]).copy()

    month_end = (
        daily_sorted
        .dropna(subset=["price"])
        .groupby(["Month", "Ticker"], as_index=False)
        .tail(1)
        .copy()
    )

    month_end = month_end[[
        "Month", "Ticker", "Date", "price",
        "ret21", "ret63",
        "ma20_gap", "ma60_gap",
        "vol20", "vol60",
        "rel_strength_63",
        "ma20_gap_q90"
    ]].copy()

    month_end = month_end.rename(columns={"Date": "MonthEndDate"})

    return month_end


def merge_indicators_and_events(month_end: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(
        month_end,
        events,
        on=["Month", "Ticker"],
        how="left"
    )

    event_cols = [
        "large_down", "large_up",
        "medium_down", "medium_up",
        "small_down", "small_up", "small_flat",
        "risk_event_count", "overheat_event_count", "event_balance"
    ]

    for col in event_cols:
        if col not in merged.columns:
            merged[col] = 0
        merged[col] = merged[col].fillna(0)

    return merged


def classify_row(row: pd.Series) -> pd.Series:
    """
    월별 지표와 사건 카운트를 바탕으로 상태명을 붙인다.

    주의:
    이 기준은 1차 실험 기준이다.
    상태명은 확정된 금융 이론이 아니라, HSI 해석을 일관되게 만들기 위한 규칙이다.
    """
    ret63 = row.get("ret63", np.nan)
    ma20_gap = row.get("ma20_gap", np.nan)
    ma60_gap = row.get("ma60_gap", np.nan)
    vol20 = row.get("vol20", np.nan)
    vol60 = row.get("vol60", np.nan)
    rel_strength = row.get("rel_strength_63", np.nan)
    ma20_gap_q90 = row.get("ma20_gap_q90", np.nan)

    large_down = row.get("large_down", 0)
    large_up = row.get("large_up", 0)
    medium_down = row.get("medium_down", 0)
    medium_up = row.get("medium_up", 0)
    risk_event_count = row.get("risk_event_count", 0)
    overheat_event_count = row.get("overheat_event_count", 0)

    vol_rising = pd.notna(vol20) and pd.notna(vol60) and vol20 > vol60
    trend_negative = pd.notna(ma20_gap) and pd.notna(ma60_gap) and ma20_gap < 0 and ma60_gap < 0
    trend_positive = pd.notna(ma20_gap) and pd.notna(ma60_gap) and ma20_gap > 0 and ma60_gap > 0
    momentum_negative = pd.notna(ret63) and ret63 < 0
    momentum_positive = pd.notna(ret63) and ret63 > 0
    relative_positive = pd.notna(rel_strength) and rel_strength > 0
    relative_negative = pd.notna(rel_strength) and rel_strength < 0

    # 과열 이격도 조건:
    # ma20_gap이 과거 기준 상위권이거나, 최소 5% 이상이면 과열 후보 신호로 본다.
    gap_overheated = False
    if pd.notna(ma20_gap):
        if pd.notna(ma20_gap_q90):
            gap_overheated = ma20_gap > ma20_gap_q90
        else:
            gap_overheated = ma20_gap > 0.05
    high_vol_mixed = (
        large_up >= 1 and
        large_down >= 1 and
        vol_rising
    )
    risk_score = 0
    risk_score += 2 if large_down >= 2 else 0
    risk_score += 1 if medium_down >= 3 else 0
    risk_score += 1 if risk_event_count >= 4 else 0
    risk_score += 1 if momentum_negative else 0
    risk_score += 1 if trend_negative else 0
    risk_score += 1 if vol_rising else 0
    risk_score += 1 if relative_negative else 0

    overheat_score = 0
    overheat_score += 2 if large_up >= 2 else 0
    overheat_score += 1 if medium_up >= 3 else 0
    overheat_score += 1 if overheat_event_count >= 4 else 0
    overheat_score += 1 if momentum_positive else 0
    overheat_score += 1 if trend_positive else 0
    overheat_score += 1 if gap_overheated else 0
    overheat_score += 1 if vol_rising else 0

    recovery_score = 0
    recovery_score += 1 if momentum_positive else 0
    recovery_score += 1 if trend_positive else 0
    recovery_score += 1 if relative_positive else 0
    recovery_score += 1 if risk_event_count <= 1 else 0
    recovery_score += 1 if pd.notna(vol20) and pd.notna(vol60) and vol20 <= vol60 else 0

    # 상태명 결정
    # 상태명 결정
    if risk_score >= 5 and large_down >= 2:
        state = "강한 위험악화"
        reason = "큰 하락 사건과 위험 지표가 동시에 강하게 나타남"
    elif high_vol_mixed and risk_score >= 3 and overheat_score >= 3:
        state = "고변동성 혼합구간"
        reason = "큰 상승과 큰 하락이 함께 나타나고 단기 변동성이 확대됨"
    elif risk_score >= 4:
        state = "위험악화"
        reason = "하락 사건·약세 추세·변동성 확대 신호가 우세함"
    elif overheat_score >= 5 and vol_rising:
        state = "불안정 과열"
        reason = "큰 상승 사건이 많지만 변동성도 함께 확대됨"
    elif overheat_score >= 4:
        state = "과열 후보"
        reason = "상승 사건과 양호한 추세가 강하지만 과도한 상승 여부 확인 필요"
    elif recovery_score >= 4:
        state = "안정적 회복 후보"
        reason = "추세·상대강도·변동성 안정 신호가 함께 나타남"
    elif recovery_score >= 3:
        state = "회복 후보"
        reason = "일부 회복 신호가 나타나지만 아직 확정적이지 않음"
    else:
        state = "중립/혼조"
        reason = "위험악화·과열·회복 중 어느 한쪽이 뚜렷하지 않음"

    return pd.Series({
        "risk_score": risk_score,
        "overheat_score": overheat_score,
        "recovery_score": recovery_score,
        "vol_rising": vol_rising,
        "trend_negative": trend_negative,
        "trend_positive": trend_positive,
        "momentum_negative": momentum_negative,
        "momentum_positive": momentum_positive,
        "relative_positive": relative_positive,
        "relative_negative": relative_negative,
        "gap_overheated": gap_overheated,
        "high_vol_mixed": high_vol_mixed,
        "HSIStateLabel": state,
        "StateReason": reason
    })


def classify_states(merged: pd.DataFrame) -> pd.DataFrame:
    state_cols = merged.apply(classify_row, axis=1)
    result = pd.concat([merged, state_cols], axis=1)

    # HSI 방향을 아주 단순한 1차 보조 점수로 표현한다.
    # +는 위험악화 쪽, -는 위험완화·회복 쪽으로 해석한다.
    result["hsi_direction_score_draft"] = (
        result["risk_score"]
        + 0.5 * result["overheat_score"]
        - result["recovery_score"]
    )

    return result


def make_state_summary(labels: pd.DataFrame) -> pd.DataFrame:
    summary = (
        labels
        .groupby("HSIStateLabel")
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )
    return summary


def load_event_calendar(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    cal = pd.read_csv(path, encoding="utf-8-sig")
    cal["StartDate"] = pd.to_datetime(cal["StartDate"], errors="coerce")
    cal["EndDate"] = pd.to_datetime(cal["EndDate"], errors="coerce")
    return cal


def check_event_period_states(labels: pd.DataFrame, event_calendar: pd.DataFrame) -> pd.DataFrame:
    """
    사건 달력 구간과 월별 HSI 상태명을 연결한다.

    주의:
    월별 리밸런싱 분석에서는 사건이 2024-08-01~2024-08-05처럼 짧아도
    해당 사건이 속한 월 전체와 연결해서 확인한다.
    """
    if labels.empty or event_calendar.empty:
        return pd.DataFrame()

    temp = labels.copy()
    temp["Month"] = temp["Month"].astype(str)

    rows = []
    distribution_rows = []

    for _, event in event_calendar.iterrows():
        start = event["StartDate"]
        end = event["EndDate"]

        if pd.isna(start) or pd.isna(end):
            continue

        start_month = start.to_period("M").strftime("%Y-%m")
        end_month = end.to_period("M").strftime("%Y-%m")

        sub = temp[
            (temp["Month"] >= start_month) &
            (temp["Month"] <= end_month)
        ].copy()

        if sub.empty:
            rows.append({
                "Market": event.get("Market", ""),
                "EventName": event.get("EventName", ""),
                "EventType": event.get("EventType", ""),
                "ExpectedHSIDirection": event.get("ExpectedHSIDirection", ""),
                "StartMonth": start_month,
                "EndMonth": end_month,
                "OverlapStatus": "no_overlap",
                "ObsCount": 0,
                "AssetCount": 0,
                "MeanRiskScore": np.nan,
                "MeanOverheatScore": np.nan,
                "MeanRecoveryScore": np.nan,
                "MostCommonState": "",
                "MostCommonStateCount": 0
            })
            continue

        state_counts = sub["HSIStateLabel"].value_counts()
        most_common_state = state_counts.index[0]
        most_common_count = int(state_counts.iloc[0])

        rows.append({
            "Market": event.get("Market", ""),
            "EventName": event.get("EventName", ""),
            "EventType": event.get("EventType", ""),
            "ExpectedHSIDirection": event.get("ExpectedHSIDirection", ""),
            "StartMonth": start_month,
            "EndMonth": end_month,
            "OverlapStatus": "overlap",
            "ObsCount": len(sub),
            "AssetCount": sub["Ticker"].nunique(),
            "MeanRiskScore": sub["risk_score"].mean(),
            "MeanOverheatScore": sub["overheat_score"].mean(),
            "MeanRecoveryScore": sub["recovery_score"].mean(),
            "MostCommonState": most_common_state,
            "MostCommonStateCount": most_common_count
        })

        for state_name, count in state_counts.items():
            distribution_rows.append({
                "Market": event.get("Market", ""),
                "EventName": event.get("EventName", ""),
                "EventType": event.get("EventType", ""),
                "ExpectedHSIDirection": event.get("ExpectedHSIDirection", ""),
                "StartMonth": start_month,
                "EndMonth": end_month,
                "HSIStateLabel": state_name,
                "Count": int(count),
                "Share": float(count / len(sub))
            })

    summary = pd.DataFrame(rows)
    distribution = pd.DataFrame(distribution_rows)

    distribution.to_csv(
        OUTPUT_TABLE_DIR / "event_period_state_distribution.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return summary


def main() -> None:
    price = load_price_data(PRICE_PATH)
    events = load_monthly_events(MONTHLY_EVENT_PATH)

    daily_indicators = calculate_daily_indicators(price)
    month_end = make_month_end_indicators(daily_indicators)

    merged = merge_indicators_and_events(month_end, events)
    labels = classify_states(merged)
    state_summary = make_state_summary(labels)

    event_calendar = load_event_calendar(EVENT_CALENDAR_PATH)
    event_period_check = check_event_period_states(labels, event_calendar)

    labels.to_csv(OUTPUT_TABLE_DIR / "monthly_hsi_state_labels.csv", index=False, encoding="utf-8-sig")
    state_summary.to_csv(OUTPUT_TABLE_DIR / "monthly_hsi_state_summary.csv", index=False, encoding="utf-8-sig")
    event_period_check.to_csv(OUTPUT_TABLE_DIR / "event_period_state_check.csv", index=False, encoding="utf-8-sig")

    print("[완료] 월별 HSI 상태명 분류")
    print(f"- 가격 데이터: {PRICE_PATH}")
    print(f"- 사건 카운트: {MONTHLY_EVENT_PATH}")
    print()
    print("[생성 파일]")
    print(f"- {OUTPUT_TABLE_DIR / 'monthly_hsi_state_labels.csv'}")
    print(f"- {OUTPUT_TABLE_DIR / 'monthly_hsi_state_summary.csv'}")
    print(f"- {OUTPUT_TABLE_DIR / 'event_period_state_check.csv'}")
    print()
    print("[상태명 요약]")
    print(state_summary.to_string(index=False))

    if not event_period_check.empty:
        print()
        print("[사건 구간별 상태명 확인]")
        print(event_period_check[[
            "Market", "EventName", "OverlapStatus",
            "ObsCount", "MostCommonState", "MostCommonStateCount"
        ]].to_string(index=False))


if __name__ == "__main__":
    main()
