import numpy as np
import plotly.graph_objects as go
from visualization._theme import default_layout, PLOTLY_COLORS


def build_run_chart(df, parameter_name, lsl=None, usl=None):
    """Run chart: X-bar values with a horizontal median line.

    Parameters lsl/usl are accepted for API consistency but not used.
    """
    rep_cols = sorted(
        [c for c in df.columns if c.startswith("rep")],
        key=lambda x: int(x[3:]),
    )
    reps = df[rep_cols].values.astype(float)
    xbar = np.nanmean(reps, axis=1)
    batch_ids = df["batch_id"].tolist()
    median_val = float(np.median(xbar))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=batch_ids, y=xbar, mode="lines+markers",
        name="X̄",
        marker=dict(size=6, color=PLOTLY_COLORS["blue"]),
        line=dict(color=PLOTLY_COLORS["blue"], width=1.5),
    ))
    fig.add_hline(
        y=median_val, line_dash="dash", line_color=PLOTLY_COLORS["grey"],
        annotation_text=f"Median ({median_val:.3f})",
    )
    fig.update_layout(
        **default_layout(title=f"Run Chart &mdash; {parameter_name}", height=450),
        xaxis_title="Batch",
        yaxis_title="X̄",
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#E2E8F0", zeroline=False)
    fig.update_yaxes(gridcolor="#E2E8F0", zeroline=False)
    return fig
