import numpy as np
import plotly.graph_objects as go
from visualization._theme import default_layout, PLOTLY_COLORS
from spc_engine.capability import compute_capability


def build_rolling_ppk_chart(df, parameter_name, lsl=None, usl=None, window=10):
    """Rolling Ppk chart: sliding-window Ppk with color-coded spec zones.

    Ppk values are computed on a rolling window of batch means.
    """
    rep_cols = sorted(
        [c for c in df.columns if c.startswith("rep")],
        key=lambda x: int(x[3:]),
    )
    reps = df[rep_cols].values.astype(float)
    xbar = np.nanmean(reps, axis=1)
    batch_ids = df["batch_id"].tolist()
    n_batches = len(xbar)

    # Determine spec limits
    has_lsl = lsl is not None
    has_usl = usl is not None
    if not (has_lsl or has_usl):
        lsl_val = float("nan")
        usl_val = float("nan")
    else:
        lsl_val = lsl if has_lsl else float("nan")
        usl_val = usl if has_usl else float("nan")

    ppk_values = []
    ppk_labels = []
    for i in range(n_batches):
        if i < window - 1:
            ppk_values.append(None)
            ppk_labels.append(batch_ids[i])
        else:
            window_xbar = xbar[i - window + 1 : i + 1]
            cap = compute_capability(window_xbar, lsl_val, usl_val)
            ppk = cap["Ppk"]
            ppk_values.append(ppk if not np.isnan(ppk) else None)
            ppk_labels.append(batch_ids[i])

    fig = go.Figure()

    # Color zones
    fig.add_hrect(y0=0, y1=1.0, fillcolor=PLOTLY_COLORS["red"],
                  opacity=0.08, line_width=0)
    fig.add_hrect(y0=1.0, y1=1.33, fillcolor=PLOTLY_COLORS["green"],
                  opacity=0.06, line_width=0)
    fig.add_hline(y=1.0, line_dash="dot", line_color=PLOTLY_COLORS["red"],
                  annotation_text="Ppk = 1.0")
    fig.add_hline(y=1.33, line_dash="dot", line_color=PLOTLY_COLORS["green"],
                  annotation_text="Ppk = 1.33")

    fig.add_trace(go.Scatter(
        x=ppk_labels, y=ppk_values, mode="lines+markers",
        name="Rolling Ppk",
        connectgaps=False,
        marker=dict(size=6, color=PLOTLY_COLORS["blue"]),
        line=dict(color=PLOTLY_COLORS["blue"], width=1.5),
    ))

    # Compute y-axis max safely
    valid_ppk = [v for v in ppk_values if v is not None]
    y_max = max(2.0, max(valid_ppk) * 1.1) if valid_ppk else 2.0

    fig.update_layout(
        **default_layout(
            title=f"Rolling Ppk (window={window}) &mdash; {parameter_name}",
            height=450,
        ),
        xaxis_title="Batch",
        yaxis_title="Ppk",
        hovermode="x unified",
        yaxis=dict(range=[0, y_max]),
    )
    fig.update_xaxes(gridcolor="#E2E8F0", zeroline=False)
    fig.update_yaxes(gridcolor="#E2E8F0", zeroline=False)
    return fig
