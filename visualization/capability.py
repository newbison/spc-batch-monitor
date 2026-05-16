import plotly.graph_objects as go
import numpy as np
import math
from visualization._theme import default_layout, PLOTLY_COLORS


def build_capability_chart(
    xbar: np.ndarray,
    lsl: float,
    usl: float,
    target: float | None,
    parameter_name: str,
) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=xbar, nbinsx=max(10, len(xbar) // 3),
        name="X̄ values",
        marker_color=PLOTLY_COLORS["blue"],
        opacity=0.75,
    ))

    # Only draw lines for non-NaN spec limits
    lines = []
    if not math.isnan(lsl):
        lines.append((lsl, PLOTLY_COLORS["red"], "dash", f"LSL ({lsl:.4g})"))
    if not math.isnan(usl):
        lines.append((usl, PLOTLY_COLORS["red"], "dash", f"USL ({usl:.4g})"))
    if target is not None:
        lines.append((target, PLOTLY_COLORS["green"], "dot", f"Target ({target:.4g})"))
    for x_val, color, dash, label in lines:
        fig.add_vline(x=x_val, line_dash=dash, line_color=color, annotation_text=label)

    fig.update_layout(
        **default_layout(title=f"Process Capability — {parameter_name}", height=400),
        xaxis_title="X̄ value",
        yaxis_title="Frequency",
        bargap=0.05,
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#E2E8F0", zeroline=False)
    fig.update_yaxes(gridcolor="#E2E8F0", zeroline=False)

    return fig
