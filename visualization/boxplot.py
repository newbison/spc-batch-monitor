import numpy as np
import plotly.graph_objects as go
from visualization._theme import default_layout, PLOTLY_COLORS


def build_boxplot_chart(df, parameter_name, lsl=None, usl=None):
    """Build a boxplot of replicate measurements grouped by batch/lot.

    Parameters
    ----------
    df : pd.DataFrame
        Filtered to one formula + one parameter, sorted by date.
    parameter_name : str
        Display name for the y-axis.
    lsl : float or None
        Lower spec limit (dashed red line).
    usl : float or None
        Upper spec limit (dashed red line).

    Returns
    -------
    go.Figure
    """
    rep_cols = sorted(
        [c for c in df.columns if c.startswith("rep")],
        key=lambda x: int(x[3:]),
    )

    batch_ids = []
    values = []
    for _, row in df.iterrows():
        for col in rep_cols:
            val = float(row[col])
            if not np.isnan(val):
                batch_ids.append(str(row["batch_id"]))
                values.append(val)

    fig = go.Figure()

    fig.add_trace(go.Box(
        x=batch_ids,
        y=values,
        name=parameter_name,
        boxmean="sd",
        boxpoints="outliers",
        marker_color=PLOTLY_COLORS["blue"],
        line_color="#1565C0",
    ))

    if lsl is not None:
        fig.add_hline(
            y=lsl,
            line_dash="dash",
            line_color=PLOTLY_COLORS["red"],
            annotation_text=f"LSL ({lsl:.4g})",
            annotation_font_color=PLOTLY_COLORS["red"],
        )

    if usl is not None:
        fig.add_hline(
            y=usl,
            line_dash="dash",
            line_color=PLOTLY_COLORS["red"],
            annotation_text=f"USL ({usl:.4g})",
            annotation_font_color=PLOTLY_COLORS["red"],
        )

    fig.update_layout(
        **default_layout(title=f"Batch Variation — {parameter_name}", height=450),
        xaxis_title="Batch / Lot",
        yaxis_title=parameter_name,
        hovermode="y unified",
    )
    fig.update_xaxes(gridcolor="#E2E8F0", zeroline=False)
    fig.update_yaxes(gridcolor="#E2E8F0", zeroline=False)

    return fig
