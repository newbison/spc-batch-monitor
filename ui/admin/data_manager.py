"""Admin data management - view, edit, delete, export, import batches."""
import streamlit as st
import pandas as pd
import math
from datetime import datetime, date

from data_access.base import DataRepository
from config import DATA_DIR

UPLOADS_DIR = DATA_DIR / "uploads"


def _format_reps(row, n=10):
    """Format rep values into a compact string."""
    vals = []
    for i in range(1, n + 1):
        col = f"rep{i}"
        if col in row and not (isinstance(row[col], float) and math.isnan(row[col])):
            vals.append(str(row[col]))
    return ", ".join(vals) if vals else "-"


def render_data_manager(repo: DataRepository):
    st.markdown(
        "<h1 style='margin-top: 0;'>\U0001f5c4 Data Management</h1>",
        unsafe_allow_html=True,
    )

    df_all = repo.load_all()
    if df_all.empty:
        st.warning("No data available.")
        return

    # --- Filter Bar ---
    st.markdown("### Filters")
    f1, f2, f3, f4 = st.columns(4)
    min_date = pd.to_datetime(df_all["date"]).min().date()
    max_date = pd.to_datetime(df_all["date"]).max().date()
    date_from = f1.date_input("Date from", min_date, key="dm_date_from")
    date_to = f2.date_input("Date to", max_date, key="dm_date_to")

    formulas = sorted(df_all["formula"].unique().tolist())
    selected_formula = f3.selectbox("Formula", ["All"] + formulas, key="dm_formula")

    params = sorted(df_all["parameter"].unique().tolist())
    selected_param = f4.selectbox("Parameter", ["All"] + params, key="dm_param")

    search = st.text_input("Search batch_id", placeholder="e.g. BATCH-001")

    # --- Apply filters ---
    df_filtered = df_all[
        (pd.to_datetime(df_all["date"]).dt.date >= date_from)
        & (pd.to_datetime(df_all["date"]).dt.date <= date_to)
    ]
    if selected_formula != "All":
        df_filtered = df_filtered[df_filtered["formula"] == selected_formula]
    if selected_param != "All":
        df_filtered = df_filtered[df_filtered["parameter"] == selected_param]
    if search:
        df_filtered = df_filtered[df_filtered["batch_id"].str.contains(search, case=False)]

    st.caption(f"Showing {len(df_filtered)} of {len(df_all)} rows")

    # --- Data Table ---
    st.divider()

    rep_cols = sorted(
        [c for c in df_filtered.columns if c.startswith("rep") and c[3:].isdigit()],
        key=lambda x: int(x[3:]),
    )
    display_cols = ["date", "batch_id", "formula", "parameter"] + rep_cols + ["lower_spec", "upper_spec"]
    display_df = df_filtered[display_cols].sort_values(["date", "batch_id", "parameter"])

    selection = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        selection_mode="multi-row",
        on_select="rerun",
        key="dm_table",
    )

    # --- Actions ---
    st.divider()
    st.markdown("### Actions")

    a1, a2, a3, a4 = st.columns(4)

    with a1:
        # Export
        csv_data = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "\U0001f4e5 Export Filtered",
            csv_data,
            f"spc_export_{date.today().isoformat()}.csv",
            "text/csv",
            key="dm_export",
        )

    with a2:
        # Import
        uploaded = st.file_uploader("\U0001f4e4 Import CSV", type=["csv"], key="dm_import")
        if uploaded is not None:
            new_df = pd.read_csv(uploaded)
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            archive_path = UPLOADS_DIR / f"{ts}-{uploaded.name}"
            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            new_df.to_csv(archive_path, index=False)

            result = repo.upload_csv(new_df)
            if result["errors"]:
                st.error(f"Validation failed - {len(result['errors'])} error(s)")
            else:
                st.success(f"Imported {result['inserted']}, skipped {result['skipped']}")
                st.rerun()

    # Edit / Delete selected rows
    if selection is not None and len(selection.selection.rows) > 0:
        selected_indices = selection.selection.rows
        selected_rows = display_df.iloc[selected_indices]

        with a3:
            if st.button("\U0001f5d1 Delete Selected", type="secondary", key="dm_delete"):
                deleted_count = 0
                for _, row in selected_rows.iterrows():
                    repo.delete_batch(
                        row["batch_id"], row["formula"], row["parameter"]
                    )
                    deleted_count += 1
                st.success(f"Deleted {deleted_count} row(s)")
                st.rerun()

        # Edit form (single row)
        st.divider()
        st.markdown("### Edit Selected Row")

        if len(selected_rows) == 1:
            row = selected_rows.iloc[0]
            _render_edit_form(repo, row)
        else:
            st.info("Select exactly one row to edit.")
    else:
        st.info("Select rows above to edit or delete.")


def _render_edit_form(repo: DataRepository, row):
    """Inline form to edit a single batch/parameter row."""
    st.write(f"**Editing:** {row['batch_id']} - {row['formula']} / {row['parameter']}  ({row['date']})")

    # Detect existing reps
    rep_vals = []
    for i in range(1, 51):
        col = f"rep{i}"
        if col in row.index and not (isinstance(row[col], float) and math.isnan(row[col])):
            rep_vals.append(float(row[col]))

    n = len(rep_vals)
    st.caption(f"{n} replicates detected")

    ec1, ec2 = st.columns(2)
    with ec1:
        lsl_val = float(row["lower_spec"]) if not (
            isinstance(row["lower_spec"], float) and math.isnan(row["lower_spec"])
        ) else 0.0
        lsl = st.number_input("LSL", value=lsl_val, key="dm_edit_lsl")
    with ec2:
        usl_val = float(row["upper_spec"]) if not (
            isinstance(row["upper_spec"], float) and math.isnan(row["upper_spec"])
        ) else 0.0
        usl = st.number_input("USL", value=usl_val, key="dm_edit_usl")

    new_reps = []
    rcols = st.columns(min(n, 10))
    for i in range(n):
        with rcols[i % 10]:
            val = st.number_input(
                f"R{i+1}",
                value=rep_vals[i],
                key=f"dm_rep_{i}",
                label_visibility="collapsed",
            )
            new_reps.append(val)

    if st.button("\U0001f4be Save Changes", type="primary", key="dm_save_edit"):
        try:
            repo.update_batch(
                row["batch_id"], row["formula"], row["parameter"],
                {"reps": new_reps, "lower_spec": lsl, "upper_spec": usl},
            )
            st.success("Updated successfully")
            st.rerun()
        except ValueError as e:
            st.error(str(e))
