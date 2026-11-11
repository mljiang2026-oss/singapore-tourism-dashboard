"""Streamlit dashboard for Singapore tourism and hotel recovery."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

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
from src.plots import (
    build_hotel_metric_chart,
    build_market_arrivals_chart,
    build_market_composition_chart,
    build_market_recovery_chart,
    build_market_recovery_ranking,
    build_market_share_change_chart,
    build_recovery_comparison_chart,
    build_total_arrivals_chart,
    phase_key_html,
)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"
VISITOR_FILE = DATA_DIR / "visitor_arrivals_2019_2025.csv"
HOTEL_FILE = DATA_DIR / "hotel_statistics_2019_2025.csv"
BASELINE_YEAR = 2019
MAJOR_MARKET_COUNT = 15

ARRIVALS_SOURCE = (
    "https://data.gov.sg/datasets/"
    "d_7e7b2ee60c6ffc962f80fef129cf306e/view"
)
HOTEL_SOURCE = (
    "https://data.gov.sg/datasets/"
    "d_8e62605f0c1c948702b6ea0fe45242d3/view"
)

st.set_page_config(
    page_title="Singapore Tourism Recovery",
    page_icon="🌏",
    layout="wide",
)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    visitors = pd.read_csv(VISITOR_FILE, parse_dates=["date"])
    hotels = pd.read_csv(HOTEL_FILE, parse_dates=["date"])
    return visitors, hotels


def show_phase_key() -> None:
    """Display one compact key instead of repeating labels inside small charts."""
    st.markdown(phase_key_html(), unsafe_allow_html=True)


st.markdown(
    """
    <style>
    .block-container {padding-top: 2.4rem; padding-bottom: 3rem;}
    .phase-key {display:flex; flex-wrap:wrap; gap:.65rem 1rem; margin:.1rem 0 .8rem;}
    .phase-item {display:inline-flex; align-items:center; gap:.35rem; font-size:.84rem; color:#475569;}
    .phase-swatch {width:.72rem; height:.72rem; border-radius:.18rem; opacity:.65;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Singapore Tourism Recovery")
st.caption(
    "International visitor arrivals, source-market change and gazetted-hotel "
    "performance using monthly official data, January 2019-December 2025."
)

if not VISITOR_FILE.exists() or not HOTEL_FILE.exists():
    st.error("Processed data files are missing. Run the data-wrangling script first.")
    st.code("python src/wrangle.py", language="bash")
    st.stop()

visitors, hotels = load_data()
latest_complete_year = int(visitors["year"].max())
countries = sorted(
    visitors.loc[visitors["market_type"] == "country", "market"].unique()
)

default_markets = [
    market
    for market in ["China", "Indonesia", "India", "Australia", "Malaysia"]
    if market in countries
]

st.sidebar.header("Explore the data")
year_range = st.sidebar.slider(
    "Year range",
    min_value=int(visitors["year"].min()),
    max_value=latest_complete_year,
    value=(BASELINE_YEAR, latest_complete_year),
)
st.sidebar.caption(
    "The year filter controls the Markets and Hotels pages. Overview and Visitor "
    "mix use the complete-year comparison of 2019 and 2025."
)
filtered_hotels = hotels[hotels["year"].between(year_range[0], year_range[1])].copy()

market_comparison = annual_market_comparison(
    visitors, BASELINE_YEAR, latest_complete_year
)
major_recovery = major_market_recovery(
    market_comparison, number_of_markets=MAJOR_MARKET_COUNT
)
fastest_market = major_recovery.iloc[0]

total_annual = annual_total_arrivals(visitors).set_index("year")
hotel_annual = annual_hotel_summary(hotels).set_index("year")
baseline_total = float(total_annual.loc[BASELINE_YEAR, "arrivals"])
latest_total = float(total_annual.loc[latest_complete_year, "arrivals"])
total_recovery_pct = latest_total / baseline_total * 100

baseline_hotel = hotel_annual.loc[BASELINE_YEAR]
latest_hotel = hotel_annual.loc[latest_complete_year]
occupancy_change_pp = (
    latest_hotel["occupancy_pct"] - baseline_hotel["occupancy_pct"]
)
room_rate_change_pct = (
    latest_hotel["room_rate_sgd"] / baseline_hotel["room_rate_sgd"] - 1
) * 100
revenue_change_pct = (
    latest_hotel["room_revenue_sgd_thousand"]
    / baseline_hotel["room_revenue_sgd_thousand"]
    - 1
) * 100

story_tab, markets_tab, mix_tab, hotels_tab, methods_tab = st.tabs(
    [
        "Overview",
        "Markets",
        "Visitor mix",
        "Hotels",
        "Methods",
    ]
)

with story_tab:
    headline_1, headline_2, headline_3, headline_4 = st.columns(4)
    headline_1.metric(
        f"Visitors in {latest_complete_year}",
        f"{latest_total / 1_000_000:.2f}M",
        f"{total_recovery_pct - 100:.1f}% vs 2019",
    )
    headline_2.metric(
        "Fastest major recovery",
        str(fastest_market["market"]),
        f"{fastest_market['recovery_pct']:.1f}% of 2019",
    )
    headline_3.metric(
        "Nominal room revenue",
        f"S${latest_hotel['room_revenue_sgd_thousand'] / 1_000_000:.2f}B",
        f"{revenue_change_pct:+.1f}% vs 2019",
    )
    headline_4.metric(
        "Hotel occupancy",
        f"{latest_hotel['occupancy_pct']:.1f}%",
        f"{occupancy_change_pp:+.1f} pp vs 2019",
    )

    st.subheader("The recovery is clearer when divided into phases")
    st.write(
        "One continuous monthly series, read across four distinct phases: baseline, "
        "shock, reopening and recovery."
    )

    total_monthly = visitors[visitors["market_type"] == "total"].copy()
    story_figure = build_total_arrivals_chart(total_monthly)
    st.plotly_chart(story_figure, width="stretch")

    st.info(
        f"By {latest_complete_year}, total arrivals had recovered to "
        f"{total_recovery_pct:.1f}% of the 2019 level. Recovery was substantial, "
        "but not yet complete."
    )

    left_story, right_story = st.columns(2)
    with left_story:
        st.markdown("#### Which major market recovered fastest?")
        ranking = major_recovery.head(10).sort_values("recovery_pct")
        ranking_figure = build_market_recovery_ranking(
            ranking,
            latest_complete_year,
        )
        st.plotly_chart(ranking_figure, width="stretch")
        st.caption(
            f"Major markets are defined as the {MAJOR_MARKET_COUNT} largest source "
            "markets in 2019. This avoids calling a very small market the fastest "
            "because of a low starting point."
        )

    with right_story:
        st.markdown("#### Did hotels recover for the same reason?")
        st.metric(
            "Nominal average room rate",
            f"S${latest_hotel['room_rate_sgd']:,.0f}",
            f"{room_rate_change_pct:+.1f}% vs 2019",
        )
        st.metric(
            "Total visitor arrivals",
            f"{total_recovery_pct:.1f}% of 2019",
        )
        st.write(
            "Nominal hotel room revenue exceeded its 2019 level even though visitor arrivals and "
            "occupancy had not fully returned. Higher nominal room rates therefore matter "
            "to the revenue story; visitor volume alone is not a sufficient explanation."
        )
        st.warning(
            "This is descriptive evidence. It does not prove that visitor arrivals caused "
            "hotel outcomes. Inflation, room supply, business travel, major events and "
            "staycations may also contribute."
        )

with markets_tab:
    st.subheader("Explore source-market recovery")
    selected_markets = st.multiselect(
        "Source markets",
        options=countries,
        default=default_markets,
        help="Source market means place of residence, not citizenship.",
    )
    show_2019_reference = st.checkbox(
        "Show the 2019 reference line on the recovery chart",
        value=True,
    )

    country_data = visitors[
        (visitors["market_type"] == "country")
        & (visitors["market"].isin(selected_markets))
    ].copy()
    filtered_visitors = country_data[
        country_data["year"].between(year_range[0], year_range[1])
    ].copy()

    if not selected_markets:
        st.warning("Select at least one source market to display the charts.")
    elif filtered_visitors.empty:
        st.warning("No visitor-arrival data are available for the selected filters.")
    else:
        latest_visitor_date = filtered_visitors["date"].max()
        latest_selected_arrivals = int(
            filtered_visitors.loc[
                filtered_visitors["date"] == latest_visitor_date, "arrivals"
            ].sum()
        )
        selected_recovery_pct = same_month_recovery(
            country_data,
            latest_visitor_date,
            BASELINE_YEAR,
        )

        selected_1, selected_2 = st.columns(2)
        selected_1.metric(
            f"Selected arrivals, {latest_visitor_date:%b %Y}",
            f"{latest_selected_arrivals:,.0f}",
        )
        selected_2.metric(
            "Recovery vs matching 2019 month",
            "n.a."
            if selected_recovery_pct is None
            else f"{selected_recovery_pct:.1f}%",
        )

        st.subheader("Visitor arrivals by selected source market")
        arrivals_figure = build_market_arrivals_chart(filtered_visitors)
        st.plotly_chart(arrivals_figure, width="stretch")

        st.subheader("Recovery relative to the same month in 2019")
        recovery_data = recovery_index_by_market(country_data, BASELINE_YEAR)
        recovery_data = recovery_data[
            recovery_data["year"].between(year_range[0], year_range[1])
        ]
        recovery_figure = build_market_recovery_chart(
            recovery_data,
            show_reference=show_2019_reference,
        )
        st.plotly_chart(recovery_figure, width="stretch")
        st.caption(
            "Each month is compared with the matching calendar month in 2019, "
            "reducing distortion from regular seasonal peaks and troughs."
        )

        st.subheader("Annual comparison for the selected markets")
        selected_annual = (
            filtered_visitors.groupby(["market", "year"], as_index=False)[
                "arrivals"
            ]
            .sum()
            .pivot(index="market", columns="year", values="arrivals")
            .reset_index()
        )
        selected_annual.columns = [
            str(column) for column in selected_annual.columns
        ]
        recovery_column = f"{year_range[1]} vs {year_range[0]} recovery (%)"
        if (
            year_range[0] != year_range[1]
            and str(year_range[0]) in selected_annual.columns
            and str(year_range[1]) in selected_annual.columns
        ):
            selected_baseline = selected_annual[str(year_range[0])].where(
                selected_annual[str(year_range[0])] > 0
            )
            selected_annual[recovery_column] = (
                selected_annual[str(year_range[1])].div(selected_baseline) * 100
            )
        selected_config = {
            str(year): st.column_config.NumberColumn(
                f"{year} arrivals", format="%,d"
            )
            for year in range(year_range[0], year_range[1] + 1)
            if str(year) in selected_annual.columns
        }
        if recovery_column in selected_annual.columns:
            selected_config[recovery_column] = st.column_config.NumberColumn(
                recovery_column, format="%.1f%%"
            )
        st.dataframe(
            selected_annual,
            width="stretch",
            hide_index=True,
            column_config=selected_config,
        )

with mix_tab:
    st.subheader("The source-market mix changed after the disruption")
    st.write(
        "Absolute arrivals answer how many visitors came. Market share answers whether "
        "Singapore became more or less dependent on particular source markets."
    )

    composition = composition_with_other(
        market_comparison,
        BASELINE_YEAR,
        latest_complete_year,
        number_of_markets=5,
    )
    composition_figure = build_market_composition_chart(composition)
    st.plotly_chart(composition_figure, width="stretch")

    major_share_change = major_recovery.sort_values("share_change_pp")
    share_figure = build_market_share_change_chart(
        major_share_change,
        BASELINE_YEAR,
        latest_complete_year,
    )
    st.plotly_chart(share_figure, width="stretch")

    largest_gain = major_share_change.iloc[-1]
    largest_loss = major_share_change.iloc[0]
    st.info(
        f"Among the major 2019 markets, {largest_gain['market']} recorded the largest "
        f"share gain ({largest_gain['share_change_pp']:+.2f} percentage points), while "
        f"{largest_loss['market']} recorded the largest decline "
        f"({largest_loss['share_change_pp']:+.2f} percentage points)."
    )

    with st.expander("View the full 2019-2025 comparison table"):
        mix_table = market_comparison.sort_values(
            "comparison_arrivals", ascending=False
        ).rename(
            columns={
                "market": "Source market",
                "baseline_arrivals": "2019 arrivals",
                "comparison_arrivals": f"{latest_complete_year} arrivals",
                "recovery_pct": "Recovery (%)",
                "baseline_share_pct": "2019 share (%)",
                "comparison_share_pct": f"{latest_complete_year} share (%)",
                "share_change_pp": "Share change (pp)",
            }
        )
        st.dataframe(
            mix_table,
            width="stretch",
            hide_index=True,
            column_config={
                "2019 arrivals": st.column_config.NumberColumn(format="%,d"),
                f"{latest_complete_year} arrivals": st.column_config.NumberColumn(
                    format="%,d"
                ),
                "Recovery (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "2019 share (%)": st.column_config.NumberColumn(format="%.2f%%"),
                f"{latest_complete_year} share (%)": st.column_config.NumberColumn(
                    format="%.2f%%"
                ),
                "Share change (pp)": st.column_config.NumberColumn(format="%+.2f"),
            },
        )

with hotels_tab:
    latest_hotel_date = filtered_hotels["date"].max()
    occupancy = hotel_value(
        filtered_hotels, "Average Hotel Occupancy Rate", latest_hotel_date
    )
    room_rate = hotel_value(
        filtered_hotels, "Average Room Rate", latest_hotel_date
    )

    hotel_1, hotel_2 = st.columns(2)
    hotel_1.metric(
        f"Hotel occupancy, {latest_hotel_date:%b %Y}",
        "n.a." if occupancy is None else f"{occupancy:.1f}%",
    )
    hotel_2.metric(
        f"Nominal average room rate, {latest_hotel_date:%b %Y}",
        "n.a." if room_rate is None else f"S${room_rate:,.0f}",
    )

    overall_hotels = filtered_hotels[
        filtered_hotels["segment"] == "All gazetted hotels"
    ].copy()
    occupancy_data = overall_hotels[
        overall_hotels["metric"] == "Average Hotel Occupancy Rate"
    ]
    room_rate_data = overall_hotels[
        overall_hotels["metric"] == "Average Room Rate"
    ]

    show_phase_key()
    left_chart, right_chart = st.columns(2)
    with left_chart:
        occupancy_figure = build_hotel_metric_chart(
            occupancy_data,
            title="Average hotel occupancy rate",
            y_axis_label="Occupancy rate (%)",
            colour="#2563EB",
        )
        st.plotly_chart(occupancy_figure, width="stretch")
    with right_chart:
        rate_figure = build_hotel_metric_chart(
            room_rate_data,
            title="Nominal average room rate",
            y_axis_label="Nominal average room rate (S$)",
            colour="#0F766E",
        )
        st.plotly_chart(rate_figure, width="stretch")

    st.subheader(
        "Visitor arrivals and nominal room revenue moved together, but not identically"
    )
    show_phase_key()
    comparison = arrivals_room_revenue_recovery(
        visitors,
        hotels,
        BASELINE_YEAR,
        year_range[0],
        year_range[1],
    )
    comparison_figure = build_recovery_comparison_chart(comparison)
    st.plotly_chart(comparison_figure, width="stretch")

    arrivals_index = comparison[
        comparison["series"] == "Total visitor arrivals"
    ]
    revenue_index = comparison[
        comparison["series"] == "Nominal hotel room revenue"
    ]
    monthly_correlation = paired_recovery_correlation(
        arrivals_index,
        revenue_index,
    )
    st.metric(
        "Descriptive monthly correlation",
        f"{monthly_correlation:.2f}",
        help=(
            "Pearson correlation between the two same-month 2019 recovery indices "
            "for the selected year range."
        ),
    )
    st.warning(
        "A high correlation means the two recovery indices often moved together; it does not show "
        "that one caused the other. Prices, inflation, room supply, business travel, "
        "staycations and major events are plausible additional explanations."
    )

with methods_tab:
    st.subheader("Data sources")
    st.markdown(
        f"- [International Visitor Arrivals By Place Of Residence, Monthly]({ARRIVALS_SOURCE})\n"
        f"- [Hotel Statistics, Monthly]({HOTEL_SOURCE})"
    )
    st.write(
        "Both datasets are published on data.gov.sg and sourced from the Singapore "
        "Tourism Board. The project uses complete calendar years from 2019 through 2025."
    )

    st.subheader("How the story is measured")
    st.markdown(
        "- **Monthly recovery index:** current month divided by the matching month in 2019.\n"
        "- **Annual market recovery:** 2025 annual arrivals divided by 2019 annual arrivals.\n"
        f"- **Major market ranking:** limited to the {MAJOR_MARKET_COUNT} largest markets in 2019.\n"
        "- **Visitor share:** a market's arrivals divided by arrivals from all country markets.\n"
        "- **Descriptive correlation:** Pearson correlation between the two same-month "
        "2019 recovery indices; it shows co-movement, not causation."
    )

    st.subheader("Analytical phases")
    st.markdown(
        "- **2019 baseline:** pre-disruption comparison year.\n"
        "- **March 2020-2021 pandemic shock:** exceptional collapse in international arrivals.\n"
        "- **2022 reopening:** initial return of cross-border travel.\n"
        "- **2023-2025 recovery:** continued recovery and changing source-market mix."
    )

    st.subheader("Limitations")
    st.markdown(
        "- Source market means place of residence, not citizenship.\n"
        "- Aggregated monthly data cannot identify individual behaviour or establish causality.\n"
        "- Hotel statistics cover gazetted hotels rather than every accommodation provider.\n"
        "- Room rates and revenue are nominal and are not adjusted for inflation.\n"
        "- Results can also reflect border policy, flight capacity, exchange rates and events."
    )

    st.subheader("Download filtered data")
    st.download_button(
        "Download selected visitor-arrival data",
        data=filtered_visitors.to_csv(index=False).encode("utf-8"),
        file_name="selected_visitor_arrivals.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download selected hotel data",
        data=filtered_hotels.to_csv(index=False).encode("utf-8"),
        file_name="selected_hotel_statistics.csv",
        mime="text/csv",
    )
