# app.py
import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# Page setup
# --------------------------------------------------
st.set_page_config(
    page_title="Project Dashboard",
    layout="wide",
)

# Global styling: Zilla Slab, white background, black text
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@300;400;500;700&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Zilla Slab', serif;
        background-color: white;
        color: black;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Zilla Slab', serif !important;
        color: black;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# Example data (replace with your own)
# --------------------------------------------------
# You can replace this with: df = pd.read_csv("your_data.csv")
df = px.data.gapminder()

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(include="object").columns.tolist()

# Helper to build a consistent-looking plot
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
    )
    return fig

# --------------------------------------------------
# Introduction (top section)
# --------------------------------------------------
st.title("Project Title")

st.subheader("Introduction")
st.markdown(
    """
    Briefly describe the goal of the project here.

    Explain what the dataset represents, how it was collected,
    and what kind of patterns the user can explore in the plots below.
    """
)

st.divider()

# --------------------------------------------------
# Reusable "plot window" component
# --------------------------------------------------
def plot_window(window_title: str, key_prefix: str):
    st.header(window_title)

    controls_col, plot_col = st.columns([1, 3])

    with controls_col:
        st.subheader("Controls")

        # Default values: first numeric column for x,
        # second numeric column for y (if it exists),
        # and "None" for color
        x_idx_default = 0
        y_idx_default = 1 if len(numeric_cols) > 1 else 0

        x_col = st.selectbox(
            "X axis",
            numeric_cols,
            index=x_idx_default,
            key=f"{key_prefix}_x",
        )

        y_col = st.selectbox(
            "Y axis",
            numeric_cols,
            index=y_idx_default,
            key=f"{key_prefix}_y",
        )

        color_col = st.selectbox(
            "Color / group by",
            ["None"] + categorical_cols,
            index=0,
            key=f"{key_prefix}_color",
        )

    with plot_col:
        fig = make_plot(df, x_col, y_col, color_col)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()


# --------------------------------------------------
# Three vertically stacked plot windows
# --------------------------------------------------
plot_window("Plot Window 1", key_prefix="w1")
plot_window("Plot Window 2", key_prefix="w2")
plot_window("Plot Window 3", key_prefix="w3")
