from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import pandas as pd

# --------------------------------------------------
# Data loading and preparation
# --------------------------------------------------

# TODO: change this to the path of your JSON file
DATA_PATH = "Data/data.json"

# Read JSON into a DataFrame
df_raw = pd.read_json(DATA_PATH)

# Ensure Year is numeric
df_raw["Year"] = pd.to_numeric(df_raw["Year"], errors="coerce")

# Global min/max years (for x-axis range on line charts)
_year_nonnull = df_raw["Year"].dropna()
if not _year_nonnull.empty:
    YEAR_MIN = int(_year_nonnull.min())
    YEAR_MAX = int(_year_nonnull.max())
else:
    YEAR_MIN = YEAR_MAX = None

# ---------- Keyword-level data ----------
# Keywords is a list of strings per record
df_keywords_global = (
    df_raw[["Keywords"]]
    .explode("Keywords")
    .rename(columns={"Keywords": "Keyword"})
    .dropna(subset=["Keyword"])
)

# Keywords with Year (for line chart)
df_keywords_year = (
    df_raw[["Year", "Keywords"]]
    .explode("Keywords")
    .rename(columns={"Keywords": "Keyword"})
    .dropna(subset=["Keyword", "Year"])
)
df_keywords_year["YearInt"] = df_keywords_year["Year"].astype(int)

# ---------- Institution-level data ----------
df_inst_long = df_raw[
    ["Year", "FrascatiClassification", "Keywords", "Institutions", "Source"]
].copy()
df_inst_long = df_inst_long.explode("Institutions")


def extract_inst_name(inst):
    if isinstance(inst, dict):
        if inst.get("NameEng"):
            return inst.get("NameEng")
        return inst.get("Name")
    return None


df_inst_long["InstitutionName"] = df_inst_long["Institutions"].apply(extract_inst_name)
df_inst_long = df_inst_long.dropna(subset=["InstitutionName"])

# Frascati with Year (for line chart)
df_fras_year = df_raw[["Year", "FrascatiClassification"]].dropna()
df_fras_year = df_fras_year[df_fras_year["Year"].notna()]
df_fras_year["YearInt"] = df_fras_year["Year"].astype(int)

# --------------------------------------------------
# Helper functions: bar charts (Window 1)
# --------------------------------------------------

def style_bar_fig(fig):
    """Common styling for bar charts with plenty of space."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Zilla Slab", color="black", size=14),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=260, r=40, t=60, b=60),  # room for long labels
        height=600,  # tall figure
        yaxis=dict(automargin=True),
        xaxis=dict(automargin=True),
    )
    fig.update_yaxes(tickfont=dict(size=12))
    fig.update_xaxes(tickfont=dict(size=12))
    return fig


def bar_top_10_keywords():
    counts = (
        df_keywords_global["Keyword"]
        .value_counts()
        .nlargest(10)
        .reset_index()
    )
    counts.columns = ["Keyword", "count"]
    counts = counts.sort_values("count")

    fig = px.bar(
        counts,
        x="count",
        y="Keyword",
        orientation="h",
        text="count",
        title="Top 10 most frequent keywords",
    )
    fig.update_traces(textposition="outside", textfont=dict(size=14))
    return style_bar_fig(fig)


def bar_top_10_sources():
    counts = (
        df_raw["Source"]
        .dropna()
        .value_counts()
        .nlargest(10)
        .reset_index()
    )
    counts.columns = ["Source", "count"]
    counts = counts.sort_values("count")

    fig = px.bar(
        counts,
        x="count",
        y="Source",
        orientation="h",
        text="count",
        title="Top 10 most frequent sources",
    )
    fig.update_traces(textposition="outside", textfont=dict(size=14))
    return style_bar_fig(fig)


def bar_most_frequent_frascati_per_institution(top_n=6):
    """
    For each institution, find its most frequent Frascati classification.
    Bars: institutions (y), x-axis: count of that classification.
    Text on the bar: the classification label.
    """
    sub = df_inst_long[["InstitutionName", "FrascatiClassification"]].dropna()
    if sub.empty:
        fig = px.bar(title="No data for institution Frascati classifications")
        return style_bar_fig(fig)

    counts = (
        sub.groupby(["InstitutionName", "FrascatiClassification"])
        .size()
        .reset_index(name="count")
    )

    idx = counts.groupby("InstitutionName")["count"].idxmax()
    top = counts.loc[idx].sort_values("count", ascending=False).head(top_n)
    top = top.sort_values("count")

    fig = px.bar(
        top,
        x="count",
        y="InstitutionName",
        orientation="h",
        text="FrascatiClassification",
        title="Most frequent Frascati classification of each institution",
    )
    fig.update_traces(textposition="outside", textfont=dict(size=14))
    return style_bar_fig(fig)


# --------------------------------------------------
# Line charts (Window 2) – keyword (default) & Frascati
# --------------------------------------------------

def _apply_year_axis(fig):
    """Apply global year range and integer ticks to a line chart."""
    if YEAR_MIN is not None and YEAR_MAX is not None:
        fig.update_xaxes(
            range=[YEAR_MIN - 0.5, YEAR_MAX + 0.5],
            dtick=1,
            tickmode="linear",
            title_text="Year",
        )
    else:
        fig.update_xaxes(
            dtick=1,
            tickmode="linear",
            title_text="Year",
        )
    fig.update_yaxes(title_text="count")
    return fig


def keywords_over_years_top6():
    """Top 6 keywords over years (line chart)."""
    if df_keywords_year.empty:
        return px.line(title="No keyword data")

    top_kw = (
        df_keywords_year["Keyword"]
        .value_counts()
        .nlargest(6)
        .index
    )
    df_top = df_keywords_year[df_keywords_year["Keyword"].isin(top_kw)]

    year_counts = (
        df_top.groupby(["YearInt", "Keyword"])
        .size()
        .reset_index(name="count")
    )

    fig = px.line(
        year_counts,
        x="YearInt",
        y="count",
        color="Keyword",
        markers=True,
        title="Top 6 keywords over years",
    )

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Zilla Slab", color="black"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=40, r=20, t=60, b=60),
        legend_title_text="Keyword",
    )
    return _apply_year_axis(fig)


def frascati_over_years_top6():
    """Top 6 Frascati classifications over years (line chart)."""
    if df_fras_year.empty:
        return px.line(title="No Frascati data")

    top_codes = (
        df_fras_year["FrascatiClassification"]
        .value_counts()
        .nlargest(6)
        .index
    )
    df_top = df_fras_year[df_fras_year["FrascatiClassification"].isin(top_codes)]

    year_counts = (
        df_top.groupby(["YearInt", "FrascatiClassification"])
        .size()
        .reset_index(name="count")
    )

    fig = px.line(
        year_counts,
        x="YearInt",
        y="count",
        color="FrascatiClassification",
        markers=True,
        title="Top 6 Frascati classifications over years",
    )

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Zilla Slab", color="black"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=40, r=20, t=60, b=60),
        legend_title_text="Frascati",
    )
    return _apply_year_axis(fig)


# --------------------------------------------------
# Pie charts (Window 3)
# --------------------------------------------------

def make_pie_from_series(series, title, top_n=10):
    s = series.dropna()
    if s.empty:
        fig = px.pie(title=f"No data for {title}")
        fig.update_layout(
            template="plotly_white",
            font=dict(family="Zilla Slab", color="black"),
            paper_bgcolor="white",
            plot_bgcolor="white",
        )
        return fig

    counts = s.value_counts()
    if len(counts) > top_n:
        top = counts.iloc[:top_n]
        other = counts.iloc[top_n:].sum()
        counts = pd.concat([top, pd.Series({"Other": other})])

    df_counts = counts.reset_index()
    df_counts.columns = ["label", "count"]

    fig = px.pie(
        df_counts,
        names="label",
        values="count",
        title=title,
    )

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Zilla Slab", color="black"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend_title_text="",
    )
    return fig


def distribution_pie(metric_value: str):
    """Return the appropriate pie chart for window 3."""
    # Default & 'frascati' → Frascati frequency
    if metric_value in (None, "frascati"):
        return make_pie_from_series(
            df_raw["FrascatiClassification"], "Frascati frequency"
        )
    # Institutions frequency
    elif metric_value == "institution":
        return make_pie_from_series(
            df_inst_long["InstitutionName"], "Institutions frequency"
        )
    # Fallback to Frascati
    return make_pie_from_series(
        df_raw["FrascatiClassification"], "Frascati frequency"
    )


# --------------------------------------------------
# Dash app setup
# --------------------------------------------------

external_stylesheets = [
    "https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@300;400;500;700&display=swap"
]

app = Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Project Dashboard"

# Options for Window 1 (bar plots)
METRIC_OPTIONS_W1 = [
    {"label": "Top 10 most frequent keywords", "value": "top_keywords"},
    {"label": "Top 10 most frequent sources", "value": "top_sources"},
    {
        "label": "Most frequent Frascati classification of each institution",
        "value": "inst_top_frascati",
    },
]

# Options for Window 2 (line plots)
METRIC_OPTIONS_W2 = [
    {"label": "Top 6 keywords over years", "value": "keyword"},
    {"label": "Top 6 Frascati classifications over years", "value": "frascati"},
]

# Options for Window 3 (pie charts) – ONLY frascati & institutions
METRIC_OPTIONS_W3 = [
    {"label": "Frascati frequency", "value": "frascati"},
    {"label": "Institutions frequency", "value": "institution"},
]


# --------------------------------------------------
# Layout blocks
# --------------------------------------------------

def make_first_plot_window():
    return html.Div(
        className="plot-window",
        style={
            "display": "flex",
            "flexDirection": "row",
            "alignItems": "stretch",
            "gap": "24px",
            "marginBottom": "40px",
        },
        children=[
            html.Div(
                className="controls",
                style={"width": "25%", "minWidth": "260px"},
                children=[
                    html.H2(
                        "Plot Window 1 – Overview",
                        style={"fontFamily": "Zilla Slab, serif", "marginBottom": "12px"},
                    ),
                    html.H3(
                        "Controls",
                        style={
                            "fontFamily": "Zilla Slab, serif",
                            "fontSize": "18px",
                            "marginBottom": "8px",
                        },
                    ),
                    html.Label("Select view"),
                    dcc.Dropdown(
                        id="w1-metric",
                        options=METRIC_OPTIONS_W1,
                        value="top_keywords",  # default
                        clearable=False,
                    ),
                ],
            ),
            html.Div(
                className="plot-area",
                style={"flex": "1"},
                children=[
                    dcc.Graph(
                        id="w1-graph",
                        style={"height": "600px"},  # fixed tall height
                        config={"modeBarButtonsToRemove": ["select2d", "lasso2d"]},
                    )
                ],
            ),
        ],
    )


def make_second_plot_window():
    return html.Div(
        className="plot-window",
        style={
            "display": "flex",
            "flexDirection": "row",
            "alignItems": "stretch",
            "gap": "24px",
            "marginBottom": "40px",
        },
        children=[
            html.Div(
                className="controls",
                style={"width": "25%", "minWidth": "260px"},
                children=[
                    html.H2(
                        "Plot Window 2 – Trends over years",
                        style={"fontFamily": "Zilla Slab, serif", "marginBottom": "12px"},
                    ),
                    html.H3(
                        "Controls",
                        style={
                            "fontFamily": "Zilla Slab, serif",
                            "fontSize": "18px",
                            "marginBottom": "8px",
                        },
                    ),
                    html.Label("Select view"),
                    dcc.Dropdown(
                        id="w2-metric",
                        options=METRIC_OPTIONS_W2,
                        value="keyword",  # default: keyword line
                        clearable=False,
                    ),
                ],
            ),
            html.Div(
                className="plot-area",
                style={"flex": "1"},
                children=[
                    dcc.Graph(
                        id="w2-graph",
                        style={"height": "500px"},
                        config={"modeBarButtonsToRemove": ["select2d", "lasso2d"]},
                    )
                ],
            ),
        ],
    )


def make_third_plot_window():
    return html.Div(
        className="plot-window",
        style={
            "display": "flex",
            "flexDirection": "row",
            "alignItems": "stretch",
            "gap": "24px",
            "marginBottom": "40px",
        },
        children=[
            html.Div(
                className="controls",
                style={"width": "25%", "minWidth": "260px"},
                children=[
                    html.H2(
                        "Plot Window 3 – Distribution",
                        style={"fontFamily": "Zilla Slab, serif", "marginBottom": "12px"},
                    ),
                    html.H3(
                        "Controls",
                        style={
                            "fontFamily": "Zilla Slab, serif",
                            "fontSize": "18px",
                            "marginBottom": "8px",
                        },
                    ),
                    html.Label("Select view"),
                    dcc.Dropdown(
                        id="w3-metric",
                        options=METRIC_OPTIONS_W3,
                        value="frascati",  # default: Frascati pie
                        clearable=False,
                    ),
                ],
            ),
            html.Div(
                className="plot-area",
                style={"flex": "1"},
                children=[
                    dcc.Graph(
                        id="w3-graph",
                        style={"height": "500px"},
                    )
                ],
            ),
        ],
    )


# --------------------------------------------------
# App layout
# --------------------------------------------------

app.layout = html.Div(
    style={
        "fontFamily": "Zilla Slab, serif",
        "backgroundColor": "white",
        "color": "black",
        "minHeight": "100vh",
    },
    children=[
        html.Div(
            style={
                "maxWidth": "1200px",
                "margin": "0 auto",
                "padding": "24px 16px 40px 16px",
            },
            children=[
                html.H1(
                    "Estonian Resarch Trends",
                    style={
                        "fontFamily": "Zilla Slab, serif",
                        "fontWeight": "700",
                        "marginBottom": "8px",
                    },
                ),
                html.H2(
                    "Introduction",
                    style={
                        "fontFamily": "Zilla Slab, serif",
                        "fontWeight": "400",
                        "fontSize": "22px",
                        "marginBottom": "8px",
                    },
                ),
                html.P(
                    """
                    The plots below demonstrate different aspects of the data we extracted. 
                    """,
                    style={
                        "fontSize": "16px",
                        "lineHeight": "1.5",
                        "marginBottom": "24px",
                    },
                ),
                html.Hr(),
                make_first_plot_window(),
                make_second_plot_window(),
                make_third_plot_window(),
            ],
        )
    ],
)


# --------------------------------------------------
# Callbacks
# --------------------------------------------------

# Window 1 – bar plots
@app.callback(
    Output("w1-graph", "figure"),
    Input("w1-metric", "value"),
)
def update_w1_graph(metric_value):
    if metric_value == "top_keywords":
        return bar_top_10_keywords()
    elif metric_value == "top_sources":
        return bar_top_10_sources()
    elif metric_value == "inst_top_frascati":
        return bar_most_frequent_frascati_per_institution(top_n=6)

    fig = px.bar(title="No metric selected")
    return style_bar_fig(fig)


# Window 2 – line plots
@app.callback(
    Output("w2-graph", "figure"),
    Input("w2-metric", "value"),
)
def update_w2_graph(metric_value):
    if metric_value == "keyword":
        return keywords_over_years_top6()
    elif metric_value == "frascati":
        return frascati_over_years_top6()
    return keywords_over_years_top6()


# Window 3 – pie charts
@app.callback(
    Output("w3-graph", "figure"),
    Input("w3-metric", "value"),
)
def update_w3_graph(metric_value):
    return distribution_pie(metric_value)


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
