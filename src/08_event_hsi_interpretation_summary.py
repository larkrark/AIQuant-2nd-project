from pathlib import Path
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_DIR / "output" / "tables"

INPUT_PATH = TABLE_DIR / "event_period_state_distribution.csv"
OUTPUT_PATH = TABLE_DIR / "event_hsi_interpretation_summary.csv"


def make_interpretation(event_name: str, top_state: str, second_state: str) -> str:
    if "COVID crash" in event_name:
        return (
            "코로나 급락 구간은 강한 위험악화가 주된 상태로 나타났다. "
            "다만 일부 자산에서는 반등과 급등락이 함께 나타나 불안정 과열 또는 고변동성 혼합구간도 관측되었다."
        )

    if "COVID liquidity rebound" in event_name:
        return (
            "코로나 이후 유동성 반등 구간은 과열 후보와 강한 위험악화가 함께 높게 나타났다. "
            "이는 단순한 안정적 회복장이 아니라 급락 이후 반등과 잔존 위험이 공존한 혼합 국면으로 해석된다."
        )

    if "Inflation" in event_name or "rate-hike" in event_name:
        return (
            "인플레이션 및 금리 인상 충격 구간은 강한 위험악화가 가장 많이 나타났다. "
            "다만 일부 과열 후보와 고변동성 혼합구간도 함께 관측되어 자산별 반응 차이가 존재했음을 보여준다."
        )

    if "Battery" in event_name:
        return (
            "2차전지 테마 과열 구간은 특정 테마에서는 과열 성격이 강했지만, "
            "한국 ETF 전체 자산군 기준에서는 위험악화가 가장 많이 나타났다. "
            "따라서 이 구간은 순수 과열장이라기보다 테마 과열과 시장 전반의 위험 신호가 혼재한 구간으로 해석된다."
        )

    if "carry-trade" in event_name or "Global tech" in event_name:
        return (
            "2024년 8월 글로벌 기술주 및 엔캐리 청산 충격 구간은 강한 위험악화와 고변동성 혼합구간이 높게 나타났다. "
            "이는 단순 하락 구간이 아니라 급락, 일부 반등, 자산별 차별적 움직임이 함께 나타난 충격성 혼합 구간으로 해석된다."
        )

    return (
        f"해당 사건 구간에서는 {top_state}가 가장 많이 나타났고, "
        f"{second_state}도 함께 관측되었다. 따라서 단일 상태로 단정하기보다 복수의 HSI 상태가 혼재한 구간으로 해석한다."
    )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"입력 파일이 없습니다: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")

    if df.empty:
        raise ValueError(f"입력 파일이 비어 있습니다: {INPUT_PATH}")

    rows = []

    group_cols = [
        "Market",
        "EventName",
        "EventType",
        "ExpectedHSIDirection",
        "StartMonth",
        "EndMonth",
    ]

    for keys, group in df.groupby(group_cols, dropna=False):
        group = group.sort_values("Share", ascending=False).reset_index(drop=True)

        top = group.iloc[0]
        second = group.iloc[1] if len(group) > 1 else None

        top_state = top["HSIStateLabel"]
        top_share = top["Share"]

        if second is not None:
            second_state = second["HSIStateLabel"]
            second_share = second["Share"]
        else:
            second_state = ""
            second_share = 0.0

        market, event_name, event_type, expected_direction, start_month, end_month = keys

        rows.append({
            "Market": market,
            "EventName": event_name,
            "EventType": event_type,
            "ExpectedHSIDirection": expected_direction,
            "StartMonth": start_month,
            "EndMonth": end_month,
            "TopState": top_state,
            "TopStateShare": top_share,
            "SecondState": second_state,
            "SecondStateShare": second_share,
            "Interpretation": make_interpretation(event_name, top_state, second_state),
        })

    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("[완료] 사건별 HSI 해석 요약표 생성")
    print(f"- 입력: {INPUT_PATH}")
    print(f"- 출력: {OUTPUT_PATH}")
    print()
    print(summary[[
        "Market",
        "EventName",
        "StartMonth",
        "EndMonth",
        "TopState",
        "TopStateShare",
        "SecondState",
        "SecondStateShare",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()