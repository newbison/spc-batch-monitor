import streamlit as st
import pandas as pd
import math
import re
import io
from datetime import datetime, date
from data_access.base import DataRepository
from config import DATA_DIR

UPLOADS_DIR = DATA_DIR / "uploads"
FIXED_COLS = {"date", "batch_id", "formula", "parameter", "lower_spec", "upper_spec"}


def _build_template_csv(n: int) -> str:
    """Return a CSV string template with example data for one batch.

    Parameters
    ----------
    n : int
        Number of replicate columns to include (from repo.subgroup_size()).
    """
    rep_cols = [f"rep{i}" for i in range(1, n + 1)]
    rows = [
        {
            "date": "2025-06-01", "batch_id": "COAT-XXX", "formula": "Your Formula",
            "parameter": "adhesion", "lower_spec": 0.6, "upper_spec": 1.5,
            **{f"rep{i}": round(1.05 + (i - 3) * 0.04, 3) for i in range(1, n + 1)},
        },
        {
            "date": "2025-06-01", "batch_id": "COAT-XXX", "formula": "Your Formula",
            "parameter": "cohesion", "lower_spec": 1000.0, "upper_spec": None,
            **{f"rep{i}": round(1500 + (i - 5) * 40) for i in range(1, n + 1)},
        },
        {
            "date": "2025-06-01", "batch_id": "COAT-XXX", "formula": "Your Formula",
            "parameter": "rolling_ball_tack", "lower_spec": 10.0, "upper_spec": 50.0,
            **{f"rep{i}": round(30 + (i - 5) * 2, 1) for i in range(1, n + 1)},
        },
        {
            "date": "2025-06-01", "batch_id": "COAT-XXX", "formula": "Your Formula",
            "parameter": "liner_release", "lower_spec": 5.0, "upper_spec": 20.0,
            **{f"rep{i}": round(12.5 + (i - 5) * 0.8, 2) for i in range(1, n + 1)},
        },
    ]
    cols = ["date", "batch_id", "formula", "parameter", "lower_spec", "upper_spec"] + [f"rep{i}" for i in range(1, n + 1)]
    df = pd.DataFrame(rows, columns=cols)
    return df.to_csv(index=False)


def render_data_entry(repo: DataRepository):
    st.header("🧪 Batch Data Entry")

    mode = st.radio("Input mode:", ["📂 CSV Upload", "✏️ Manual Entry", "📋 View & Edit"],
                    horizontal=True, key="entry_mode")

    if mode == "📂 CSV Upload":
        _render_csv_upload(repo)
    elif mode == "✏️ Manual Entry":
        _render_manual_entry(repo)
    else:
        _render_view_edit(repo)


def _render_csv_upload(repo: DataRepository):
    n = repo.subgroup_size()
    rep_cols_list = [f"rep{i}" for i in range(1, n + 1)]
    required_cols = FIXED_COLS | set(rep_cols_list)

    st.subheader("Upload Batch Data CSV")
    st.caption(f"Expected columns: date, batch_id, formula, parameter, "
               f"{', '.join(rep_cols_list[:3])}...{rep_cols_list[-1]} "
               f"({n} replicates), lower_spec, upper_spec")

    # --- CSV Format Instructions ---
    with st.expander("CSV Format Instructions"):
        st.markdown(f"""
**Column layout** (one row per test-parameter combination):

| Column | Description |
|--------|-------------|
| `date` | Batch date (YYYY-MM-DD) |
| `batch_id` | Unique batch/lot identifier |
| `formula` | Formula or product name |
| `parameter` | Test name (e.g. adhesion, cohesion, rolling_ball_tack, liner_release) |
| `rep1` … `rep{n}` | {n} replicate measurements |
| `lower_spec` | Lower specification limit (leave blank if none) |
| `upper_spec` | Upper specification limit (leave blank if none) |

**Rules:**
- One row per (batch, parameter) — a single batch produces {n} rows (one per test).
- Spec limits: leave the cell **empty** (not 0) if a parameter has no lower or upper limit.
- Formula names are case-sensitive — use the same spelling across all uploads.
- Download the **template** below for a ready-to-edit example.
""")

        template_csv = _build_template_csv(n)
        st.download_button(
            label="Download CSV Template",
            data=template_csv,
            file_name="spc_template.csv",
            mime="text/csv",
            key="op_dl_template",
        )

    uploaded = st.file_uploader("Choose CSV file", type=["csv"], key="op_upload")

    if uploaded is not None:
        new_df = pd.read_csv(uploaded)
        missing = required_cols - set(new_df.columns)
        if missing:
            st.error(f"Missing columns: {', '.join(sorted(missing))}")
            st.write("Your columns:", list(new_df.columns))
            return

        st.write(f"**{len(new_df)} rows** | {new_df['formula'].nunique()} formula(s) "
                 f"| {n} replicates per measurement")

        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(new_df.head(6), use_container_width=True, hide_index=True)

        with col2:
            st.write("**Formulas in upload:**")
            for f in sorted(new_df["formula"].unique()):
                count = len(new_df[new_df["formula"] == f])
                st.write(f"- {f}: {count} rows")

        st.divider()

        if st.button("✅ Confirm Import", type="primary", key="op_import_btn"):
            # Archive the raw CSV
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            archive_path = UPLOADS_DIR / f"{ts}-{uploaded.name}"
            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            new_df.to_csv(archive_path, index=False)

            # Upload to SQLite with validation + dedup
            result = repo.upload_csv(new_df)

            if result["errors"]:
                st.error(f"Validation failed — {len(result['errors'])} error(s):")
                for err in result["errors"][:10]:
                    st.write(f"- {err}")
                if len(result["errors"]) > 10:
                    st.write(f"- ... and {len(result['errors']) - 10} more")

            if result["inserted"] > 0 or result["skipped"] > 0:
                msg = f"✅ Imported {result['inserted']} new rows"
                if result["skipped"] > 0:
                    msg += f", skipped {result['skipped']} duplicates"
                msg += f". Archive: {archive_path.name}"
                st.success(msg)

            if not result["errors"]:
                st.rerun()


def _render_manual_entry(repo: DataRepository):
    n = repo.subgroup_size()
    st.subheader(f"Manual Data Entry  — {n} replicates per test")
    st.caption("Enter measurements for each parameter.")

    existing_formulas = repo.get_formulas()
    formula_options = existing_formulas + ["+ New Formula"]
    selected = st.selectbox("Formula", formula_options, key="entry_formula")

    if selected == "+ New Formula":
        formula = st.text_input("New formula name", key="entry_new_formula")
    else:
        formula = selected

    col1, col2 = st.columns(2)
    with col1:
        batch_id = st.text_input("Batch ID", value="COAT-", key="entry_batch_id")
    with col2:
        batch_date = st.date_input("Date", value=date.today(), key="entry_date")

    st.divider()

    params = repo.get_parameters()
    if not params:
        params = ["adhesion", "cohesion", "rolling_ball_tack", "liner_release"]

    measurements = {}
    cols = st.columns(len(params))

    for i, param in enumerate(params):
        prior_specs = repo.get_specs_for_formula(formula, param) if formula else None
        ps = prior_specs if prior_specs else {"lower_spec": 0.0, "upper_spec": 0.0}

        with cols[i]:
            st.markdown(f"**{param}**")

            # Specs
            sc1, sc2 = st.columns([3, 1])
            with sc1:
                low_default = float(ps["lower_spec"]) if not math.isnan(float(ps["lower_spec"])) else 0.0
                low = st.number_input("LSL", value=low_default, key=f"{param}_lsl",
                                      format="%.3f")
            with sc2:
                no_lsl = st.checkbox("None", key=f"{param}_no_lsl",
                                     value=math.isnan(float(ps["lower_spec"])))

            sc3, sc4 = st.columns([3, 1])
            with sc3:
                high_default = float(ps["upper_spec"]) if not math.isnan(float(ps["upper_spec"])) else 0.0
                high = st.number_input("USL", value=high_default, key=f"{param}_usl",
                                       format="%.3f")
            with sc4:
                no_usl = st.checkbox("None", key=f"{param}_no_usl",
                                     value=math.isnan(float(ps["upper_spec"])))

            lower_spec = float("nan") if no_lsl else low
            upper_spec = float("nan") if no_usl else high

            st.caption("—")

            # Replicate inputs: compact rows of 5
            rep_vals = []
            half = (n + 1) // 2
            for row_idx in range(2):
                rcols = st.columns(5)
                for j in range(5):
                    idx = row_idx * 5 + j
                    if idx < n:
                        default = (low + high) / 2 if not (no_lsl or no_usl) else (low if not no_lsl else high)
                        val = rcols[j].number_input(
                            f"R{idx + 1}", value=default,
                            key=f"{param}_r{idx + 1}",
                            format="%.3f" if param == "liner_release" else "%.2f",
                            label_visibility="collapsed",
                        )
                        rep_vals.append(val)

            avg = sum(rep_vals) / n
            rng = max(rep_vals) - min(rep_vals)
            in_spec = True
            if not no_lsl and avg < lower_spec:
                in_spec = False
            if not no_usl and avg > upper_spec:
                in_spec = False
            status = "✅" if in_spec else "❌"

            st.metric(f"X̄", f"{avg:.3f} {status}")
            st.metric(f"R", f"{rng:.3f}")

            measurements[param] = {
                "reps": rep_vals,
                "lower_spec": lower_spec,
                "upper_spec": upper_spec,
            }

    if st.button("💾 Save Batch", type="primary", key="manual_save"):
        if not formula:
            st.error("Please select or enter a formula name.")
        else:
            try:
                repo.append_batch(batch_id, batch_date.isoformat(), formula, measurements)
                st.success(f"Batch {batch_id} saved for {batch_date.isoformat()}")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    st.divider()
    st.subheader("Recent Batches")
    df = repo.load_all()
    if not df.empty:
        tail = df.sort_values("date", ascending=False).head(12)
        rep_cols = sorted([c for c in tail.columns if re.match(r"^rep\d+$", c)],
                          key=lambda x: int(x[3:]))
        display_cols = ["date", "batch_id", "formula"] + rep_cols + ["lower_spec", "upper_spec"]
        st.dataframe(tail[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No data yet.")


def _render_view_edit(repo: DataRepository):
    st.subheader("View & Edit Recent Batches")
    today = date.today().isoformat()

    df = repo.load_all()
    if df.empty:
        st.info("No data yet.")
        return

    today_df = df[df["date"] == today]
    if today_df.empty:
        st.info("No batches entered today.")
    else:
        rep_cols = sorted(
            [c for c in df.columns if c.startswith("rep") and c[3:].isdigit()],
            key=lambda x: int(x[3:]),
        )
        display_cols = ["date", "batch_id", "formula", "parameter"] + rep_cols + ["lower_spec", "upper_spec"]
        display = today_df[display_cols].sort_values(["date", "batch_id", "parameter"])

        st.caption(f"Today's batches ({today}): {len(display)} rows, "
                   f"{today_df['batch_id'].nunique()} batches")
        st.dataframe(display, use_container_width=True, hide_index=True)

    # Edit a specific batch
    st.divider()
    st.markdown("### Edit a Batch")
    all_batches = sorted(df["batch_id"].unique().tolist(), reverse=True)
    edit_batch = st.selectbox("Select batch", all_batches, key="ve_select_batch")

    if edit_batch:
        batch_df = repo.get_batch(edit_batch)
        if batch_df.empty:
            st.warning(f"No data found for batch {edit_batch}.")
            return

        batch_date = batch_df["date"].iloc[0]
        batch_formula = batch_df["formula"].iloc[0]

        # Operator can only edit today's batches
        if batch_date != today:
            st.warning(f"Batch {edit_batch} is from {batch_date}. Operators can only edit today's batches.")
            return

        st.write(f"Batch: **{edit_batch}**  |  Formula: **{batch_formula}**  |  Date: **{batch_date}**")

        for _, row in batch_df.iterrows():
            param = row["parameter"]
            with st.expander(f"{param}", expanded=False):
                # Find existing replicate values
                existing_reps = []
                for i in range(1, 51):
                    col = f"rep{i}"
                    if col in row.index and not (isinstance(row[col], float) and math.isnan(row[col])):
                        existing_reps.append(float(row[col]))

                n = len(existing_reps)

                rc1, rc2 = st.columns(2)
                with rc1:
                    lsl_val = float(row["lower_spec"]) if not (
                        isinstance(row["lower_spec"], float) and math.isnan(row["lower_spec"])
                    ) else 0.0
                    new_lsl = st.number_input(f"LSL", value=lsl_val, key=f"ve_lsl_{param}")
                with rc2:
                    usl_val = float(row["upper_spec"]) if not (
                        isinstance(row["upper_spec"], float) and math.isnan(row["upper_spec"])
                    ) else 0.0
                    new_usl = st.number_input(f"USL", value=usl_val, key=f"ve_usl_{param}")

                new_reps = []
                rcols = st.columns(min(n, 10))
                for i in range(n):
                    with rcols[i % 10]:
                        val = st.number_input(
                            f"R{i+1}",
                            value=existing_reps[i],
                            key=f"ve_rep_{param}_{i}",
                            label_visibility="collapsed",
                        )
                        new_reps.append(val)

                c_save, c_del = st.columns(2)
                with c_save:
                    if st.button(f"\U0001f4be Save {param}", key=f"ve_save_{param}"):
                        try:
                            repo.update_batch(
                                edit_batch, batch_formula, param,
                                {"reps": new_reps, "lower_spec": new_lsl, "upper_spec": new_usl},
                            )
                            st.success(f"Updated {param}")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

                with c_del:
                    if st.button(f"\U0001f5d1 Delete {param}", key=f"ve_del_{param}"):
                        repo.delete_batch(edit_batch, batch_formula, param)
                        st.success(f"Deleted {param} row")
                        st.rerun()

        st.divider()
        st.warning("⚠️ Delete entire batch")
        if st.button("\U0001f5d1 Delete Entire Batch", key="ve_delete_batch",
                     help=f"Permanently delete all {len(batch_df)} rows for {edit_batch}"):
            count = repo.delete_all_for_batch(edit_batch)
            st.success(f"Deleted {count} rows for batch {edit_batch}")
            st.rerun()
