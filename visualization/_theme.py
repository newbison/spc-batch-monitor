"""Shared Plotly theme defaults for consistent chart styling."""

PLOTLY_FONT = {"family": "Calibri, Arial, sans-serif", "size": 13}
PLOTLY_COLORS = {
    "primary": "#0D7377",
    "blue": "#2196F3",
    "red": "#E53935",
    "green": "#43A047",
    "grey": "#94A3B8",
}


def default_layout(title="", height=450):
    """Return a layout dict with consistent styling defaults.

    Caller merges or updates this, then passes to fig.update_layout().
    """
    return dict(
        title=dict(
            text=title,
            font=dict(size=16, color="#1E293B"),
        ),
        height=height,
        margin=dict(l=50, r=20, t=50, b=40),
        font=PLOTLY_FONT,
        plot_bgcolor="#F8FAFC",
        paper_bgcolor="#FFFFFF",
    )
