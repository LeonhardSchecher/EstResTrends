# dash_app.py
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import pandas as pd

# --------------------------------------------------
# Data 
# --------------------------------------------------
df = px.data.gapminder()  

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(include="object").columns.tolist()

def make_plot(data, x_col, y_col, color_col):
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
    # Load Zilla Slab font from Google Fonts
    "https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@300;400;500;700&display=swap"
]

app = Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Project Dashboard"  # tab title

# Small helpers
def dropdown_options(values):
    return [{"label": v, "value": v} for v in values]

numeric_options = dropdown_options(numeric_cols)
color_options = dropdown_options(["None"] + categorical_cols)

# Default dropdown values
x_default = numeric_cols[0]
y_default = numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0]
color_default = "None"

# --------------------------------------------------
# Reusable "plot window" block (layout only)
# --------------------------------------------------
def make_plot_window(window_title, prefix):
    """
    window_title: e.g. "Plot Window 1"
    prefix: e.g. "w1" (used to create unique component IDs)
    """
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
            # Controls on the left
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

            # Plot on the right
            html.Div(
                className="plot-area",
                style={
                    "flex": "1",
                },
                children=[
                    dcc.Graph(
                        id=f"{prefix}-graph",
                        style={
                            "height": "100%",
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
                # Top intro section
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

                # Three vertically stacked plot windows
                make_plot_window("Plot Window 1", "w1"),
                make_plot_window("Plot Window 2", "w2"),
                make_plot_window("Plot Window 3", "w3"),
            ],
        )
    ],
)


# --------------------------------------------------
# Callbacks: one per window
# --------------------------------------------------
@app.callback(
    Output("w1-graph", "figure"),
    Input("w1-x", "value"),
    Input("w1-y", "value"),
    Input("w1-color", "value"),
)
def update_w1_graph(x_col, y_col, color_col):
    return make_plot(df, x_col, y_col, color_col)


@app.callback(
    Output("w2-graph", "figure"),
    Input("w2-x", "value"),
    Input("w2-y", "value"),
    Input("w2-color", "value"),
)
def update_w2_graph(x_col, y_col, color_col):
    return make_plot(df, x_col, y_col, color_col)


@app.callback(
    Output("w3-graph", "figure"),
    Input("w3-x", "value"),
    Input("w3-y", "value"),
    Input("w3-color", "value"),
)
def update_w3_graph(x_col, y_col, color_col):
    return make_plot(df, x_col, y_col, color_col)


# --------------------------------------------------
# Entry point
# --------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True) 
    

