import streamlit as st
import pandas as pd
import math
import re
from datetime import datetime, date
from config import DATA_FILE, DATA_DIR, SUBGROUP_SIZE

from data_access.repository import CsvRepository

UPLOADS_DIR = DATA_DIR / "uploads"
FIXED_COLS = {"date", "batch_id", "formula", "parameter", "lower_spec", "upper_spec"}


def _detect_n_reps() -> int:
    """Detect subgroup size from existing data, or fall back to config default."""
    if DATA_FILE.exists():
        df = pd.read_csv(DATA_FILE)
        rep_cols = [c for c in df.columns if re.match(r"^rep\d+$", c)]
        if rep_cols:
            return len(rep_cols)
    return SUBGROUP_SIZE


def render_data_entry(repo: CsvRepository):
    st.header("🧪 Batch Data Entry")

    mode = st.radio("Input mode:", ["📂 CSV Upload", "✏️ Manual Entry"],
                    horizontal=True, key="entry_mode")

    if mode == "📂 CSV Upload":
        _render_csv_upload(repo)
    else:
        _render_manual_entry(repo)


def _render_csv_upload(repo: CsvRepository):
    n = _detect_n_reps()
    rep_cols_list = [f"rep{i}" for i in range(1, n + 1)]
    required_cols = FIXED_COLS | set(rep_cols_list)

    st.subheader("Upload Batch Data CSV")
    st.caption(f"Expected columns: date, batch_id, formula, parameter, "
               f"{', '.join(rep_cols_list[:3])}...{rep_cols_list[-1]} "
               f"({n} replicates), lower_spec, upper_spec")

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
        action = st.radio("Action:", ["Append to existing data",
                                       "Replace all data"],
                          horizontal=True, key="op_action")

        if st.button("✅ Confirm Import", type="primary", key="op_import_btn"):
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            archive_path = UPLOADS_DIR / f"{ts}-{uploaded.name}"
            new_df.to_csv(archive_path, index=False)

            if action == "Replace all data":
                new_df.to_csv(DATA_FILE, index=False)
            else:
                existing = pd.read_csv(DATA_FILE) if DATA_FILE.exists() else pd.DataFrame()
                combined = pd.concat([existing, new_df], ignore_index=True)
                combined.to_csv(DATA_FILE, index=False)

            st.success(f"✅ Imported {len(new_df)} rows. Archive: {archive_path.name}")
            if "repo" in st.session_state:
                del st.session_state["repo"]
            st.rerun()


def _render_manual_entry(repo: CsvRepository):
    n = _detect_n_reps()
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
        params = ["adhesion", "cohesion", "tack", "liner_release"]

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
            repo.append_batch(batch_id, batch_date.isoformat(), formula, measurements)
            st.success(f"Batch {batch_id} saved for {batch_date.isoformat()}")
            st.rerun()

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
