from pathlib import Path

import pandas as pd
import pytest

from src.analysis import (
    arrivals_room_revenue_recovery,
    annual_hotel_summary,
    annual_market_comparison,
    annual_total_arrivals,
    composition_with_other,
    hotel_value,
    major_market_recovery,
    paired_recovery_correlation,
    recovery_index_by_market,
    same_month_recovery,
)


BASE_DIR = Path(__file__).resolve().parents[1]
VISITOR_FILE = BASE_DIR / "data" / "processed" / "visitor_arrivals_2019_2025.csv"
HOTEL_FILE = BASE_DIR / "data" / "processed" / "hotel_statistics_2019_2025.csv"


@pytest.fixture(scope="module")
def visitors() -> pd.DataFrame:
    return pd.read_csv(VISITOR_FILE, parse_dates=["date"])


@pytest.fixture(scope="module")
def hotels() -> pd.DataFrame:
    return pd.read_csv(HOTEL_FILE, parse_dates=["date"])


def test_market_comparison_uses_annual_totals(visitors: pd.DataFrame) -> None:
    comparison = annual_market_comparison(visitors, 2019, 2025).set_index("market")

    assert comparison.loc["Australia", "recovery_pct"] == pytest.approx(110.85, 0.01)
    assert comparison.loc["Malaysia", "comparison_share_pct"] > comparison.loc[
        "Malaysia", "baseline_share_pct"
    ]


def test_major_market_ranking_avoids_small_baselines(visitors: pd.DataFrame) -> None:
    comparison = annual_market_comparison(visitors, 2019, 2025)
    ranking = major_market_recovery(comparison, number_of_markets=15)

    assert len(ranking) == 15
    assert ranking.iloc[0]["market"] == "Australia"
    assert ranking["recovery_pct"].is_monotonic_decreasing


def test_composition_sums_to_one_hundred(visitors: pd.DataFrame) -> None:
    comparison = annual_market_comparison(visitors, 2019, 2025)
    composition = composition_with_other(comparison, 2019, 2025)

    totals = composition.groupby("year")["share_pct"].sum()
    assert totals.loc["2019"] == pytest.approx(100)
    assert totals.loc["2025"] == pytest.approx(100)


def test_annual_headline_summaries(visitors: pd.DataFrame, hotels: pd.DataFrame) -> None:
    arrivals = annual_total_arrivals(visitors).set_index("year")
    hotel_summary = annual_hotel_summary(hotels).set_index("year")

    assert arrivals.loc[2025, "arrivals"] == 16_912_288
    assert hotel_summary.loc[2025, "occupancy_pct"] == pytest.approx(81.94, 0.01)
    assert hotel_summary.loc[2025, "room_revenue_sgd_thousand"] > hotel_summary.loc[
        2019, "room_revenue_sgd_thousand"
    ]


def test_market_comparison_rejects_missing_year(visitors: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="missing comparison years"):
        annual_market_comparison(visitors, 2019, 2026)


def test_recovery_correlation_aligns_dates_and_uses_both_indices() -> None:
    arrivals_index = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-01", "2023-02-01", "2023-03-01"]),
            "value": [40.0, 70.0, 100.0],
        }
    )
    revenue_index = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-03-01", "2023-01-01", "2023-02-01"]),
            "value": [110.0, 50.0, 80.0],
        }
    )

    assert paired_recovery_correlation(
        arrivals_index, revenue_index
    ) == pytest.approx(1.0)


def test_monthly_recovery_uses_matching_2019_month(
    visitors: pd.DataFrame,
) -> None:
    australia = visitors[
        (visitors["market_type"] == "country")
        & (visitors["market"] == "Australia")
    ]
    recovery = recovery_index_by_market(australia, 2019)

    assert recovery.loc[
        recovery["year"] == 2019, "recovery_index"
    ].eq(100).all()
    latest_date = pd.Timestamp("2025-12-01")
    expected = recovery.loc[
        recovery["date"] == latest_date, "recovery_index"
    ].iloc[0]
    assert same_month_recovery(australia, latest_date, 2019) == pytest.approx(
        expected
    )


def test_hotel_value_uses_all_gazetted_hotels(hotels: pd.DataFrame) -> None:
    value = hotel_value(
        hotels,
        "Average Room Rate",
        pd.Timestamp("2025-12-01"),
    )

    assert value == pytest.approx(280.4)


def test_arrivals_and_room_revenue_indices_are_aligned(
    visitors: pd.DataFrame,
    hotels: pd.DataFrame,
) -> None:
    comparison = arrivals_room_revenue_recovery(
        visitors,
        hotels,
        baseline_year=2019,
        start_year=2019,
        end_year=2025,
    )

    assert set(comparison["series"]) == {
        "Total visitor arrivals",
        "Nominal hotel room revenue",
    }
    baseline = comparison[comparison["date"].dt.year == 2019]
    assert baseline["value"].eq(100).all()
    counts = comparison.groupby("series")["date"].nunique()
    assert counts.nunique() == 1
