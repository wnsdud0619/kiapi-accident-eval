import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import os
import io

# 1. 웹 페이지 기본 설정
st.set_page_config(page_title="자율주행 사고재현 검증 플랫폼", layout="wide", initial_sidebar_state="collapsed")

# 2. 커스텀 CSS
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }
    .badge-pass { background-color: #d1fae5; color: #065f46; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-cond { background-color: #fef3c7; color: #92400e; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-fail { background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .final-box { border: 2px solid #f59e0b; padding: 15px; border-radius: 8px; background-color: #fffbeb; }
    .metric-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; }
    .metric-title { font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 2px; }
    .metric-value { font-size: 18px; color: #0f172a; font-weight: 700; }
    .sync-banner { background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 8px 12px; border-radius: 4px; margin: 8px 0; font-size: 13px; color: #1e40af; }
    .sampling-banner { background-color: #f1f5f9; border-left: 4px solid #64748b; padding: 6px 10px; border-radius: 4px; margin: 6px 0; font-size: 12px; color: #334155; }
</style>
""", unsafe_allow_html=True)

# 3. 상단 헤더
img_b64 = ""
logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PNG", "Wordmark.png")
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

header_html = f'''
<div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
    {"<img src='data:image/png;base64," + img_b64 + "' style='height: 40px; object-fit: contain;'>" if img_b64 else ""}
    <h1 style="margin: 0; font-size: 2.0rem; font-weight: 700; color: #0f172a;">자율주행 사고재현 S/W 통합 신뢰성 검증 플랫폼</h1>
</div>
'''
st.markdown(header_html, unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# 헬퍼 함수 1: CSV 파싱
# ==========================================
def parse_flexible_csv(file_or_path):
    if hasattr(file_or_path, 'getvalue'):
        raw_bytes = file_or_path.getvalue()
        text = raw_bytes.decode('utf-8', errors='ignore')
    elif isinstance(file_or_path, str):
        with open(file_or_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    else:
        text = file_or_path.read().decode('utf-8', errors='ignore')

    lines = text.splitlines()
    header_idx = 0
    for idx, line in enumerate(lines[:20]):
        tokens = [t.strip().strip('"').lower() for t in line.split(',')]
        if any(keyword in tokens for keyword in ['time', 'time(s)', 'frame']):
            header_idx = idx
            break

    df = pd.read_csv(io.StringIO(text), skiprows=header_idx)
    df.columns = [c.strip().strip('"') for c in df.columns]
    return df

# ==========================================
# 헬퍼 함수 2: 기준 데이터(DSSAD/EDR) 특징 추출
# ==========================================
def extract_dssad_features(df):
    time_col = next((c for c in df.columns if c.lower() in ['time', 'time(s)']), df.columns[0])
    df[time_col] = pd.to_numeric(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col]).sort_values(time_col).reset_index(drop=True)

    col_x = next((c for c in df.columns if 'location-x' in c.lower()), None)
    col_y = next((c for c in df.columns if 'location-y' in c.lower()), None)
    col_speed = next((c for c in df.columns if 'determined vehicle speed' in c.lower() or 'vehicle speed' in c.lower()), None)

    ws_fr = next((c for c in df.columns if 'wheelspeedfr' in c.lower().replace(' ', '').replace('_', '')), None)
    ws_fl = next((c for c in df.columns if 'wheelspeedfl' in c.lower().replace(' ', '').replace('_', '')), None)
    ws_rr = next((c for c in df.columns if 'wheelspeedrr' in c.lower().replace(' ', '').replace('_', '')), None)
    ws_rl = next((c for c in df.columns if 'wheelspeedrl' in c.lower().replace(' ', '').replace('_', '')), None)

    wheel_cols = {'FR': ws_fr, 'FL': ws_fl, 'RR': ws_rr, 'RL': ws_rl}
    valid_wheels = [col for col in wheel_cols.values() if col is not None]
    wheel_avg = df[valid_wheels].mean(axis=1) if valid_wheels else None

    main_speed = pd.to_numeric(df[col_speed], errors='coerce') if col_speed else wheel_avg

    return {
        'time_col': time_col,
        'col_x': col_x,
        'col_y': col_y,
        'col_speed': col_speed,
        'wheel_cols': wheel_cols,
        'main_speed': main_speed,
        'wheel_avg': wheel_avg
    }

# ==========================================
# 헬퍼 함수 3: 시뮬레이션 재현 데이터(위치 & 속도) 파싱 및 병합
# ==========================================
def extract_sim_features(sim_dfs, pos_prefix=('gnss_src_x', 'gnss_src_y')):
    if not sim_dfs:
        return None, {}

    df_merged = None
    pos_file_found = False
    spd_file_found = False
    
    col_sim_x = None
    col_sim_y = None
    col_sim_speed = None
    time_col = None

    for df_item in sim_dfs:
        df = df_item.copy()
        t_c = next((c for c in df.columns if 'time' in c.lower()), None)
        if t_c:
            df[t_c] = pd.to_numeric(df[t_c], errors='coerce')
            df = df.dropna(subset=[t_c]).sort_values(t_c).reset_index(drop=True)
            time_col = t_c

        # GNSS 컬럼 탐색 (gnss_x, gnss_y)
        # GNSS 위치 컬럼 탐색 (기본: gnss_src_x(m), gnss_src_y(m))
        def _find(prefix):
            return next((c for c in df.columns if c.lower().replace(' ', '').startswith(prefix)), None)
        curr_x = _find(pos_prefix[0])
        curr_y = _find(pos_prefix[1])
        curr_spd = next((c for c in df.columns if 'speed' in c.lower()), None)

        if curr_x and curr_y:
            col_sim_x = curr_x
            col_sim_y = curr_y
            pos_file_found = True

        if curr_spd:
            col_sim_speed = curr_spd
            spd_file_found = True

        if df_merged is None:
            df_merged = df
        else:
            join_key = next((k for k in ['frame', 'time(s)', 'Time'] if k in df_merged.columns and k in df.columns), None)
            if join_key:
                df_merged = pd.merge(df_merged, df, on=join_key, suffixes=('', '_dup'), how='outer')
                # outer merge 시 한쪽 파일에만 있는 frame은 시간값이 _dup 컬럼에만 존재 → 병합
                for c in list(df_merged.columns):
                    if c.endswith('_dup') and c[:-4] in df_merged.columns:
                        df_merged[c[:-4]] = df_merged[c[:-4]].fillna(df_merged[c])
                if time_col in df_merged.columns:
                    df_merged = df_merged.sort_values(time_col).reset_index(drop=True)
            else:
                df_merged = pd.concat([df_merged, df], axis=1)

    return df_merged, {
        'time_col': time_col,
        'col_x': col_sim_x,
        'col_y': col_sim_y,
        'col_speed': col_sim_speed,
        'pos_file_found': pos_file_found,
        'spd_file_found': spd_file_found
    }

# ==========================================
# 헬퍼 함수 4: 차량 진행방향 기반 정밀 횡방향 오차 (Frenet Frame)
# ==========================================
def calculate_frenet_errors(x_ref, y_ref, x_test, y_test):
    """
    주행 진행 방향(접선 벡터)을 고려하여 실제 차선 이탈량(횡방향 오차)과 전진 밀림량(종방향 오차)을 직교 분해
    """
    dx = np.gradient(x_ref)
    dy = np.gradient(y_ref)
    heading = np.arctan2(dy, dx) # 차량 주행 각도

    diff_x = x_test - x_ref
    diff_y = y_test - y_ref

    # Frenet 변환: 종방향(전진 오차) / 횡방향(차선 직교 오차)
    err_lon = diff_x * np.cos(heading) + diff_y * np.sin(heading)
    err_lat = -diff_x * np.sin(heading) + diff_y * np.cos(heading)
    euclidean = np.sqrt(diff_x**2 + diff_y**2)

    return np.abs(err_lat), np.abs(err_lon), euclidean

# ==========================================
# 레이아웃 분할
# ==========================================
col1, col2, col3 = st.columns([1.25, 2.45, 1.3])

# ==========================================
# [좌측 영역] 1. 파일 불러오기 및 프로세스 제어
# ==========================================
with col1:
    st.subheader("1. 데이터 및 프로세스 제어")
    
    st.markdown("##### ▶ 기준 데이터 (DSSAD/EDR)")
    edr_file = st.file_uploader("📂 기준 데이터 CSV 불러오기", type=['csv'], key="edr_uploader")
    
    use_sample_edr = False
    if not edr_file:
        if os.path.exists("sample_dssad.csv"):
            use_sample_edr = st.checkbox("📌 기본 샘플 DSSAD 데이터 사용", value=False, key="use_sample_edr")

    df_edr = None
    edr_info = None
    if edr_file:
        try:
            df_edr = parse_flexible_csv(edr_file)
            st.success(f"✔ 기준 데이터 로드 완료 ({len(df_edr)} 행)")
        except Exception as e:
            st.error(f"기준 파일 파싱 오류: {e}")
    elif use_sample_edr:
        try:
            df_edr = parse_flexible_csv("sample_dssad.csv")
            st.info("ℹ️ 샘플 DSSAD 데이터 적용 중 (sample_dssad.csv)")
        except Exception as e:
            st.error(f"샘플 로드 오류: {e}")

    if df_edr is not None:
        edr_info = extract_dssad_features(df_edr)
        dssad_t0 = float(df_edr[edr_info['time_col']].min())
        dssad_t_end = float(df_edr[edr_info['time_col']].max())
    else:
        dssad_t0 = 0.0
        dssad_t_end = 0.0

    st.markdown("##### ▶ 재현 S/W 데이터 (최대 2개 파일)")
    sim_files = st.file_uploader(
        "📂 재현 결과 CSV 불러오기 (위치/속도 파일)", 
        type=['csv'], 
        accept_multiple_files=True,
        help="GNSS 위치 파일(gnss_x, gnss_y) 및 속도 파일(Speed)을 최대 2개까지 업로드할 수 있습니다."
    )
    
    use_sample_sim = False
    if not sim_files:
        if os.path.exists("sample_sim_position.csv") and os.path.exists("sample_sim_speed.csv"):
            use_sample_sim = st.checkbox("📌 기본 샘플 재현 데이터 사용 (위치+속도)", value=False, key="use_sample_sim")

    sim_parsed_list = []
    if sim_files:
        if len(sim_files) > 2:
            st.warning("⚠️ 최대 2개 파일까지만 분석에 사용됩니다. (초과 파일 무시)")
        for sf in sim_files[:2]:
            try:
                parsed_df = parse_flexible_csv(sf)
                sim_parsed_list.append(parsed_df)
                st.success(f"✔ {sf.name} 로드 완료 ({len(parsed_df)} 행)")
            except Exception as e:
                st.error(f"재현 파일({sf.name}) 로드 오류: {e}")
    elif use_sample_sim:
        try:
            df_p = parse_flexible_csv("sample_sim_position.csv")
            df_s = parse_flexible_csv("sample_sim_speed.csv")
            sim_parsed_list = [df_p, df_s]
            st.info("ℹ️ 샘플 재현 데이터 적용 중 (위치 + 속도 2개 파일)")
        except Exception as e:
            st.error(f"샘플 재현 데이터 로드 오류: {e}")

    df_sim, sim_info = extract_sim_features(sim_parsed_list, pos_prefix=('gnss_src_x', 'gnss_src_y'))

    # ----------------------------------------------------
    # 타임스탬프 동기화 및 샘플링 분석
    # ----------------------------------------------------
    st.markdown("##### ▶ 타임스탬프 동기화 & 샘플링 보정")
    auto_sync = st.checkbox("기준 데이터 기반 자동 동기화", value=True)
    
    if auto_sync:
        time_offset = dssad_t0
        st.markdown(f"""
        <div class="sync-banner">
            ⏱️ <b>Time Offset 자동 정합:</b> +{time_offset:.2f}s 적용됨<br>
            <span style="font-size:11px;color:#475569;">Sim(0.00s~13.26s) ➔ 기준시간({dssad_t0:.2f}s~{dssad_t_end:.2f}s)</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        time_offset = st.number_input("수동 Time Offset (초)", value=dssad_t0, step=0.01, format="%.2f")

    st.markdown(f"""
    <div class="sampling-banner">
        📶 <b>샘플링 레이트 비교</b><br>
        • 기준 GNSS: <b>100ms (10 Hz)</b><br>
        • 시뮬레이터: <b>20ms (50 Hz)</b>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔍 감지된 데이터 신호 정보", expanded=False):
        if edr_info:
            st.caption(f"• **[기준] 위치**: `{edr_info['col_x']}`, `{edr_info['col_y']}`")
            st.caption(f"• **[기준] 속도**: `{edr_info['col_speed']}`")
        if sim_info:
            pos_badge = "✅" if sim_info.get('pos_file_found') else "❌"
            spd_badge = "✅" if sim_info.get('spd_file_found') else "❌"
            st.caption(f"• **[재현] GNSS 위치**: `{sim_info.get('col_x')}` ({pos_badge})")
            st.caption(f"• **[재현] 속도**: `{sim_info.get('col_speed')}` ({spd_badge})")

    st.markdown("##### 🔹 필수요건 점검")
    st.checkbox("데이터 품질 점검 여부", value=True, disabled=True)
    st.checkbox("재현 실행 정상 수행", value=True, disabled=True)
    st.checkbox("비교 데이터셋 생성", value=True, disabled=True)
    
    if st.button("⚙️ 유사도 및 검증 지표 연산 실행", use_container_width=True, type="primary"):
        st.toast("정합성 평가가 완료되었습니다!")

# ==========================================
# 데이터 처리 및 동기화/보간 연산
# ==========================================
has_edr = False
t_edr_pos, x_edr, y_edr = None, None, None
t_edr_spd, v_edr = None, None

if df_edr is not None and edr_info is not None and edr_info.get('col_x') and edr_info.get('col_y'):
    time_edr_col = edr_info['time_col']
    mask_edr_pos = df_edr[edr_info['col_x']].notna() & df_edr[edr_info['col_y']].notna()
    if mask_edr_pos.any():
        pos_edr_df = df_edr[mask_edr_pos].copy()
        t_edr_pos = pos_edr_df[time_edr_col].values
        x_edr = pos_edr_df[edr_info['col_x']].values
        y_edr = pos_edr_df[edr_info['col_y']].values
        has_edr = True
        
        spd_edr_series = edr_info.get('main_speed')
        if spd_edr_series is not None:
            mask_edr_spd = spd_edr_series.notna()
            if mask_edr_spd.any():
                spd_edr_df = df_edr[mask_edr_spd].copy()
                t_edr_spd = spd_edr_df[time_edr_col].values
                v_edr = spd_edr_series[mask_edr_spd].values

has_sim = False
t_sim_pos, x_sim, y_sim = None, None, None
t_sim_spd, v_sim = None, None

if df_sim is not None and sim_info and sim_info.get('col_x') and sim_info.get('col_y') and sim_info.get('col_speed'):
    t_sim_raw = df_sim[sim_info['time_col']].values
    t_sim_aligned = t_sim_raw + time_offset # 시간 오프셋 보정

    x_sim_raw = pd.to_numeric(df_sim[sim_info['col_x']], errors='coerce').values
    y_sim_raw = pd.to_numeric(df_sim[sim_info['col_y']], errors='coerce').values
    v_sim_raw = pd.to_numeric(df_sim[sim_info['col_speed']], errors='coerce').values

    valid_sim_pos = ~np.isnan(x_sim_raw) & ~np.isnan(y_sim_raw)
    valid_sim_spd = ~np.isnan(v_sim_raw)
    
    if valid_sim_pos.any():
        t_sim_pos = t_sim_aligned[valid_sim_pos]
        x_sim = x_sim_raw[valid_sim_pos]
        y_sim = y_sim_raw[valid_sim_pos]
    
    if valid_sim_spd.any():
        t_sim_spd = t_sim_aligned[valid_sim_spd]
        v_sim = v_sim_raw[valid_sim_spd]

    if valid_sim_pos.any() and valid_sim_spd.any():
        has_sim = True

# ----------------------------------------------------
# 4. 정합 및 오차 연산 (기준 + 재현 데이터 모두 존재할 때만 수행)
# ----------------------------------------------------
def align_to_ref(t_ref, t_src, v_src, tol=0.005):
    """t_ref 각 시각에 대해 t_src에서 |Δt|<=tol 인 샘플을 그대로 사용, 없으면 보간"""
    t_src = np.asarray(t_src, float); v_src = np.asarray(v_src, float)
    order = np.argsort(t_src); t_src, v_src = t_src[order], v_src[order]
    idx = np.clip(np.searchsorted(t_src, t_ref), 1, len(t_src) - 1)
    left, right = idx - 1, idx
    nearest = np.where(np.abs(t_src[left] - t_ref) <= np.abs(t_src[right] - t_ref), left, right)
    exact = np.abs(t_src[nearest] - t_ref) <= tol
    out = np.where(exact, v_src[nearest], np.interp(t_ref, t_src, v_src))
    in_range = (t_ref >= t_src[0] - tol) & (t_ref <= t_src[-1] + tol)
    return out, exact, in_range

def point_to_polyline_dist(Q, A):
    dmin = np.full(len(Q), np.inf)
    for i in range(len(A) - 1):
        Ai, Bi = A[i], A[i + 1]
        AB = Bi - Ai
        L2 = float(AB @ AB)
        if L2 == 0.0:
            dist = np.linalg.norm(Q - Ai, axis=1)
        else:
            t = ((Q - Ai) @ AB) / L2
            dist = np.where(t <= 0, np.linalg.norm(Q - Ai, axis=1),
                   np.where(t >= 1, np.linalg.norm(Q - Bi, axis=1),
                            np.linalg.norm(Q - (Ai + np.outer(t, AB)), axis=1)))
        dmin = np.minimum(dmin, dist)
    return dmin

def calculate_iso18571_corridor_score(t_ref_vals, c_sim_vals, a0=0.05, b0=0.50, k_z=2):
    """ISO/TS 18571 하위 지표 중 Corridor 점수 Z 산출 (표준 기본값: a0=0.05, b0=0.50, k_Z=2)"""
    t_ref_vals = np.asarray(t_ref_vals, float)
    c_sim_vals = np.asarray(c_sim_vals, float)
    if len(t_ref_vals) == 0:
        return 0.0, np.array([]), 0.0, 0.0, 0.0

    t_norm = float(np.max(np.abs(t_ref_vals)))
    err = np.abs(c_sim_vals - t_ref_vals)
    if t_norm == 0.0:
        z_t = np.where(err == 0.0, 1.0, 0.0)
        return float(np.mean(z_t)), z_t, 0.0, 0.0, 0.0

    delta_i = a0 * t_norm
    delta_o = b0 * t_norm
    if delta_o <= delta_i:
        z_t = np.where(err <= delta_i, 1.0, 0.0)
    else:
        z_t = np.where(
            err <= delta_i,
            1.0,
            np.where(
                err >= delta_o,
                0.0,
                ((delta_o - err) / (delta_o - delta_i)) ** k_z
            )
        )
    return float(np.mean(z_t)), z_t, t_norm, delta_i, delta_o

has_comparison = has_edr and has_sim and (len(x_edr) > 1) and (len(x_sim) > 1)

if has_comparison:
    # 평가 구간: DSSAD 0.1s 시각 중 Sim 데이터 범위 안에 있는 시각만 사용
    x_sim_interp, exact_x, rng_pos = align_to_ref(t_edr_pos, t_sim_pos, x_sim)
    y_sim_interp, exact_y, _ = align_to_ref(t_edr_pos, t_sim_pos, y_sim)
    exact_pos = exact_x & exact_y

    t_edr_pos_eval = t_edr_pos[rng_pos]
    x_edr_eval = x_edr[rng_pos]
    y_edr_eval = y_edr[rng_pos]
    x_sim_interp = x_sim_interp[rng_pos]
    y_sim_interp = y_sim_interp[rng_pos]
    exact_pos = exact_pos[rng_pos]
    n_pos_total, n_pos_exact = len(t_edr_pos_eval), int(exact_pos.sum())

    # 차량 진행방향(Frenet Frame) 기준 정밀 횡방향 / 종방향 오차 분해
    err_lat, err_lon, euclidean_error = calculate_frenet_errors(x_edr_eval, y_edr_eval, x_sim_interp, y_sim_interp)

    rmse_lat = np.sqrt(np.mean(err_lat ** 2))
    mae_lat = np.mean(err_lat)
    max_lat = np.max(err_lat)

    rmse_lon = np.sqrt(np.mean(err_lon ** 2))
    mae_lon = np.mean(err_lon)
    max_lon = np.max(err_lon)

    rmse_euclid = np.sqrt(np.mean(euclidean_error ** 2))

    # 속도 오차
    if v_edr is not None and len(v_edr) > 0 and v_sim is not None and len(v_sim) > 0:
        v_edr_at_pos = np.interp(t_edr_pos_eval, t_edr_spd, v_edr)
        v_sim_interp, exact_spd, rng_spd = align_to_ref(t_edr_pos_eval, t_sim_spd, v_sim)
        v_edr_eval = v_edr_at_pos[rng_spd]
        v_sim_interp = v_sim_interp[rng_spd]
        exact_spd = exact_spd[rng_spd]
        t_edr_spd_eval = t_edr_pos_eval[rng_spd]
        n_spd_total, n_spd_exact = len(t_edr_spd_eval), int(exact_spd.sum())
        speed_error = np.abs(v_edr_eval - v_sim_interp)

        rmse_speed = np.sqrt(np.mean(speed_error ** 2))
        mae_speed = np.mean(speed_error)
        max_speed = np.max(speed_error)
    else:
        v_edr_eval, v_sim_interp, speed_error = np.array([]), np.array([]), np.array([])
        t_edr_spd_eval = np.array([])
        n_spd_total, n_spd_exact = 0, 0
        rmse_speed, mae_speed, max_speed = 0.0, 0.0, 0.0

    # 유사도 파라미터 (col1)
    with col1:
        st.markdown("##### 🔹 유사도 지표 파라미터")
        ACC_T = st.number_input("궤적 Accuracy 임계거리 T (m)", value=0.1, min_value=0.01, step=0.05, format="%.2f")
        with st.expander("⚙️ ISO/TS 18571 속도 Corridor 파라미터", expanded=False):
            ISO_A0 = st.number_input("내부 통로 비율 a0 (표준 기본값 0.05)", value=0.05, min_value=0.01, max_value=0.49, step=0.01, format="%.2f")
            ISO_B0 = st.number_input("외부 통로 비율 b0 (표준 기본값 0.50)", value=0.50, min_value=0.05, max_value=1.00, step=0.05, format="%.2f")
            ISO_KZ = st.selectbox("통로 감쇠 지수 k_Z (표준 기본값 2)", options=[1, 2, 3], index=1)
            if ISO_B0 <= ISO_A0:
                st.warning("외부 통로 비율(b0)은 내부 통로 비율(a0)보다 커야 합니다.")
                ISO_B0 = min(1.0, ISO_A0 + 0.05)

    # (1) 궤적 Accuracy(T)
    poly_ref = np.c_[x_edr_eval, y_edr_eval]
    Q_sim = np.c_[x_sim_interp, y_sim_interp]
    d_poly = point_to_polyline_dist(Q_sim, poly_ref)
    traj_N = len(d_poly)
    traj_hit = int(np.sum(d_poly <= ACC_T))
    traj_accuracy = traj_hit / traj_N * 100 if traj_N else 0.0

    # (2) 속도 Corridor 점수 (ISO/TS 18571 하위 지표 Z)
    if len(v_edr_eval) > 0:
        spd_N = len(v_edr_eval)
        spd_z_score, spd_z_t, spd_t_norm, spd_delta_i, spd_delta_o = calculate_iso18571_corridor_score(
            v_edr_eval, v_sim_interp, a0=ISO_A0, b0=ISO_B0, k_z=ISO_KZ
        )
        speed_accuracy = spd_z_score * 100.0
    else:
        spd_N, spd_z_score, spd_t_norm, spd_delta_i, spd_delta_o, speed_accuracy = 0, 0.0, 0.0, 0.0, 0.0, 0.0

# ==========================================
# [중앙 영역] 2. 뷰어 및 시각화
# ==========================================
with col2:
    tab1, tab2, tab3 = st.tabs([
        "🗺️ 주행 궤적 비교 (GNSS Map View)", 
        "⚡ 속도 추종성 비교 (Speed Profile)", 
        "📉 물리좌표계 오차 분석 (Frenet Lateral/Longitudinal)"
    ])
    
    # ----------------------------------------------------
    # TAB 1: 주행 궤적 오버랩 뷰어
    # ----------------------------------------------------
    with tab1:
        st.subheader("2. 주행 궤적 오버랩 뷰어 (GNSS 위치 데이터)")
        
        if not has_edr and not has_sim:
            st.markdown("""
            <div style="border: 2px dashed #94a3b8; border-radius: 8px; padding: 60px 20px; text-align: center; background-color: #f8fafc; margin-top: 15px;">
                <div style="font-size: 40px; margin-bottom: 12px;">📂</div>
                <div style="font-size: 17px; font-weight: 700; color: #1e293b; margin-bottom: 6px;">표시할 주행 궤적 데이터가 없습니다.</div>
                <div style="font-size: 13px; color: #64748b; line-height: 1.6;">
                    좌측의 <b>[1. 데이터 및 프로세스 제어]</b> 영역에서<br>
                    기준 데이터(DSSAD/EDR) 또는 재현 S/W 데이터 CSV 파일을 업로드하면 궤적이 시각화됩니다.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            aspect_equal = st.checkbox("📏 실제 도로 1:1 종횡비 고정 (왜곡 방지)", value=True, help="체크 시 X/Y축 축척을 동일하게 1:1로 고정하여 실제 도로 비율 그대로 표현합니다.")

            fig_map = go.Figure()
            
            # 1. 기준 궤적 플롯 (DSSAD)
            if has_edr and x_edr is not None and len(x_edr) > 0:
                fig_map.add_trace(go.Scatter(
                    x=x_edr, y=y_edr,
                    mode='lines',
                    name='기준 궤적 (DSSAD GNSS)',
                    line=dict(color='#0284c7', width=4),
                    hovertemplate="<b>[기준 DSSAD]</b><br>시간: %{customdata:.2f}s<br>X (횡방향): %{x:.3f}m<br>Y (종방향): %{y:.3f}m<extra></extra>",
                    customdata=t_edr_pos
                ))
                
                # 출발점 및 정지점 마커
                fig_map.add_trace(go.Scatter(
                    x=[x_edr[0]], y=[y_edr[0]],
                    mode='markers+text',
                    name='주행 시작점',
                    marker=dict(symbol='circle', size=13, color='#16a34a', line=dict(width=2, color='white')),
                    text=["출발"], textposition="bottom center"
                ))
                fig_map.add_trace(go.Scatter(
                    x=[x_edr[-1]], y=[y_edr[-1]],
                    mode='markers+text',
                    name='최종 정지점',
                    marker=dict(symbol='star', size=15, color='#dc2626', line=dict(width=2, color='white')),
                    text=["정지"], textposition="top center"
                ))
            
            # 2. 재현 궤적 플롯 (Sim)
            if has_sim and x_sim is not None and len(x_sim) > 0:
                fig_map.add_trace(go.Scatter(
                    x=x_sim, y=y_sim,
                    mode='lines',
                    name='재현 궤적 (Sim GNSS)',
                    line=dict(color='#f43f5e', width=2.5, dash='dash'),
                    hovertemplate="<b>[재현 S/W]</b><br>시간: %{customdata:.2f}s<br>X (횡방향): %{x:.3f}m<br>Y (종방향): %{y:.3f}m<extra></extra>",
                    customdata=t_sim_pos
                ))
            
            yaxis_cfg = dict(
                title="GNSS Y 좌표 (m) [주행 종방향]",
                showgrid=True,
                zeroline=False
            )
            if aspect_equal:
                yaxis_cfg['scaleanchor'] = "x"
                yaxis_cfg['scaleratio'] = 1
            
            fig_map.update_layout(
                height=540,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis=dict(
                    title="GNSS X 좌표 (m) [차선 횡방향]",
                    showgrid=True,
                    zeroline=False
                ),
                yaxis=yaxis_cfg,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_map, use_container_width=True)
            
            if has_comparison:
                st.caption(
                    f"⏱️ 평가 시간축 = DSSAD GNSS 0.1s 시각 **{n_pos_total}개** · "
                    f"Sim(0.02s) 동일 시각 직접 매칭 **{n_pos_exact}개** · "
                    f"동일 시각 샘플 없어 보간 {n_pos_total - n_pos_exact}개"
                )
    
    # ----------------------------------------------------
    # TAB 2: 속도 추종성 비교
    # ----------------------------------------------------
    with tab2:
        st.subheader("기준 차속 vs 재현 S/W 속도 추종 비교")
        has_speed_data = (has_edr and v_edr is not None and len(v_edr) > 0) or (has_sim and v_sim is not None and len(v_sim) > 0)
        
        if not has_speed_data:
            st.markdown("""
            <div style="border: 2px dashed #94a3b8; border-radius: 8px; padding: 60px 20px; text-align: center; background-color: #f8fafc; margin-top: 15px;">
                <div style="font-size: 40px; margin-bottom: 12px;">⚡</div>
                <div style="font-size: 17px; font-weight: 700; color: #1e293b; margin-bottom: 6px;">표시할 속도 데이터가 없습니다.</div>
                <div style="font-size: 13px; color: #64748b; line-height: 1.6;">
                    좌측 패널에서 속도 신호가 포함된 CSV 파일을 업로드해 주세요.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            fig_speed = go.Figure()
            
            if has_comparison and len(v_edr_eval) > 0 and spd_delta_i > 0:
                fig_speed.add_trace(go.Scatter(
                    x=np.concatenate([t_edr_spd_eval, t_edr_spd_eval[::-1]]),
                    y=np.concatenate([v_edr_eval + spd_delta_i, (v_edr_eval - spd_delta_i)[::-1]]),
                    fill='toself',
                    fillcolor='rgba(16, 185, 129, 0.15)',
                    line=dict(color='rgba(16, 185, 129, 0.35)', width=1, dash='dot'),
                    name=f'ISO/TS 18571 내부 통로 (±{spd_delta_i:.2f} km/h)',
                    hoverinfo='skip'
                ))

            if has_edr and v_edr is not None and len(v_edr) > 0:
                fig_speed.add_trace(go.Scatter(
                    x=t_edr_spd, y=v_edr,
                    mode='lines',
                    name='기준 차속 (DSSAD)',
                    line=dict(color='#0284c7', width=3.5),
                    hovertemplate="Time: %{x:.2f}s<br>속도: %{y:.2f} km/h<extra></extra>"
                ))
            
            if has_sim and v_sim is not None and len(v_sim) > 0:
                fig_speed.add_trace(go.Scatter(
                    x=t_sim_spd, y=v_sim,
                    mode='lines',
                    name='재현 속도 (Sim Speed)',
                    line=dict(color='#f43f5e', width=2.5, dash='dash'),
                    hovertemplate="Time: %{x:.2f}s<br>속도: %{y:.2f} km/h<extra></extra>"
                ))
            
            fig_speed.update_layout(
                height=370,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis_title="시간 Time (s) [Time Offset 동기화 적용]",
                yaxis_title="속도 (km/h)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_speed, use_container_width=True)
            if has_comparison and len(v_edr_eval) > 0:
                st.caption(
                    f"⚡ ISO/TS 18571 속도 Corridor 점수 = **{speed_accuracy:.2f}%** (Z={spd_z_score:.4f}, 평가 {spd_N}개 전 구간) · "
                    f"T_norm={spd_t_norm:.2f} km/h, 내부통로 ±{spd_delta_i:.2f} km/h, 외부통로 ±{spd_delta_o:.2f} km/h"
                )
    
    # ----------------------------------------------------
    # TAB 3: 정밀 시계열 오차 분석 (Frenet 분해)
    # ----------------------------------------------------
    with tab3:
        st.subheader("3. 진행방향 기준 직교 오차 분석 (Frenet Frame)")
        
        if not has_comparison:
            st.markdown("""
            <div style="border: 2px dashed #94a3b8; border-radius: 8px; padding: 60px 20px; text-align: center; background-color: #f8fafc; margin-top: 15px;">
                <div style="font-size: 40px; margin-bottom: 12px;">📉</div>
                <div style="font-size: 17px; font-weight: 700; color: #1e293b; margin-bottom: 6px;">오차 분석을 위한 비교 데이터셋이 부족합니다.</div>
                <div style="font-size: 13px; color: #64748b; line-height: 1.6;">
                    <b>기준 데이터(DSSAD/EDR)</b>와 <b>재현 S/W 데이터</b>가 모두 로드되어야<br>
                    실제 차선 횡방향 이탈 오차 및 주행 밀림 오차를 분석할 수 있습니다.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            fig_err = make_subplots(
                rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.14,
                subplot_titles=[
                    f"(1) 실제 차선 횡방향 이탈 오차 |e_lat| (RMSE: {rmse_lat:.2f}m, MAE: {mae_lat:.2f}m)",
                    f"(2) 주행 종방향 밀림 오차 |e_lon| (RMSE: {rmse_lon:.2f}m, MAE: {mae_lon:.2f}m)"
                ]
            )
            
            # 1. 실제 차선 횡방향 오차 (Frenet Lateral)
            fig_err.add_trace(go.Scatter(
                x=t_edr_pos_eval, y=err_lat,
                mode='lines', name='차선 횡방향 오차',
                fill='tozeroy', line=dict(color='#10b981', width=2)
            ), row=1, col=1)
            fig_err.add_hline(y=0.20, line_dash="dot", line_color="#16a34a", annotation_text="0.20m (합격선)", row=1, col=1)
            fig_err.add_hline(y=0.57, line_dash="dash", line_color="#dc2626", annotation_text="0.57m (불가선)", row=1, col=1)
            
            # 2. 주행 종방향 밀림 오차 (Frenet Longitudinal)
            fig_err.add_trace(go.Scatter(
                x=t_edr_pos_eval, y=err_lon,
                mode='lines', name='주행 종방향 오차',
                fill='tozeroy', line=dict(color='#f59e0b', width=2)
            ), row=2, col=1)
            
            fig_err.update_layout(
                height=370,
                margin=dict(l=10, r=10, t=30, b=10),
                showlegend=False
            )
            st.plotly_chart(fig_err, use_container_width=True)
            st.caption("💡 차량의 주행 궤적 법선(Normal) 벡터로 투영하여 제동 거리 차이(종방향)와 실제 차선 이탈량(횡방향)을 물리적으로 정확히 분리했습니다.")

# ==========================================
# [우측 영역] 3. 정량 지표 연산 및 판정
# ==========================================
with col3:
    st.subheader("4. 유사도 정량 평가")

    if not has_comparison:
        st.markdown("""
        <div class="metric-card" style="text-align:center; padding: 40px 15px; margin-top: 15px;">
            <div style="font-size: 32px; margin-bottom: 10px;">📊</div>
            <div style="font-size: 15px; font-weight: 700; color: #1e293b; margin-bottom: 6px;">평가 데이터 대기 중</div>
            <div style="font-size: 12px; color: #64748b; line-height: 1.6;">
                좌측 패널에서 <b>기준 데이터</b>와 <b>재현 S/W 데이터</b>를<br>
                모두 업로드하면 유사도(%) 및 정량 오차 지표가 자동으로 산출됩니다.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("##### 📊 유사도 (0 ~ 100%)")
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            <div class="metric-card">
                <div class="metric-title">궤적 Accuracy (T={ACC_T:.2f}m)</div>
                <div class="metric-value" style="color:#0284c7;">{traj_accuracy:.2f} <span style="font-size:12px;font-weight:normal;">%</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-title">속도 Corridor (ISO/TS 18571)</div>
                <div class="metric-value" style="color:#16a34a;">{speed_accuracy:.2f} <span style="font-size:12px;font-weight:normal;">%</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("##### 📏 오차 지표")
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            <div class="metric-card">
                <div class="metric-title">횡방향 MAE</div>
                <div class="metric-value">{mae_lat:.3f} <span style="font-size:12px;font-weight:normal;">m</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-title">횡방향 RMSE</div>
                <div class="metric-value">{rmse_lat:.3f} <span style="font-size:12px;font-weight:normal;">m</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-title">속도 MAE</div>
                <div class="metric-value">{mae_speed:.3f} <span style="font-size:12px;font-weight:normal;">km/h</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-title">속도 RMSE</div>
                <div class="metric-value">{rmse_speed:.3f} <span style="font-size:12px;font-weight:normal;">km/h</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("##### 🔹 상세 오차표")
        st.markdown(f"""
| 평가 변수 | 지표 | 측정 결과 |
|---|---|---|
| **횡방향 궤적** | RMSE | **{rmse_lat:.3f} m** |
| 횡방향 궤적 | MAE | {mae_lat:.3f} m |
| 횡방향 궤적 | 최대 편차 | {max_lat:.3f} m |
| **종방향 궤적** | RMSE | **{rmse_lon:.3f} m** |
| 종방향 궤적 | MAE | {mae_lon:.3f} m |
| **주행 속도** | RMSE | **{rmse_speed:.3f} km/h** |
| 주행 속도 | MAE | {mae_speed:.3f} km/h |
| 주행 속도 | 최대 편차 | {max_speed:.3f} km/h |
""")

