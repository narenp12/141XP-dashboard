import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px

# Load precomputed data and dictionary
earn_data = pd.read_csv("dash_data.csv")
data_dict = pd.read_excel("datadict_institution.xlsx")

# Build label dictionary from data dictionary
label_dict = {}
labeled_vars = data_dict[
    data_dict["developer-friendly name"].isin(earn_data.columns) &
    data_dict["LABEL"].notna() &
    data_dict["VALUE"].notna()
]
for var in labeled_vars["developer-friendly name"].unique():
    subset = labeled_vars[labeled_vars["developer-friendly name"] == var]
    label_dict[var] = dict(zip(subset["VALUE"].astype(str), subset["LABEL"]))

# Prepare list of usable variables
exclude_cols = ['id', 'name', 'metric']
candidate_cols = [col for col in earn_data.columns if col not in exclude_cols]
valid_cols = [col for col in candidate_cols if earn_data[col].nunique(dropna=True) > 1]

# Identify categorical vs numeric
categorical_vars, numeric_vars = [], []
for col in valid_cols:
    if col in label_dict or earn_data[col].dtype == 'object':
        categorical_vars.append(col)
    elif pd.api.types.is_numeric_dtype(earn_data[col]):
        numeric_vars.append(col)

# Bin numeric vars based on uniqueness (up to 6 bins)
for col in numeric_vars:
    try:
        unique_vals = earn_data[col].nunique()
        num_bins = min(max(4, unique_vals.bit_length()), 6)
        if unique_vals > 4:
            earn_data[col + "_binned"] = pd.cut(earn_data[col], bins=num_bins, duplicates='drop')
            categorical_vars.append(col + "_binned")
    except Exception:
        pass

# Remove carnegie categories
categorical_vars = [col for col in categorical_vars if not col.startswith("carnegie_")]

# User-facing labels for dropdown
pretty_names = {
    'state': 'State',
    'ownership': 'Ownership Type',
    'degrees_awarded.highest': 'Highest Degree Awarded',
    'admission_rate.overall_binned': 'Admission Rate',
    'demographics.race_ethnicity.white_binned': 'White Student Share',
    'demographics.race_ethnicity.black_binned': 'Black Student Share',
    'demographics.race_ethnicity.hispanic_binned': 'Hispanic Student Share',
    'demographics.race_ethnicity.asian_binned': 'Asian Student Share',
    'completion_rate_4yr_150nt_binned': 'Completion Rate',
    'retention_rate.four_year.full_time_binned': 'Retention Rate',
    'usnews.median_rank_binned': 'US News Rank'
}

dropdown_options = [
    {"label": pretty_names.get(col, col.replace("_", " ").title()), "value": col}
    for col in categorical_vars
]

# Dash app
app = dash.Dash(__name__)
server = app.server

app.title = "University Outcomes Dashboard"

app.layout = html.Div([
    html.H1("University Outcomes Dashboard", style={'textAlign': 'center'}),
    html.P("Explore how institutional features relate to income outcomes.",
           style={'textAlign': 'center', 'marginBottom': '30px'}),

    html.Div([
        html.Label("Group by:"),
        dcc.Dropdown(id="group-var", options=dropdown_options, value=categorical_vars[0])
    ], style={"width": "50%", "margin": "auto"}),

    html.Br(),

    html.Div([
        html.Label("Filter by US News Rank:"),
        dcc.RangeSlider(
            id="rank-range",
            min=int(earn_data['usnews.median_rank'].min()),
            max=int(earn_data['usnews.median_rank'].max()),
            step=1,
            value=[1, 50],
            marks={i: str(i) for i in range(0, int(earn_data['usnews.median_rank'].max()) + 1, 25)},
            tooltip={"placement": "bottom", "always_visible": False}
        )
    ], style={"width": "80%", "margin": "auto"}),

    html.Br(),

    dcc.Graph(id="bar-plot", config={'displayModeBar': False})
])

@app.callback(
    Output("bar-plot", "figure"),
    Input("group-var", "value"),
    Input("rank-range", "value")
)
def update_graph(group_var, rank_range):
    df = earn_data.copy()
    df = df[df["usnews.median_rank"].between(rank_range[0], rank_range[1])]
    df[group_var] = df[group_var].astype(str)

    base_var = group_var.replace("_binned", "")

    if group_var == "ownership":
        df["group"] = df[group_var].apply(lambda x: "Public" if x == "1" else "Private")
    elif base_var in label_dict and not group_var.endswith("_binned"):
        df["group"] = df[group_var].map(label_dict[base_var]).fillna("Unknown")
    else:
        df["group"] = df[group_var]

    agg = df.groupby("group", as_index=False)["metric"].mean().sort_values("metric", ascending=False)

    fig = px.bar(
        agg,
        x="group",
        y="metric",
        labels={"group": pretty_names.get(group_var, group_var.title()), "metric": "Income Score"},
        title=f"Income Score by {pretty_names.get(group_var, group_var)} (Rank {rank_range[0]}–{rank_range[1]})",
        text_auto=True
    )
    fig.update_layout(xaxis_tickangle=-45)
    return fig

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000, debug=True)