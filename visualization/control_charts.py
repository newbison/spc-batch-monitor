import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_xbar_r_chart(
    limits: dict,
    violations: list[dict],
    parameter_name: str,
    batch_ids: list[str],
) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06)

    n = len(limits["xbar"])
    x_labels = batch_ids if len(batch_ids) == n else list(range(n))

    # --- X-bar trace ---
    fig.add_trace(
        go.Scatter(
            x=x_labels, y=limits["xbar"], mode="lines+markers",
            name="X̄", marker=dict(size=6, color="#2196F3"),
        ),
        row=1, col=1,
    )
    for line_val, color, label in [
        (limits["UCLx"], "#f44336", f'UCL ({limits["UCLx"]:.3f})'),
        (limits["LCLx"], "#f44336", f'LCL ({limits["LCLx"]:.3f})'),
        (limits["CLx"], "#4CAF50", f'CL ({limits["CLx"]:.3f})'),
    ]:
        fig.add_hline(y=line_val, line_dash="dash", line_color=color,
                      annotation_text=label, row=1, col=1)

    # Mark violations
    violation_indices = {v["batch_index"] for v in violations if v["rule"] == 1}
    viol_x = [x_labels[i] for i in violation_indices if i < n]
    viol_y = [limits["xbar"][i] for i in violation_indices if i < n]
    if viol_x:
        fig.add_trace(
            go.Scatter(x=viol_x, y=viol_y, mode="markers",
                       marker=dict(color="#f44336", size=10, symbol="x"),
                       name="Rule 1 violation"),
            row=1, col=1,
        )

    # --- R trace ---
    fig.add_trace(
        go.Scatter(
            x=x_labels, y=limits["r"], mode="lines+markers",
            name="R", marker=dict(size=6, color="#4CAF50"),
        ),
        row=2, col=1,
    )
    for line_val, color, label in [
        (limits["UCLr"], "#f44336", f'UCL ({limits["UCLr"]:.3f})'),
        (limits["CLr"], "#4CAF50", f'R̄ ({limits["CLr"]:.3f})'),
    ]:
        fig.add_hline(y=line_val, line_dash="dash", line_color=color,
                      annotation_text=label, row=2, col=1)

    fig.update_layout(
        title=f"X-bar & R Chart — {parameter_name}",
        height=650, showlegend=True,
    )
    fig.update_yaxes(title_text="X̄", row=1, col=1)
    fig.update_yaxes(title_text="R", row=2, col=1)
    fig.update_xaxes(title_text="Batch", row=2, col=1)

    return fig
