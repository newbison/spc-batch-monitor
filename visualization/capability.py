import plotly.graph_objects as go
import numpy as np
import math


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
        name="X̄ values", marker_color="#2196F3", opacity=0.75,
    ))

    # Only draw lines for non-NaN spec limits
    lines = []
    if not math.isnan(lsl):
        lines.append((lsl, "#f44336", "dash", f"LSL ({lsl:.4g})"))
    if not math.isnan(usl):
        lines.append((usl, "#f44336", "dash", f"USL ({usl:.4g})"))
    if target is not None:
        lines.append((target, "#4CAF50", "dot", f"Target ({target:.4g})"))
    for x_val, color, dash, label in lines:
        fig.add_vline(x=x_val, line_dash=dash, line_color=color, annotation_text=label)

    fig.update_layout(
        title=f"Process Capability — {parameter_name}",
        xaxis_title="X̄ value",
        yaxis_title="Frequency",
        bargap=0.05,
    )
    return fig
