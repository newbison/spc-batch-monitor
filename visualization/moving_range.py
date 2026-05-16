import numpy as np
import plotly.graph_objects as go
from visualization._theme import default_layout, PLOTLY_COLORS

D4_MR = 3.267  # I-MR constant for n=2 subgroups


def build_moving_range_chart(df, parameter_name, lsl=None, usl=None):
    """Moving range chart: |X-bar_i - X-bar_i-1| with CL and UCL.

    Parameters lsl/usl are accepted for API consistency but not used.
    """
    rep_cols = sorted(
        [c for c in df.columns if c.startswith("rep")],
        key=lambda x: int(x[3:]),
    )
    reps = df[rep_cols].values.astype(float)
    xbar = np.nanmean(reps, axis=1)
    batch_ids = df["batch_id"].tolist()

    mr = np.abs(np.diff(xbar))
    mr_bar = float(np.mean(mr))
    ucl = D4_MR * mr_bar

    # X-axis: one label per consecutive pair, show second batch name
    mr_labels = batch_ids[1:]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=mr_labels, y=mr, mode="lines+markers",
        name="Moving Range",
        marker=dict(size=6, color=PLOTLY_COLORS["blue"]),
        line=dict(color=PLOTLY_COLORS["blue"], width=1.5),
    ))
    fig.add_hline(
        y=mr_bar, line_dash="dash", line_color=PLOTLY_COLORS["green"],
        annotation_text=f"mR̄ ({mr_bar:.3f})",
    )
    fig.add_hline(
        y=ucl, line_dash="dash", line_color=PLOTLY_COLORS["red"],
        annotation_text=f"UCL ({ucl:.3f})",
    )
    fig.update_layout(
        **default_layout(title=f"Moving Range &mdash; {parameter_name}", height=450),
        xaxis_title="Batch (consecutive pairs)",
        yaxis_title="|X̄ₖ - X̄ₖ₋₁|",
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#E2E8F0", zeroline=False)
    fig.update_yaxes(gridcolor="#E2E8F0", zeroline=False)
    return fig
