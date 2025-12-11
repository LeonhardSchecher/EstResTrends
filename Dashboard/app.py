# app.py
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

# ---------- Prepare keyword-level data (global keyword counts) ----------
# "Keywords" is a list of strings per record, e.g. ['biomass', 'graphene', 'catalysis']
df_keywords_global = (
    df_raw[["Keywords"]]
    .explode("Keywords")
    .rename(columns={"Keywords": "Keyword"})
    .dropna(subset=["Keyword"])
)

# ---------- Prepare institution-level data ----------
# "Institutions" is a list of dicts per record.
# Example:
# [
#   {
#     'BusinessRegNo': '74001073',
#     'Guid': 'edd8273f-2bf0-41f6-a4e8-167597dffdf5',
#     'Name': '...',
#     'NameEng': '...'
#   },
#   ...
# ]
df_inst_long = df_raw[
    ["Year", "FrascatiClassification", "Keywords", "Institutions", "Source"]
].copy()
df_inst_long = df_inst_long.explode("Institutions")

# Extract a clean institution name (prefer NameEng, fallback to Name)
def extract_inst_name(inst):
    if isinstance(inst, dict):
        if inst.get("NameEng"):
            return inst.get("NameEng")
        return inst.get("Name")
    return None


df_inst_long["InstitutionName"] = df_inst_long["Institutions"].apply(extract_inst_name)
df_inst_long = df_inst_long.dropna(subset=["InstitutionName"])

# List of all institutions (for dropdown 2 in mode 7)
institutions = sorted(df_inst_long["InstitutionName"].dropna().unique().tolist())

# ---------- Institution + keyword long format ----------
# One row per (InstitutionName, Year, Keyword)
df_inst_keywords_long = (
    df_inst_long[["InstitutionName", "Year", "Keywords"]]
    .explode("Keywords")
    .rename(columns={"Keywords": "Keyword"})
    .dropna(subset=["Keyword"])
)

# ---------- Columns for windows 2 & 3 playground ----------
numeric_cols = df_raw.select_dtypes(include="number").columns.tolist()
categorical_cols = [
    c
    for c in df_raw.select_dtypes(include="object").columns
    if c not in ["Institutions", "Keywords"]
]

# --------------------------------------------------
# Helper functions: bar charts for window 1
# --------------------------------------------------

def style_bar_fig(fig):
    """Common styling for bar charts."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Zilla Slab", color="black"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        # More room on the left for long labels
        margin=dict(l=220, r=40, t=60, b=40),
        yaxis=dict(automargin=True),
        xaxis=dict(automargin=True),
    )
    fig.update_yaxes(tickfont=dict(size=10))
    fig.update_xaxes(tickfont=dict(size=10))
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
    fig.update_traces(textposition="outside", textfont=dict(size=10))
    return style_bar_fig(fig)


def bar_top_10_frascati():
    counts = (
        df_raw["FrascatiClassification"]
        .dropna()
        .value_counts()
        .nlargest(10)
        .reset_index()
    )
    counts.columns = ["FrascatiClassification", "count"]
    counts = counts.sort_values("count")

    fig = px.bar(
        counts,
        x="count",
        y="FrascatiClassification",
        orientation="h",
        text="count",
        title="Top 10 most frequent Frascati classifications",
    )
    fig.update_traces(textposition="outside", textfont=dict(size=10))
    return style_bar_fig(fig)


def bar_top_10_institutions():
    counts = (
        df_inst_long["InstitutionName"]
        .value_counts()
        .nlargest(10)
        .reset_index()
    )
    counts.columns = ["InstitutionName", "count"]
    counts = counts.sort_values("count")

    fig = px.bar(
        counts,
        x="count",
        y="InstitutionName",
        orientation="h",
        text="count",
        title="Top 10 most frequent institutions",
    )
    fig.update_traces(textposition="outside", textfont=dict(size=10))
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
    fig.update_traces(textposition="outside", textfont=dict(size=10))
    return style_bar_fig(fig)


def bar_most_frequent_keyword_per_institution(top_n=10):
    """
    For each institution, find its most frequent keyword.
    Bars: institutions (y), x-axis: count of that keyword.
    Text on the bar: the keyword.
    """
    sub = df_inst_keywords_long.copy()
    if sub.empty:
        fig = px.bar(title="No data for institution keywords")
        return style_bar_fig(fig)

    counts = (
        sub.groupby(["InstitutionName", "Keyword"])
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
        text="Keyword",
        title="Most frequent keyword of each institution",
    )
    fig.update_traces(textposition="outside", textfont=dict(size=9))
    return style_bar_fig(fig)


def bar_most_frequent_frascati_per_institution(top_n=10):
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
    fig.update_traces(textposition="outside", textfont=dict(size=9))
    return style_bar_fig(fig)


def bar_top_keyword_per_year_for_institution(institution_name):
    """
    For a chosen institution:
    - x-axis: Year
    - y-axis: count of the top keyword that year
    - text on bar: keyword
    """
    sub = df_inst_keywords_long[
        df_inst_keywords_long["InstitutionName"] == institution_name
    ]
    if sub.empty:
        fig = px.bar(title=f"No data for institution: {institution_name}")
        return style_bar_fig(fig)

    counts = (
        sub.groupby(["Year", "Keyword"])
        .size()
        .reset_index(name="count")
    )

    idx = counts.groupby("Year")["count"].idxmax()
    top = counts.loc[idx].sort_values("Year")

    fig = px.bar(
        top,
        x="Year",
        y="count",
        text="Keyword",
        title=f"Top keyword of {institution_name} per year",
    )
    fig.update_traces(textposition="outside", textfont=dict(size=9))
    return style_bar_fig(fig)


# --------------------------------------------------
# Generic scatter for windows 2 & 3
# --------------------------------------------------

def make_scatter(data, x_col, y_col, color_col):
    color_arg = None if color_col == "None" else color_col
    fig = px.scatter(
        data,
        x=x_col,
        y=y_col,
        color=color_arg,
        template="plotly_white",
        height=400,
    )
    fig.update_layout(
        font=dict(family="Zilla Slab", color="black"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


# --------------------------------------------------
# Dash app setup
# --------------------------------------------------

external_stylesheets = [
    "https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@300;400;500;700&display=swap"
]

app = Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Project Dashboard"


def dropdown_options(values):
    return [{"label": v, "value": v} for v in values]


numeric_options = dropdown_options(numeric_cols)
color_options = dropdown_options(["None"] + categorical_cols)

# Options for the first dropdown in window 1
METRIC_OPTIONS = [
    {
        "label": "Top 10 most frequent keywords",
        "value": "top_keywords",
    },
    {
        "label": "Top 10 most frequent Frascati classifications",
        "value": "top_frascati",
    },
    {
        "label": "Top 10 most frequent institutions",
        "value": "top_institutions",
    },
    {
        "label": "Top 10 most frequent sources",
        "value": "top_sources",
    },
    {
        "label": "Most frequent keyword of each institution",
        "value": "inst_top_keyword",
    },
    {
        "label": "Most frequent Frascati classification of each institution",
        "value": "inst_top_frascati",
    },
    {
        "label": "Top keyword of an institution per year",
        "value": "inst_year_top_keyword",
    },
]


# --------------------------------------------------
# Layout blocks
# --------------------------------------------------

def make_first_plot_window():
    # Window 1: custom bar plot + 2 dropdowns
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
                style={
                    "width": "25%",
                    "minWidth": "260px",
                },
                children=[
                    html.H2(
                        "Plot Window 1 – Overview",
                        style={
                            "fontFamily": "Zilla Slab, serif",
                            "marginBottom": "12px",
                        },
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
                        options=METRIC_OPTIONS,
                        value="top_keywords",  # default: option 1
                        clearable=False,
                        style={"marginBottom": "16px"},
                    ),
                    html.Label("Institution"),
                    dcc.Dropdown(
                        id="w1-institution",
                        options=[{"label": "-", "value": "-"}],  # default: "-"
                        value="-",
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
                        style={"height": "100%"},
                        config={
                            "modeBarButtonsToRemove": ["select2d", "lasso2d"]
                        },
                    )
                ],
            ),
        ],
    )


def make_generic_plot_window(window_title, prefix):
    x_default = numeric_cols[0] if numeric_cols else None
    y_default = numeric_cols[1] if len(numeric_cols) > 1 else x_default
    color_default = "None"

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
                style={
                    "width": "25%",
                    "minWidth": "220px",
                },
                children=[
                    html.H2(
                        window_title,
                        style={
                            "fontFamily": "Zilla Slab, serif",
                            "marginBottom": "12px",
                        },
                    ),
                    html.H3(
                        "Controls",
                        style={
                            "fontFamily": "Zilla Slab, serif",
                            "fontSize": "18px",
                            "marginBottom": "8px",
                        },
                    ),
                    html.Label("X axis"),
                    dcc.Dropdown(
                        id=f"{prefix}-x",
                        options=numeric_options,
                        value=x_default,
                        clearable=False,
                        style={"marginBottom": "12px"},
                    ),
                    html.Label("Y axis"),
                    dcc.Dropdown(
                        id=f"{prefix}-y",
                        options=numeric_options,
                        value=y_default,
                        clearable=False,
                        style={"marginBottom": "12px"},
                    ),
                    html.Label("Color / group by"),
                    dcc.Dropdown(
                        id=f"{prefix}-color",
                        options=color_options,
                        value=color_default,
                        clearable=False,
                    ),
                ],
            ),
            html.Div(
                className="plot-area",
                style={"flex": "1"},
                children=[
                    dcc.Graph(
                        id=f"{prefix}-graph",
                        style={"height": "100%"},
                        config={
                            "modeBarButtonsToRemove": ["select2d", "lasso2d"]
                        },
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
                    "Project Title",
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
                    Briefly describe the goal of the project here.
                    Explain what the dataset represents, how it was collected,
                    and what kind of patterns the user can explore in the plots below.
                    """,
                    style={
                        "fontSize": "16px",
                        "lineHeight": "1.5",
                        "marginBottom": "24px",
                    },
                ),

                html.Hr(),

                # Window 1: custom bar plot with the 7 modes
                make_first_plot_window(),

                # Windows 2 & 3: generic playground scatter
                make_generic_plot_window("Plot Window 2", "w2"),
                make_generic_plot_window("Plot Window 3", "w3"),
            ],
        )
    ],
)


# --------------------------------------------------
# Callbacks
# --------------------------------------------------

# 1) Update institution dropdown based on metric selection
@app.callback(
    Output("w1-institution", "options"),
    Output("w1-institution", "value"),
    Input("w1-metric", "value"),
)
def update_w1_institution_dropdown(metric_value):
    # For all options except the last (inst_year_top_keyword), show only "-"
    if metric_value != "inst_year_top_keyword":
        return [{"label": "-", "value": "-"}], "-"

    # For the last option: list all institutions from the JSON
    if not institutions:
        return [{"label": "-", "value": "-"}], "-"

    inst_options = [{"label": inst, "value": inst} for inst in institutions]
    default_inst = institutions[0]
    return inst_options, default_inst


# 2) Update bar plot in window 1
@app.callback(
    Output("w1-graph", "figure"),
    Input("w1-metric", "value"),
    Input("w1-institution", "value"),
)
def update_w1_graph(metric_value, institution_value):
    if metric_value == "top_keywords":
        return bar_top_10_keywords()

    elif metric_value == "top_frascati":
        return bar_top_10_frascati()

    elif metric_value == "top_institutions":
        return bar_top_10_institutions()

    elif metric_value == "top_sources":
        return bar_top_10_sources()

    elif metric_value == "inst_top_keyword":
        return bar_most_frequent_keyword_per_institution(top_n=10)

    elif metric_value == "inst_top_frascati":
        return bar_most_frequent_frascati_per_institution(top_n=10)

    elif metric_value == "inst_year_top_keyword":
        if not institution_value or institution_value == "-":
            fig = px.bar(
                title="Select an institution to see its top keyword per year"
            )
            return style_bar_fig(fig)
        return bar_top_keyword_per_year_for_institution(institution_value)

    fig = px.bar(title="No metric selected")
    return style_bar_fig(fig)


# 3) Window 2 scatter
@app.callback(
    Output("w2-graph", "figure"),
    Input("w2-x", "value"),
    Input("w2-y", "value"),
    Input("w2-color", "value"),
)
def update_w2_graph(x_col, y_col, color_col):
    if x_col is None or y_col is None:
        return px.scatter(title="Select numeric columns for X and Y")
    return make_scatter(df_raw, x_col, y_col, color_col)


# 4) Window 3 scatter
@app.callback(
    Output("w3-graph", "figure"),
    Input("w3-x", "value"),
    Input("w3-y", "value"),
    Input("w3-color", "value"),
)
def update_w3_graph(x_col, y_col, color_col):
    if x_col is None or y_col is None:
        return px.scatter(title="Select numeric columns for X and Y")
    return make_scatter(df_raw, x_col, y_col, color_col)


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
