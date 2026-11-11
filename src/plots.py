"""Plotly chart builders for the tourism recovery dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure


PRIMARY_COLOUR = "#0F766E"
ACCENT_COLOUR = "#F59E0B"
MARKET_COLOURS = {
    "Australia": "#0072B2",
    "China": "#D55E00",
    "India": "#CC79A7",
    "Indonesia": "#E69F00",
    "Japan": "#56B4E9",
    "Malaysia": "#009E73",
    "Philippines": "#8C6D31",
    "USA": "#4D4D4D",
    "Other markets": "#B8C2CC",
}

PHASES = (
    ("2019 baseline", "2019-01-01", "2019-12-31", ACCENT_COLOUR, 0.06),
    ("Pandemic shock", "2020-03-01", "2021-12-31", "#64748B", 0.13),
    ("Reopening", "2022-01-01", "2022-12-31", "#3B82F6", 0.07),
    ("Recovery", "2023-01-01", "2025-12-31", "#10B981", 0.05),
)


def add_phase_shading(
    figure: Figure,
    *,
    labels: bool = False,
    label_font_size: int | None = None,
) -> Figure:
    """Shade the four analytical phases on a time-series chart."""
    for phase, start, end, colour, opacity in PHASES:
        options: dict[str, object] = {
            "x0": start,
            "x1": end,
            "fillcolor": colour,
            "opacity": opacity,
            "line_width": 0,
        }
        if labels:
            options.update(
                annotation_text=phase,
                annotation_position="top left",
            )
            if label_font_size is not None:
                options["annotation_font_size"] = label_font_size
        figure.add_vrect(**options)
    return figure


def polish_figure(figure: Figure, *, legend_title: str = "") -> Figure:
    """Apply the shared dashboard style to a Plotly figure."""
    figure.update_layout(
        hovermode="x unified",
        legend_title_text=legend_title,
        font=dict(color="#1F2937"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=45, b=10),
    )
    return figure


def use_horizontal_legend(figure: Figure) -> Figure:
    """Place a multi-series legend above the plot."""
    figure.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        )
    )
    return figure


def phase_key_html() -> str:
    """Return accessible HTML for the dashboard's analytical-phase key."""
    items = [
        "<span class='phase-item'>"
        f"<span class='phase-swatch' style='background:{colour}'></span>"
        f"{phase}</span>"
        for phase, _start, _end, colour, _opacity in PHASES
    ]
    return "<div class='phase-key'>" + "".join(items) + "</div>"


def build_total_arrivals_chart(total_monthly: pd.DataFrame) -> Figure:
    """Build the overview chart for total monthly visitor arrivals."""
    figure = px.area(
        total_monthly,
        x="date",
        y="arrivals",
        labels={"date": "Month", "arrivals": "Total visitor arrivals"},
        color_discrete_sequence=[PRIMARY_COLOUR],
    )
    add_phase_shading(figure, labels=True)
    return polish_figure(figure)


def build_market_recovery_ranking(
    ranking: pd.DataFrame,
    comparison_year: int,
) -> Figure:
    """Build the horizontal ranking of major-market recovery rates."""
    figure = px.bar(
        ranking,
        x="recovery_pct",
        y="market",
        orientation="h",
        text="recovery_pct",
        color="recovery_pct",
        color_continuous_scale=["#CBD5E1", PRIMARY_COLOUR],
        labels={
            "recovery_pct": f"{comparison_year} arrivals (2019 = 100)",
            "market": "",
        },
    )
    figure.add_vline(
        x=100,
        line_dash="dash",
        line_color="#334155",
        annotation_text="2019 level",
    )
    figure.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    figure.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=10, r=35, t=20, b=10),
    )
    return figure


def build_market_arrivals_chart(data: pd.DataFrame) -> Figure:
    """Build monthly visitor-arrival lines for selected source markets."""
    figure = px.line(
        data,
        x="date",
        y="arrivals",
        color="market",
        color_discrete_map=MARKET_COLOURS,
        labels={
            "date": "Month",
            "arrivals": "Visitor arrivals",
            "market": "Market",
        },
    )
    add_phase_shading(figure)
    polish_figure(figure)
    return use_horizontal_legend(figure)


def build_market_recovery_chart(
    data: pd.DataFrame,
    *,
    show_reference: bool,
) -> Figure:
    """Build same-month recovery lines for selected source markets."""
    figure = px.line(
        data,
        x="date",
        y="recovery_index",
        color="market",
        color_discrete_map=MARKET_COLOURS,
        labels={
            "date": "Month",
            "recovery_index": "Recovery index (same month in 2019 = 100)",
            "market": "Market",
        },
    )
    if show_reference:
        figure.add_hline(
            y=100,
            line_dash="dash",
            line_color="#374151",
            annotation_text="2019 level",
        )
    add_phase_shading(figure)
    polish_figure(figure)
    return use_horizontal_legend(figure)


def build_market_composition_chart(composition: pd.DataFrame) -> Figure:
    """Build the stacked comparison of source-market shares."""
    figure = px.bar(
        composition,
        x="year",
        y="share_pct",
        color="market",
        color_discrete_map=MARKET_COLOURS,
        barmode="stack",
        text_auto=".1f",
        labels={
            "year": "",
            "share_pct": "Share of visitor arrivals (%)",
            "market": "",
        },
    )
    figure.update_layout(
        yaxis_range=[0, 100],
        margin=dict(l=10, r=10, t=20, b=10),
    )
    return figure


def build_market_share_change_chart(
    market_changes: pd.DataFrame,
    baseline_year: int,
    comparison_year: int,
) -> Figure:
    """Build the horizontal chart of source-market share changes."""
    figure = px.bar(
        market_changes,
        x="share_change_pp",
        y="market",
        orientation="h",
        color="share_change_pp",
        color_continuous_scale=["#B91C1C", "#F8FAFC", PRIMARY_COLOUR],
        color_continuous_midpoint=0,
        labels={
            "share_change_pp": (
                f"Change in visitor share, {baseline_year}-{comparison_year} (pp)"
            ),
            "market": "",
        },
    )
    figure.add_vline(x=0, line_color="#334155")
    figure.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=20, b=10),
    )
    return figure


def build_hotel_metric_chart(
    data: pd.DataFrame,
    *,
    title: str,
    y_axis_label: str,
    colour: str,
) -> Figure:
    """Build one monthly hotel-performance line chart."""
    figure = px.line(
        data,
        x="date",
        y="value",
        labels={"date": "Month", "value": y_axis_label},
        title=title,
        color_discrete_sequence=[colour],
    )
    add_phase_shading(figure)
    return polish_figure(figure)


def build_recovery_comparison_chart(comparison: pd.DataFrame) -> Figure:
    """Build aligned recovery lines for arrivals and room revenue."""
    figure = px.line(
        comparison,
        x="date",
        y="value",
        color="series",
        labels={
            "date": "Month",
            "value": "Recovery index (same month in 2019 = 100)",
            "series": "",
        },
        color_discrete_sequence=["#2563EB", PRIMARY_COLOUR],
    )
    figure.add_hline(y=100, line_dash="dash", line_color="#374151")
    add_phase_shading(figure)
    polish_figure(figure)
    return use_horizontal_legend(figure)
