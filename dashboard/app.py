import os
import tempfile
from pathlib import Path
import importlib
import io

import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]


def _inject_css() -> None:
    st.markdown(
        """
<style>
  :root {
    --bg: #f5f4f0;
    --card: #ffffff;
    --text: #1a1a1a;
    --muted: #888;
    --border: rgba(0,0,0,0.10);
    /* Slightly softer palette */
    --green: #1B9A6C;
    --green2: #117A57;
    --blue: #3A78D8;
    --amber: #B87424;
    --red: #E05555;
  }

  .stApp { background: var(--bg); color: var(--text); }

  /* Cards */
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
  }
  .card.hi {
    border-color: rgba(29,158,117,0.35);
    background: rgba(29,158,117,0.09);
  }
  .klabel { font-size: 11px; color: var(--muted); margin-bottom: 6px; }
  .kvalue { font-size: 22px; font-weight: 600; line-height: 1.1; }
  .kunit { font-size: 12px; color: #aaa; margin-top: 4px; }

  .pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 12px;
    color: var(--green2);
    background: rgba(29,158,117,0.10);
    border: 1px solid rgba(29,158,117,0.25);
  }

  .title-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }
  .title {
    font-size: 18px;
    font-weight: 600;
  }
  .sub { font-size: 12px; color: #aaa; }

  /* Tighten Streamlit defaults */
  div[data-testid="stSidebar"] { background: #fff; }
  div[data-testid="stSidebar"] > div { border-right: 1px solid var(--border); }
  section.main > div { padding-top: 1.6rem; }
  .block-container { padding-left: 2rem; padding-right: 2rem; }

  /* Metrics grid */
  .metrics { display: grid; grid-template-columns: repeat(5, minmax(140px, 1fr)); gap: 10px; }
  @media (max-width: 1050px) { .metrics { grid-template-columns: repeat(2, minmax(140px, 1fr)); } }

  /* Keep Streamlit charts consistent */
  div[data-testid="stVegaLiteChart"] { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 10px; }
</style>
""",
        unsafe_allow_html=True,
    )


def _structure_palette(region: str) -> str:
    # Muted, but distinct and color-blind-friendly-ish.
    region = region.upper()
    return {
        "ZP": "#3A78D8",   # blue
        "TE": "#1B9A6C",   # green
        "ICM": "#E07A2F",  # orange
        "BC": "#7C869A",   # blue-gray
    }.get(region, "#999")


def _series_palette(name: str) -> str:
    name = (name or "").lower()
    if name in {"te", "te_area", "te_area_ratio", "te_fractal_d", "te_mean_thickness"}:
        return _structure_palette("TE")
    if name in {"icm", "icm_area", "icm_area_ratio", "icm_eccentricity"}:
        return _structure_palette("ICM")
    if name in {"bc", "bc_area", "bc_area_ratio"}:
        return _structure_palette("BC")
    if name in {"zp", "zp_area", "zp_r", "zp_r_outer", "zp_r_inner", "zp_thickness", "zp_symmetry", "zp_r"}:
        return _structure_palette("ZP")
    if name in {"n_cells", "cells", "cell count"}:
        return "#3A78D8"
    if name in {"fragmentation", "fragmentation_idx"}:
        return "#B87424"
    return "#7C869A"


def _render_structure_areas_chart(df_area) -> None:
    """Render a nicer bar chart with fixed colors.

    Uses Altair when available; otherwise falls back to Streamlit's default chart.
    """
    df = df_area.copy()
    df["area"] = df["area"].fillna(0)

    try:
        alt = importlib.import_module("altair")
    except Exception:
        st.bar_chart(df.set_index("region"))
        return

    domain = ["ZP", "TE", "ICM", "BC"]
    rng = [_structure_palette(r) for r in domain]

    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadius=6)
        .encode(
            y=alt.Y("region:N", sort=domain, title=""),
            x=alt.X("area:Q", title="Area (px²)"),
            color=alt.Color(
                "region:N",
                scale=alt.Scale(domain=domain, range=rng),
                legend=None,
            ),
            tooltip=["region:N", alt.Tooltip("area:Q", format=",")],
        )
        .properties(height=160)
    )

    st.altair_chart(chart, use_container_width=True)


def _render_structure_composition_pie(te: float, icm: float, bc: float) -> None:
    """Pie chart for TE/ICM/BC with fixed palette."""
    pd = importlib.import_module("pandas")
    df = pd.DataFrame(
        {
            "region": ["TE", "ICM", "BC"],
            "area": [float(te or 0), float(icm or 0), float(bc or 0)],
        }
    )
    total = float(df["area"].sum())
    if total <= 0:
        st.info("Not enough data to plot composition.")
        return

    df["pct"] = df["area"] / total

    try:
        alt = importlib.import_module("altair")
    except Exception:
        # Fallback to matplotlib
        mpl = importlib.import_module("matplotlib.pyplot")
        fig, ax = mpl.subplots(figsize=(5, 5))
        ax.pie(
            df["area"].tolist(),
            labels=df["region"].tolist(),
            autopct=lambda p: f"{p:.1f}%",
            colors=[_structure_palette("TE"), _structure_palette("ICM"), _structure_palette("BC")],
            textprops={"color": "#1a1a1a"},
        )
        ax.set_aspect("equal")
        st.pyplot(fig, use_container_width=False)
        return

    domain = ["TE", "ICM", "BC"]
    rng = [_structure_palette(r) for r in domain]

    base = alt.Chart(df).encode(
        theta=alt.Theta("area:Q", stack=True),
        color=alt.Color(
            "region:N",
            scale=alt.Scale(domain=domain, range=rng),
            legend=alt.Legend(orient="bottom", title=None),
        ),
        tooltip=[
            "region:N",
            alt.Tooltip("area:Q", format=","),
            alt.Tooltip("pct:Q", title="%", format=".1%"),
        ],
    )

    pie = base.mark_arc(outerRadius=145, innerRadius=70)

    labels = (
        alt.Chart(df)
        .mark_text(radius=170, fontSize=12, fontWeight=600)
        .encode(
            theta=alt.Theta("area:Q", stack=True),
            text=alt.Text("pct:Q", format=".1%"),
            color=alt.value("#1a1a1a"),
        )
    )
    names = (
        alt.Chart(df)
        .mark_text(radius=115, fontSize=13, fontWeight=700)
        .encode(
            theta=alt.Theta("area:Q", stack=True),
            text="region:N",
            color=alt.value("#ffffff"),
        )
    )

    # Give it enough vertical space so it doesn't clip.
    st.altair_chart((pie + names + labels).properties(height=420), use_container_width=True)


def _render_line_chart(df, x_col: str, y_cols: list[str], *, height: int = 220) -> None:
    """Altair line chart with fixed colors; fallback to st.line_chart."""
    pd = importlib.import_module("pandas")
    if not y_cols:
        st.info("No series to plot")
        return

    dff = df[[x_col] + y_cols].copy()
    # Normalize Nones
    for c in y_cols:
        dff[c] = pd.to_numeric(dff[c], errors="coerce")

    try:
        alt = importlib.import_module("altair")
    except Exception:
        st.line_chart(df.set_index(x_col)[y_cols])
        return

    long_df = dff.melt(id_vars=[x_col], var_name="series", value_name="value")
    domain = y_cols
    rng = [_series_palette(s) for s in domain]

    chart = (
        alt.Chart(long_df)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X(f"{x_col}:Q", title=x_col.replace("_", " ").title()),
            y=alt.Y("value:Q", title=""),
            color=alt.Color("series:N", scale=alt.Scale(domain=domain, range=rng), legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[f"{x_col}:Q", "series:N", alt.Tooltip("value:Q", format=",")],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def _metric(label: str, value: str, unit: str = "", highlight: bool = False) -> None:
    cls = "card hi" if highlight else "card"
    st.markdown(
        f"""
<div class="{cls}">
  <div class="klabel">{label}</div>
  <div class="kvalue">{value}</div>
  <div class="kunit">{unit}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _grade_color(g: str) -> str:
    if g == "A":
        return "#1D9E75"
    if g == "B":
        return "#BA7517"
    return "#E24B4A"


def _overlay_from_masks(img_rgb, zp, te, icm):
    np = importlib.import_module("numpy")
    # Colors consistent with the HTML mock.
    out = img_rgb.copy()

    def paint(mask, color: tuple[int, int, int], alpha: float) -> None:
        if mask is None:
            return
        m = mask > 0
        out[m] = (out[m] * (1 - alpha) + np.array(color, dtype=np.float32) * alpha).astype(np.uint8)

    paint(zp, (55, 138, 221), 0.35)   # blue
    paint(te, (29, 158, 117), 0.35)   # green
    paint(icm, (216, 90, 48), 0.45)   # orange
    return out


def _overlay_fragmentation(img_rgb, frag_mask):
    """Overlay fragmentation mask on top of the real image."""
    np = importlib.import_module("numpy")
    if frag_mask is None:
        return None

    base = img_rgb.copy()
    mask = frag_mask > 0
    if mask.shape[:2] != base.shape[:2]:
        # Best-effort: align mask to image size.
        cv2 = importlib.import_module("cv2")
        resized = cv2.resize(
            frag_mask.astype("uint8"),
            (base.shape[1], base.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        )
        mask = resized > 0

    # Warm red overlay
    color = np.array([226, 75, 74], dtype=np.float32)
    alpha = 0.45
    base[mask] = (base[mask] * (1 - alpha) + color * alpha).astype(np.uint8)
    return base


def _save_uploaded_to_temp(uploaded) -> str:
    suffix = Path(uploaded.name).suffix
    fd, path = tempfile.mkstemp(prefix="embryoscope_", suffix=suffix)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())
    return path


@st.cache_data(show_spinner=False)
def _analyze_image_bytes(
    image_bytes: bytes,
    filename: str,
    include_blastocyst_structures: bool,
    include_cell_count: bool,
    include_fragmentation: bool,
    include_grading: bool,
    include_stage: bool,
):
    cv2 = importlib.import_module("cv2")
    np = importlib.import_module("numpy")

    EmbryoImage = importlib.import_module("inference.embryo_img").EmbryoImage

    # Decode bytes into RGB image
    file_arr = np.frombuffer(image_bytes, np.uint8)
    bgr = cv2.imdecode(file_arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Could not decode image '{filename}'")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    embryo = EmbryoImage(img=rgb, cropped_image=False, compute=False)
    try:
        values = embryo.get_values(
            include_blastocyst_structures=include_blastocyst_structures,
            include_cell_count=include_cell_count,
            include_fragmentation=include_fragmentation,
            include_grading=include_grading,
            include_stage=include_stage,
        )
    except TypeError:
        # If EmbryoImage is loaded from an older version without the new flag.
        values = embryo.get_values(
            include_cell_count=include_cell_count,
            include_fragmentation=include_fragmentation,
            include_grading=include_grading,
            include_stage=include_stage,
        )

    frag_mask = embryo.get_fragmentation() if include_fragmentation else None
    frag_overlay = _overlay_fragmentation(embryo.get_image(), frag_mask) if include_fragmentation else None

    overlay = None
    seg = None
    if include_blastocyst_structures:
        overlay = _overlay_from_masks(
            embryo.get_cropped_embryo(),
            embryo.get_ZP(),
            embryo.get_TE(),
            embryo.get_ICM(),
        )
        seg = embryo.get_blasto_seg()

    return values, overlay, seg, frag_overlay


def _video_frames_from_path(path: str, n_max: int):
    cv2 = importlib.import_module("cv2")

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError("Failed to open video")
    frames = []

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, (total // n_max) if total else 1)
    for i in range(n_max):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        frames.append(frame)
    cap.release()
    return frames


@st.cache_data(show_spinner=False)
def _analyze_video_path(
    video_path: str,
    n_frames: int,
    real_secs: float,
    include_blastocyst_structures: bool,
    include_fragmentation: bool,
    include_grading: bool,
    include_stage: bool,
):
    cv2 = importlib.import_module("cv2")
    pd = importlib.import_module("pandas")

    EmbryoImage = importlib.import_module("inference.embryo_img").EmbryoImage
    EmbryoVideo = importlib.import_module("inference.embryo_video").EmbryoVideo

    frames_bgr = _video_frames_from_path(video_path, n_frames)
    if not frames_bgr:
        raise ValueError("No frames extracted")

    frames_rgb = [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in frames_bgr]
    video = EmbryoVideo(frames=frames_rgb, mask=[1] * len(frames_rgb), n_MAX=len(frames_rgb), n_total=len(frames_rgb), cropped=False)
    video.get_video_frames = lambda simplify=True: frames_rgb  # bypass capture
    video.cropped_video_frames = frames_rgb

    # Compute per-frame metrics. Cell count is expensive; keep it on for timeline usefulness.
    values = {k: [] for k in EmbryoVideo.DEFAULT_FEATURES}
    for frame in frames_rgb:
        embryo = EmbryoImage(img=frame, cropped_image=True, compute=False)
        try:
            v = embryo.get_values(
                include_blastocyst_structures=include_blastocyst_structures,
                include_cell_count=True,
                include_fragmentation=include_fragmentation,
                include_grading=include_grading,
                include_stage=include_stage,
            )
        except TypeError:
            v = embryo.get_values(
                include_cell_count=True,
                include_fragmentation=include_fragmentation,
                include_grading=include_grading,
                include_stage=include_stage,
            )
        for k in values.keys():
            values[k].append(v.get(k, None))

    # Add time axis (hours)
    hours = [(i * real_secs) / (len(frames_rgb) * 3600.0) for i in range(len(frames_rgb))]
    df = pd.DataFrame(values)
    df.insert(0, "frame", range(len(df)))
    df.insert(1, "time_hours", hours)

    summary = {
        "frames": len(frames_rgb),
        "duration_hours": hours[-1] if hours else 0,
    }

    # Blasto formation: use existing helper if TE/ICM exist
    try:
        video.values = {k: df[k].tolist() for k in df.columns if k in EmbryoVideo.DEFAULT_FEATURES}
        blasto_frame = video.get_blasto_frame()
        summary["blasto_frame"] = int(blasto_frame)
        if 0 <= int(blasto_frame) < len(hours):
            summary["blasto_formation_hours"] = float(hours[int(blasto_frame)])
    except Exception:
        pass

    return df, summary


def main() -> None:
    st.set_page_config(page_title="EmbryoMarkers", layout="wide")
    _inject_css()

    # If this renders but the rest doesn't, it's an import/deps issue below.
    st.write("")

    missing = []
    for mod, pip_name in [
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("cv2", "opencv-python"),
        ("torch", "torch"),
        ("torchvision", "torchvision"),
        ("skimage", "scikit-image"),
        ("scipy", "scipy"),
        ("sklearn", "scikit-learn"),
    ]:
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append((mod, pip_name))

    if missing:
        st.error(
            "Faltan dependencias de Python. Esto suele dar pantalla blanca o reinicios del servidor."
        )
        st.code(
            "python3 -m pip install -r requirements.txt\n\n"
            "# o instala solo lo que falta:\n"
            + "\n".join([f"python3 -m pip install {pip}" for _, pip in missing])
        )
        st.stop()

    # Shared deps for UI rendering
    pd = importlib.import_module("pandas")

    st.markdown(
        """
<div class="title-row">
  <div>
    <div class="title">EmbryoMarkers <span class="pill">Research Analysis Platform</span></div>
    <div class="sub">Upload an image or a timelapse video to extract embryo markers</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Upload")
        uploaded = st.file_uploader(
            "Drop images or videos here",
            type=["jpg", "jpeg", "png", "bmp", "tiff", "mp4", "avi", "mov", "mkv"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

        if uploaded:
            names = [f.name for f in uploaded]
            active_name = st.selectbox("Loaded samples", names, index=0)
        else:
            active_name = None

        st.divider()
        st.markdown("### Options")
        include_blastocyst_structures = st.toggle("Blastocyst structures", value=True)
        include_cell_count = st.toggle("Cell count", value=False)
        include_fragmentation = st.toggle("Fragmentation", value=False)
        include_grading = st.toggle("Grading", value=False)
        include_stage = st.toggle("Stage", value=False)

        st.caption("Tip: enable only what you need; some models are heavy.")

        st.divider()
        st.markdown("### Video")
        n_frames = st.slider("Frames to sample", min_value=20, max_value=300, value=120, step=10)
        real_secs = st.number_input("Real duration (seconds)", min_value=1.0, value=3000.0, step=100.0)

    if not uploaded:
        st.info("Upload an image or video to start.")
        return

    active = next(f for f in uploaded if f.name == active_name)
    ext = Path(active.name).suffix.lower()
    is_video = ext in {".mp4", ".avi", ".mov", ".mkv"}

    # Small preview on the right
    col_main, col_preview = st.columns([3, 1], gap="large")
    with col_preview:
        st.markdown("### Preview")
        if is_video:
            st.video(active.getvalue())
        else:
            try:
                img = (
                    importlib.import_module("PIL.Image")
                    .open(io.BytesIO(active.getvalue()))
                    .convert("RGB")
                )
                # Keep it smaller than full container.
                st.image(img, width=340)
            except Exception as e:
                st.error(f"Could not preview image: {e}")

    if not is_video:
        with col_main:
            with st.spinner("Analyzing image…"):
                values, overlay, seg, frag_overlay = _analyze_image_bytes(
                    active.getvalue(),
                    active.name,
                    include_blastocyst_structures,
                    include_cell_count,
                    include_fragmentation,
                    include_grading,
                    include_stage,
                )

            st.markdown(f"#### {active.name}  ")

            tab_names = ["Overview", "Graphs"]
            if include_blastocyst_structures:
                tab_names.insert(1, "Blastocyst")
                tab_names.append("Segmentation")
            else:
                tab_names.append("Segmentation")
            tabs = st.tabs(tab_names)

            tab_overview = tabs[0]
            if include_blastocyst_structures:
                tab_blasto = tabs[1]
                tab_graphs = tabs[2]
                tab_seg = tabs[3]
            else:
                tab_graphs = tabs[1]
                tab_seg = tabs[2]

        with tab_overview:
            # First: grading cards
            c1, c2, c3 = st.columns(3)
            te_g = values.get("te_grading")
            icm_g = values.get("icm_grading")
            exp = values.get("expansion")
            with c1:
                st.markdown(
                    f"<div class='card hi' style='text-align:center'><div class='klabel'>Expansion</div><div class='kvalue' style='font-size:34px;color:#0F6E56'>{'' if exp is None else exp}</div><div class='kunit'>stage (1–6)</div></div>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"<div class='card' style='text-align:center'><div class='klabel'>TE</div><div class='kvalue' style='font-size:34px;color:{_grade_color(te_g)}'>{te_g}</div><div class='kunit'>grading</div></div>",
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    f"<div class='card' style='text-align:center'><div class='klabel'>ICM</div><div class='kvalue' style='font-size:34px;color:{_grade_color(icm_g)}'>{icm_g}</div><div class='kunit'>grading</div></div>",
                    unsafe_allow_html=True,
                )

            st.markdown('<div class="metrics">', unsafe_allow_html=True)
            stage_txt = values.get("stage_classif")
            _metric("Stage", stage_txt if stage_txt is not None else "(disabled)", "classification")
            _metric("Number of cells", str(values.get("n_cells")), "cells")
            frag = values.get("fragmentation_idx")
            frag_txt = "" if frag is None else f"{frag * 100:.1f}%"
            _metric("Fragmentation", frag_txt or "(disabled)", "index")
            _metric("Total area", f"{values.get('area', 0):.0f}", "px²")
            _metric("Diameter", f"{values.get('diameter', 0):.2f}", "px")
            st.markdown("</div>", unsafe_allow_html=True)

            st.divider()
            st.markdown("**Structure areas**")
            df_area = pd.DataFrame(
                {
                    "region": ["ZP", "TE", "ICM", "BC"],
                    "area": [
                        values.get("ZP_area"),
                        values.get("TE_area"),
                        values.get("ICM_area"),
                        values.get("BC_area"),
                    ],
                }
            )
            _render_structure_areas_chart(df_area)

        if include_blastocyst_structures:
            with tab_blasto:
                zp_tab, te_tab, icm_tab, bc_tab = st.tabs(["ZP", "TE", "ICM", "Blastocele"])

            with zp_tab:
                st.markdown('<div class="metrics">', unsafe_allow_html=True)
                _metric("Outer radius (R)", f"{values.get('ZP_R', 0):.2f}", "px")
                _metric("Inner radius (r)", f"{values.get('ZP_r', 0):.2f}", "px")
                _metric("Thickness", f"{values.get('ZP_thickness', 0):.2f}", "px")
                _metric("ZP area", f"{values.get('ZP_area', 0):.0f}", "px²")
                sym = values.get("ZP_symmetry")
                sym_txt = "" if sym is None else f"{sym * 100:.1f}%"
                _metric("Symmetry", sym_txt, "IoU", highlight=(sym is not None and sym > 0.85))
                st.markdown("</div>", unsafe_allow_html=True)

            with te_tab:
                st.markdown('<div class="metrics">', unsafe_allow_html=True)
                _metric("TE grading", str(values.get("te_grading")), "A/B/C")
                _metric("TE area", f"{values.get('TE_area', 0):.0f}", "px²")
                _metric("TE area ratio", f"{values.get('TE_area_ratio', 0):.3f}", "0–1")
                _metric("TE fractal D", f"{values.get('TE_fractal_d', 0):.3f}", "Higuchi")
                _metric("TE mean thickness", f"{values.get('TE_mean_thickness', 0):.2f}", "px")
                st.markdown("</div>", unsafe_allow_html=True)

            with icm_tab:
                st.markdown('<div class="metrics">', unsafe_allow_html=True)
                _metric("ICM grading", str(values.get("icm_grading")), "A/B/C")
                _metric("ICM area", f"{values.get('ICM_area', 0):.0f}", "px²")
                _metric("ICM area ratio", f"{values.get('ICM_area_ratio', 0):.3f}", "0–1")
                ecc = values.get("ICM_eccentricity")
                _metric("ICM eccentricity", "" if ecc is None else f"{ecc:.3f}", "0=circle")
                st.markdown("</div>", unsafe_allow_html=True)

            with bc_tab:
                st.markdown('<div class="metrics">', unsafe_allow_html=True)
                _metric("BC area", f"{values.get('BC_area', 0):.0f}", "px²")
                _metric("BC area ratio", f"{values.get('BC_area_ratio', 0):.3f}", "0–1")
                st.markdown("</div>", unsafe_allow_html=True)

        with tab_graphs:
            if not include_blastocyst_structures:
                st.info("Enable ‘Blastocyst structures’ to see structure-based graphs.")
            else:
                st.markdown("**Blastocyst composition (TE / ICM / BC)**")
                te = values.get("TE_area") or 0
                icm = values.get("ICM_area") or 0
                bc = values.get("BC_area") or 0
                _render_structure_composition_pie(te, icm, bc)

                st.divider()
                st.markdown("**Compartment areas (px²)**")
                df_area = pd.DataFrame(
                    {
                        "region": ["ZP", "TE", "ICM", "BC"],
                        "area": [
                            values.get("ZP_area"),
                            values.get("TE_area"),
                            values.get("ICM_area"),
                            values.get("BC_area"),
                        ],
                    }
                )
                _render_structure_areas_chart(df_area)

        with tab_seg:
            c1, c2 = st.columns([1, 1], gap="large")
            with c1:
                st.markdown("**Blastocyst segmentation**")
                if overlay is None:
                    st.info("Enable ‘Blastocyst structures’ to see this overlay.")
                else:
                    st.image(overlay, use_container_width=True)
            with c2:
                st.markdown("**Fragmentation**")
                if frag_overlay is None:
                    st.info("Enable ‘Fragmentation’ in the sidebar.")
                else:
                    st.image(frag_overlay, use_container_width=True)

            # Export
            st.divider()
            df = pd.DataFrame([values])
            st.download_button(
                "Export CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"{Path(active.name).stem}_metrics.csv",
                mime="text/csv",
            )
        return

    # Video path required for OpenCV seeking
    with col_main:
        with st.spinner("Preparing video…"):
            video_path = _save_uploaded_to_temp(active)

        with st.spinner("Analyzing video (sampled frames)…"):
            df, summary = _analyze_video_path(
                video_path,
                n_frames=n_frames,
                real_secs=real_secs,
                include_blastocyst_structures=include_blastocyst_structures,
                include_fragmentation=include_fragmentation,
                include_grading=include_grading,
                include_stage=include_stage,
            )

        st.markdown(f"#### {active.name}  ")
        st.markdown(
            "<span class='pill' style='background: rgba(186,117,23,0.10); border-color: rgba(186,117,23,0.25); color: #854F0B'>Video analysis</span>",
            unsafe_allow_html=True,
        )

        tab_overview, tab_evolution = st.tabs(["Overview", "Evolution"])

        with tab_overview:
            st.markdown('<div class="metrics">', unsafe_allow_html=True)
            _metric("Duration analysed", f"{summary.get('duration_hours', 0):.2f}h", "timelapse")
            _metric("Frames processed", str(summary.get("frames", len(df))), "frames")
            blasto = summary.get("blasto_formation_hours")
            _metric(
                "Blastocyst formation",
                "" if blasto is None else f"{blasto:.2f}h",
                "post fertilisation",
                highlight=True,
            )
            last_cells = df["n_cells"].dropna().iloc[-1] if "n_cells" in df and df["n_cells"].notna().any() else None
            _metric("Final cell count", "" if last_cells is None else str(int(last_cells)), "cells")
            _metric("", "", "")
            st.markdown("</div>", unsafe_allow_html=True)

            if include_stage and "stage_classif" in df.columns and df["stage_classif"].notna().any():
                st.markdown("**Stage (last known)**")
                st.write(str(df["stage_classif"].dropna().iloc[-1]))

            if include_grading and any(c in df.columns for c in ["expansion", "te_grading", "icm_grading"]):
                st.markdown("**Grading (last known)**")
                cols = [c for c in ["expansion", "te_grading", "icm_grading"] if c in df.columns]
                if cols:
                    st.dataframe(df[cols].tail(1), use_container_width=True, hide_index=True)

        with tab_evolution:
            st.markdown("**Cells & fragmentation**")
            c1, c2 = st.columns(2)
            with c1:
                if "n_cells" in df:
                    _render_line_chart(df, "time_hours", ["n_cells"], height=220)
            with c2:
                if "fragmentation_idx" in df.columns and df["fragmentation_idx"].notna().any():
                    _render_line_chart(df, "time_hours", ["fragmentation_idx"], height=220)
                else:
                    st.info("Enable ‘Fragmentation’ to see this.")

            if include_blastocyst_structures:
                st.divider()
                st.markdown("**Structure areas**")
                area_cols = [
                    c
                    for c in ["ZP_area", "TE_area", "ICM_area", "BC_area", "area"]
                    if c in df.columns
                ]
                _render_line_chart(df, "time_hours", area_cols, height=260)

                st.divider()
                st.markdown("**ZP geometry**")
                zp_cols = [c for c in ["ZP_R", "ZP_r", "ZP_thickness", "ZP_symmetry"] if c in df.columns]
                if zp_cols:
                    _render_line_chart(df, "time_hours", zp_cols, height=240)

                st.divider()
                st.markdown("**Embryo size**")
                size_cols = [c for c in ["diameter", "area"] if c in df.columns]
                if size_cols:
                    _render_line_chart(df, "time_hours", size_cols, height=240)

                st.divider()
                st.markdown("**Ratios**")
                ratio_cols = [c for c in ["TE_area_ratio", "ICM_area_ratio", "BC_area_ratio"] if c in df.columns]
                if ratio_cols:
                    _render_line_chart(df, "time_hours", ratio_cols, height=240)

                st.divider()
                st.markdown("**TE / ICM morphology**")
                morph_cols = [
                    c
                    for c in ["TE_fractal_d", "TE_mean_thickness", "ICM_eccentricity"]
                    if c in df.columns
                ]
                if morph_cols:
                    _render_line_chart(df, "time_hours", morph_cols, height=240)
            else:
                st.info("Enable ‘Blastocyst structures’ to plot structure evolution.")

            st.divider()
            st.markdown("**All markers (table)**")
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.download_button(
            "Export CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{Path(active.name).stem}_evolution.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
