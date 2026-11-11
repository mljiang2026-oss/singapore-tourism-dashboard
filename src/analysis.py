"""Reusable analysis helpers for the tourism recovery dashboard."""

from __future__ import annotations

import pandas as pd


def recovery_index_by_market(
    data: pd.DataFrame,
    baseline_year: int,
) -> pd.DataFrame:
    """Compare each market-month with the matching baseline-year month."""
    baseline = (
        data[data["year"] == baseline_year][["market", "month", "arrivals"]]
        .rename(columns={"arrivals": "baseline_arrivals"})
        .drop_duplicates(["market", "month"])
    )
    result = data.merge(
        baseline,
        on=["market", "month"],
        how="left",
        validate="many_to_one",
    )
    valid_baseline = result["baseline_arrivals"].where(
        result["baseline_arrivals"] > 0
    )
    result["recovery_index"] = result["arrivals"].div(valid_baseline) * 100
    return result


def same_month_recovery(
    data: pd.DataFrame,
    latest_date: pd.Timestamp,
    baseline_year: int,
) -> float | None:
    """Return recovery for a selected month against its baseline-year month."""
    latest_value = data.loc[data["date"] == latest_date, "arrivals"].sum()
    baseline_value = data.loc[
        (data["year"] == baseline_year)
        & (data["month"] == latest_date.month),
        "arrivals",
    ].sum()
    if baseline_value <= 0:
        return None
    return float(latest_value / baseline_value * 100)


def hotel_value(
    hotels: pd.DataFrame,
    metric: str,
    date: pd.Timestamp,
    segment: str = "All gazetted hotels",
) -> float | None:
    """Return one hotel metric for a date and hotel segment."""
    values = hotels.loc[
        (hotels["metric"] == metric)
        & (hotels["segment"] == segment)
        & (hotels["date"] == date),
        "value",
    ]
    return None if values.empty else float(values.iloc[0])


def _same_month_index(
    data: pd.DataFrame,
    value_column: str,
    baseline_year: int,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Create a same-month baseline index for one monthly series."""
    baseline = data[data["year"] == baseline_year][
        ["month", value_column]
    ].rename(columns={value_column: "baseline"})
    selected = data[data["year"].between(start_year, end_year)].copy()
    result = selected.merge(
        baseline,
        on="month",
        how="left",
        validate="many_to_one",
    )
    valid_baseline = result["baseline"].where(result["baseline"] > 0)
    result["recovery_index"] = result[value_column].div(valid_baseline) * 100
    return result


def arrivals_room_revenue_recovery(
    visitors: pd.DataFrame,
    hotels: pd.DataFrame,
    baseline_year: int,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Return aligned recovery indices for arrivals and hotel room revenue."""
    total_arrivals = visitors[visitors["market_type"] == "total"]
    arrivals_index = _same_month_index(
        total_arrivals,
        "arrivals",
        baseline_year,
        start_year,
        end_year,
    )[["date", "recovery_index"]].rename(
        columns={"recovery_index": "value"}
    )
    arrivals_index["series"] = "Total visitor arrivals"

    room_revenue = hotels[
        (hotels["metric"] == "Room Revenue")
        & (hotels["segment"] == "All gazetted hotels")
    ]
    revenue_index = _same_month_index(
        room_revenue,
        "value",
        baseline_year,
        start_year,
        end_year,
    )[["date", "recovery_index"]].rename(
        columns={"recovery_index": "value"}
    )
    revenue_index["series"] = "Nominal hotel room revenue"

    return pd.concat([arrivals_index, revenue_index], ignore_index=True)


def annual_market_comparison(
    visitors: pd.DataFrame,
    baseline_year: int,
    comparison_year: int,
) -> pd.DataFrame:
    """Compare country arrivals and visitor shares between two complete years."""
    countries = visitors[visitors["market_type"] == "country"].copy()
    annual = (
        countries[countries["year"].isin([baseline_year, comparison_year])]
        .groupby(["market", "year"], as_index=False)["arrivals"]
        .sum()
        .pivot(index="market", columns="year", values="arrivals")
    )

    missing_years = {baseline_year, comparison_year} - set(annual.columns)
    if missing_years:
        raise ValueError(f"Visitor data are missing comparison years: {sorted(missing_years)}")

    result = annual.rename(
        columns={
            baseline_year: "baseline_arrivals",
            comparison_year: "comparison_arrivals",
        }
    ).reset_index()
    baseline = result["baseline_arrivals"].where(result["baseline_arrivals"] > 0)
    baseline_total = result["baseline_arrivals"].sum()
    comparison_total = result["comparison_arrivals"].sum()

    result["recovery_pct"] = result["comparison_arrivals"].div(baseline) * 100
    result["baseline_share_pct"] = (
        result["baseline_arrivals"].div(baseline_total) * 100
    )
    result["comparison_share_pct"] = (
        result["comparison_arrivals"].div(comparison_total) * 100
    )
    result["share_change_pp"] = (
        result["comparison_share_pct"] - result["baseline_share_pct"]
    )
    return result


def major_market_recovery(
    comparison: pd.DataFrame,
    number_of_markets: int = 15,
) -> pd.DataFrame:
    """Rank recovery among the largest baseline-year source markets."""
    major_markets = comparison.nlargest(number_of_markets, "baseline_arrivals")
    return major_markets.sort_values("recovery_pct", ascending=False).reset_index(
        drop=True
    )


def composition_with_other(
    comparison: pd.DataFrame,
    baseline_year: int,
    comparison_year: int,
    number_of_markets: int = 8,
) -> pd.DataFrame:
    """Return top source-market shares for a compact 100% composition chart."""
    top_markets = comparison.nlargest(number_of_markets, "baseline_arrivals")[
        "market"
    ].tolist()
    rows: list[dict[str, object]] = []

    for year, share_column in (
        (baseline_year, "baseline_share_pct"),
        (comparison_year, "comparison_share_pct"),
    ):
        selected = comparison[comparison["market"].isin(top_markets)]
        for row in selected.itertuples(index=False):
            rows.append(
                {
                    "year": str(year),
                    "market": row.market,
                    "share_pct": getattr(row, share_column),
                }
            )
        rows.append(
            {
                "year": str(year),
                "market": "Other markets",
                "share_pct": 100 - selected[share_column].sum(),
            }
        )

    return pd.DataFrame(rows)


def annual_total_arrivals(visitors: pd.DataFrame) -> pd.DataFrame:
    """Return one total-arrival observation per calendar year."""
    return (
        visitors[visitors["market_type"] == "total"]
        .groupby("year", as_index=False)["arrivals"]
        .sum()
        .sort_values("year")
    )


def annual_hotel_summary(hotels: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hotel indicators using metric-appropriate annual statistics."""
    overall = hotels[hotels["segment"] == "All gazetted hotels"]
    mean_metrics = {
        "Average Hotel Occupancy Rate": "occupancy_pct",
        "Average Room Rate": "room_rate_sgd",
    }
    pieces = []
    for metric, column in mean_metrics.items():
        piece = (
            overall[overall["metric"] == metric]
            .groupby("year", as_index=False)["value"]
            .mean()
            .rename(columns={"value": column})
        )
        pieces.append(piece)

    revenue = (
        overall[overall["metric"] == "Room Revenue"]
        .groupby("year", as_index=False)["value"]
        .sum()
        .rename(columns={"value": "room_revenue_sgd_thousand"})
    )
    pieces.append(revenue)

    result = pieces[0]
    for piece in pieces[1:]:
        result = result.merge(piece, on="year", how="outer")
    return result.sort_values("year")


def paired_recovery_correlation(
    arrivals_index: pd.DataFrame,
    revenue_index: pd.DataFrame,
) -> float:
    """Return the correlation between aligned monthly recovery-index values."""
    paired = arrivals_index[["date", "value"]].rename(
        columns={"value": "arrivals_index"}
    ).merge(
        revenue_index[["date", "value"]].rename(
            columns={"value": "revenue_index"}
        ),
        on="date",
        how="inner",
        validate="one_to_one",
    )
    if len(paired) < 2:
        raise ValueError("At least two aligned months are required for correlation")
    return float(paired["arrivals_index"].corr(paired["revenue_index"]))
