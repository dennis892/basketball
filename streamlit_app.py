import streamlit as st
import pandas as pd
from pathlib import Path
import uuid
from datetime import date
from PIL import Image
import altair as alt

# ========== Paths (stable next to this file) ==========
BASE_DIR = Path(__file__).parent.resolve()
DATA_FILE = BASE_DIR / "data.csv"
PLAYERS_FILE = BASE_DIR / "players.csv"
IMAGE_DIR = BASE_DIR / "images"
TEAM_LOGO_FILE = IMAGE_DIR / "team_logo.png"

PLAYER_COLS = ["球員", "生日", "年紀", "身高", "性別", "體重"]
RECORD_COLS = ["record_id", "日期", "球員", "投籃數", "命中數", "是否贏球", "命中率"]

# Bootstrap
IMAGE_DIR.mkdir(exist_ok=True)
if not DATA_FILE.exists():
    pd.DataFrame(columns=RECORD_COLS).to_csv(DATA_FILE, index=False)
if not PLAYERS_FILE.exists():
    pd.DataFrame(columns=PLAYER_COLS).to_csv(PLAYERS_FILE, index=False)
else:
    _p = pd.read_csv(PLAYERS_FILE)
    for c in PLAYER_COLS:
        if c not in _p.columns:
            _p[c] = ""
    _p.to_csv(PLAYERS_FILE, index=False)

# ========== Helpers ==========
def normalize_player_series(s: pd.Series) -> pd.Series:
    if s is None:
        return pd.Series([], dtype="object")
    s = s.astype(str).str.strip()
    s = s.mask(s.isin(["", "nan", "None"]), pd.NA)
    return s

def normalize_win_col(s: pd.Series) -> pd.Series:
    """Normalize win indicator to 'Y' or 'N' only."""
    if s is None:
        return pd.Series([], dtype="object")
    s = s.astype(str).str.strip()
    # Map historical symbols/words to Y/N
    mapping = {
        "✅ 是": "Y", "是": "Y", "Y": "Y", "y": "Y", "Yes": "Y", "YES": "Y", "true": "Y", "True": "Y",
        "❌ 否": "N", "否": "N", "N": "N", "n": "N", "No": "N", "NO": "N", "false": "N", "False": "N",
        "": pd.NA, "nan": pd.NA, "None": pd.NA
    }
    s = s.map(lambda v: mapping.get(v, v))
    # Anything not Y becomes N if it's not NA
    s = s.where(s.isin(["Y","N"]) | s.isna(), "N")
    return s

def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE, dtype=str)  # read as str, cast later
    for c in RECORD_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    df["球員"] = normalize_player_series(df["球員"])
    # Normalize win col to Y/N
    df["是否贏球"] = normalize_win_col(df["是否贏球"])
    for c in ["投籃數", "命中數", "命中率"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["record_id"] = df["record_id"].astype(str).str.strip()
    df.loc[df["record_id"].isin(["", "nan", "None"]), "record_id"] = pd.NA
    return df

def save_data(df: pd.DataFrame) -> None:
    for c in RECORD_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    # Ensure win col is Y/N
    df["是否贏球"] = normalize_win_col(df["是否贏球"])
    df = df[RECORD_COLS].copy()
    df.to_csv(DATA_FILE, index=False)

def load_players_df() -> pd.DataFrame:
    dfp = pd.read_csv(PLAYERS_FILE, dtype=str)
    for c in PLAYER_COLS:
        if c not in dfp.columns:
            dfp[c] = ""
    dfp["球員"] = normalize_player_series(dfp["球員"])
    return dfp

def save_players_df(dfp: pd.DataFrame) -> None:
    for c in PLAYER_COLS:
        if c not in dfp.columns:
            dfp[c] = ""
    dfp = dfp[PLAYER_COLS].copy()
    dfp.to_csv(PLAYERS_FILE, index=False)

def get_player_names() -> list:
    dfp = load_players_df()
    names = normalize_player_series(dfp["球員"]).dropna().unique().tolist()
    names = [str(x) for x in names]
    names.sort()
    return names

def calc_accuracy(shots, made) -> float:
    shots = float(shots) if pd.notna(shots) else 0.0
    made = float(made) if pd.notna(made) else 0.0
    return round((made / shots) * 100, 2) if shots else 0.0

def compute_monthly_medals(pdf: pd.DataFrame) -> dict:
    medals = {"金": 0, "銀": 0, "銅": 0}
    if pdf.empty:
        return medals
    tmp = pdf.copy()
    tmp["日期_dt"] = pd.to_datetime(tmp["日期"], errors="coerce")
    tmp = tmp.dropna(subset=["日期_dt"])
    if tmp.empty:
        return medals
    tmp["month"] = tmp["日期_dt"].dt.to_period("M")
    agg = tmp.groupby("month").agg({"投籃數": "sum", "命中數": "sum"})
    acc = (agg["命中數"] / agg["投籃數"]).fillna(0) * 100
    for v in acc:
        if v >= 60:
            medals["金"] += 1
        elif v >= 50:
            medals["銀"] += 1
        elif v >= 35:
            medals["銅"] += 1
    return medals

# ========== UI Sections ==========
def add_record_section() -> None:
    st.header("📥 新增紀錄")
    st.markdown(
        "#### 🎖️ 勳章規則\n"
        "- **銅勳章**：當月命中率 35%～49%\n"
        "- **銀勳章**：當月命中率 50%～59%\n"
        "- **金勳章**：當月命中率 60% 以上"
    )
    players = get_player_names()
    if not players:
        st.warning("尚未有球員登錄，請先到『球員登錄』頁面登錄球員。")
        return

    with st.form("add_record"):
        c1, c2 = st.columns(2)
        with c1:
            game_date = st.date_input("比賽日期", value=date.today())
        with c2:
            player = st.selectbox("選擇球員", players)
        shots = st.number_input("投籃次數", min_value=0, step=1)
        made = st.number_input("命中次數", min_value=0, step=1)
        win = st.selectbox("這場是否贏球？", ["Y", "N"])   # <-- Y/N
        submit = st.form_submit_button("新增紀錄")

        if submit:
            if made > shots:
                st.warning("命中不能大於投籃")
            else:
                df = load_data()
                new = {
                    "record_id": str(uuid.uuid4()),
                    "日期": game_date.strftime("%Y-%m-%d"),
                    "球員": player,
                    "投籃數": int(shots),
                    "命中數": int(made),
                    "是否贏球": win,  # already Y/N
                    "命中率": calc_accuracy(shots, made),
                }
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                save_data(df)
                st.success("✅ 紀錄新增成功！")

def player_statistics_section(df: pd.DataFrame) -> None:
    st.header("📊 球員資訊")
    names = get_player_names()
    if not names:
        st.info("尚未有球員登錄。")
        return
    name = st.selectbox("選擇球員：", names)

    pdf = df[df["球員"] == name] if not df.empty else pd.DataFrame()

    # 頭像
    img_path = IMAGE_DIR / f"{name}.jpg"
    if img_path.exists():
        st.image(Image.open(img_path), width=120)

    # 整體統計
    total_games = len(pdf)
    total_shots = int(pdf["投籃數"].sum()) if not pdf.empty else 0
    total_made = int(pdf["命中數"].sum()) if not pdf.empty else 0
    acc = calc_accuracy(total_shots, total_made) if not pdf.empty else 0
    win_rate = (pdf["是否贏球"].eq("Y").sum() / total_games * 100) if total_games else 0  # <-- Y

    st.write(f"比賽場數：{total_games}")
    st.write(f"總投籃：{total_shots}，命中：{total_made}")
    st.write(f"命中率：{acc:.2f}%，贏球率：{win_rate:.2f}%")

    # 基本資料
    pdfull = load_players_df()
    row = pdfull[pdfull["球員"] == name]
    if not row.empty:
        info = row.iloc[0]
        def show(v, suffix=""):
            return "未填寫" if pd.isna(v) or str(v).strip()=="" else f"{v}{suffix}"
        st.subheader("📋 球員基本資料")
        st.write(f"姓名：{name}")
        st.write(f"生日：{show(info.get('生日',''))}")
        st.write(f"年紀：{show(info.get('年紀',''))}")
        st.write("身高：" + (f"{show(info.get('身高',''))} cm" if show(info.get('身高',''))!='未填寫' else "未填寫"))
        st.write("體重：" + (f"{show(info.get('體重',''))} kg" if show(info.get('體重',''))!='未填寫' else "未填寫"))
        st.write(f"性別：{show(info.get('性別',''))}")

    # 當日表現
    st.subheader("📅 當日表現")
    if not pdf.empty:
        d = pdf.copy()
        d["日期"] = pd.to_datetime(d["日期"], errors="coerce").dt.date
        d = d.dropna(subset=["日期"])
        if not d.empty:
            agg = (
                d.assign(贏球=d["是否贏球"].eq("Y").astype(int))  # <-- Y
                 .groupby("日期", as_index=False)
                 .agg(當日總投籃=("投籃數","sum"),
                      當日總命中=("命中數","sum"),
                      當日贏球數=("贏球","sum"),
                      場數=("record_id","count"))
            )
            agg["當日命中率(%)"] = (agg["當日總命中"] / agg["當日總投籃"]).fillna(0) * 100
            agg["當日贏球率(%)"] = (agg["當日贏球數"] / agg["場數"]).fillna(0) * 100
            agg = agg.sort_values("日期")
            st.dataframe(agg[["日期","當日命中率(%)","當日贏球率(%)","場數"]], use_container_width=True)
        else:
            st.info("尚無有效日期的比賽紀錄。")
    else:
        st.info("該球員尚無比賽紀錄。")

    # 勳章
    medals = compute_monthly_medals(pdf)
    st.subheader("🏅 勳章統計")
    if any(medals.values()):
        st.markdown(f"🥇 金：{medals['金']}　🥈 銀：{medals['銀']}　🥉 銅：{medals['銅']}")
    else:
        st.write("尚未獲得任何勳章")

    # 趨勢圖
    if not pdf.empty:
        g = pdf.groupby("日期")["命中率"].mean().reset_index()
        g["日期"] = pd.to_datetime(g["日期"], errors="coerce")
        g = g.dropna(subset=["日期"])
        if not g.empty:
            start, end = g["日期"].min(), g["日期"].max()
            chart = (
                alt.Chart(g)
                .mark_line(point=True)
                .encode(x=alt.X("日期:T", scale=alt.Scale(domain=[start, end])), y="命中率:Q")
                .properties(width=600)
            )
            st.subheader("📈 命中率趨勢圖 (以日期為單位)")
            st.altair_chart(chart, use_container_width=True)

def compare_players_section(df: pd.DataFrame) -> None:
    st.header("📊 多人比較")
    if df.empty:
        st.info("目前沒有任何比賽紀錄。")
        return
    players = normalize_player_series(df["球員"]).dropna().unique().tolist()
    players = [str(x) for x in players]
    players.sort()
    chosen = st.multiselect("選擇球員進行比較：", players)
    if chosen:
        cdf = (
            df[df["球員"].isin(chosen)]
            .groupby(["球員","日期"])["命中率"]
            .mean()
            .reset_index()
        )
        cdf["日期"] = pd.to_datetime(cdf["日期"], errors="coerce")
        cdf = cdf.dropna(subset=["日期"])
        if cdf.empty:
            st.warning("⚠️ 選擇的球員目前沒有任何紀錄，無法比較。")
            return
        st.altair_chart(
            alt.Chart(cdf).mark_line(point=True).encode(x="日期:T", y="命中率:Q", color="球員:N").properties(width=600),
            use_container_width=True
        )

def edit_records_section(df: pd.DataFrame) -> None:
    st.header("✏️ 登錄修改")

    # 批次修改（有紀錄時才顯示）
    if df.empty:
        st.info("沒有紀錄可修改")
    else:
        players = normalize_player_series(df["球員"]).dropna().unique().tolist()
        players = [str(x) for x in players]
        players.sort()
        pick = st.selectbox("選擇球員進行修改：", players) if players else None

        if pick:
            sub = df[df["球員"] == pick].copy()
        else:
            sub = df.copy()

        # 移除命中率欄位供編輯，避免誤改；儲存時自動重算
        editable = sub.drop(columns=["命中率"]).copy()

        # 讓 record_id 只讀，避免被刪改
        try:
            col_cfg = {"record_id": st.column_config.TextColumn("record_id", disabled=True)}
        except Exception:
            col_cfg = None

        edited = st.data_editor(
            editable, num_rows="dynamic", use_container_width=True, key="editor_records",
            column_config=col_cfg if col_cfg else None
        )

        if st.button("💾 儲存全部修改"):
            # 轉型 & 計算命中率 & 規一化贏球欄
            edited["投籃數"] = pd.to_numeric(edited["投籃數"], errors="coerce").fillna(0).astype(int)
            edited["命中數"] = pd.to_numeric(edited["命中數"], errors="coerce").fillna(0).astype(int)
            edited["record_id"] = edited["record_id"].astype(str).str.strip()
            # 規一化 Y/N
            edited["是否贏球"] = normalize_win_col(edited["是否贏球"])
            edited["命中率"] = edited.apply(lambda r: calc_accuracy(r["投籃數"], r["命中數"]), axis=1)

            full = load_data()  # 重新讀最新資料
            full["record_id"] = full["record_id"].astype(str).str.strip()

            if pick:
                # ① 先把該球員原本的紀錄整批移除（讓刪除真正生效）
                full = full[full["球員"] != pick].copy()
                # ② 再把編輯後（保留下來）的紀錄加入回去
                edited["球員"] = pick  # 確保球員名一致
                full = pd.concat([full, edited], ignore_index=True, sort=False)
            else:
                # 沒挑球員：以保留的 record_id 為準，刪除不在 edited 的列
                keep_ids = set(edited["record_id"].dropna().tolist())
                full = full[full["record_id"].isin(keep_ids)].copy()
                # 更新保留列
                full = full.set_index("record_id")
                edited = edited.set_index("record_id")
                full.update(edited)
                full = full.reset_index()

            # 最後確保欄位順序與 Y/N 格式
            for c in RECORD_COLS:
                if c not in full.columns:
                    full[c] = pd.NA
            full["是否贏球"] = normalize_win_col(full["是否贏球"])
            full = full[RECORD_COLS]

            save_data(full)
            st.success("✅ 所有修改已儲存（包含刪除），且贏球欄統一為 Y/N。")

    # 修改球員資料（永遠顯示）
    st.subheader("🔧 修改球員基本資料")
    pdf = load_players_df()
    if not pdf.empty:
        opts = normalize_player_series(pdf["球員"]).dropna().unique().tolist()
        opts = [str(x) for x in opts]
        opts.sort()
        who = st.selectbox("選擇要修改的球員", opts, key="edit_player_select_batch")
        if who:
            row = pdf[pdf["球員"] == who].iloc[0]
            try:
                default_birthday = date.fromisoformat(str(row.get("生日",""))) if str(row.get("生日","")) else date.today()
            except Exception:
                default_birthday = date.today()

            def _f(v, d=0.0):
                try:
                    if pd.isna(v) or str(v).strip()=="":
                        return d
                    return float(v)
                except Exception:
                    return d
            h_def = _f(row.get("身高",0.0))
            w_def = _f(row.get("體重",0.0))
            gender_opts = ["男","女","其他"]
            g_def = str(row.get("性別","男")) if str(row.get("性別","")).strip() in gender_opts else "男"

            with st.form("edit_player_form_batch"):
                st.markdown(f"**姓名：{who}**")
                new_bd = st.date_input("生日", value=default_birthday, min_value=date(1925,1,1), max_value=date.today())
                new_h = st.number_input("身高 (cm)", min_value=0.0, step=1.0, value=h_def)
                new_g = st.selectbox("性別", gender_opts, index=gender_opts.index(g_def))
                new_w = st.number_input("體重 (kg)", min_value=0.0, step=1.0, value=w_def)
                new_photo = st.file_uploader("更新頭像（可選）", type=["jpg","jpeg","png"])
                ok = st.form_submit_button("保存球員修改")
                if ok:
                    pdf.loc[pdf["球員"] == who, "生日"] = new_bd.strftime("%Y-%m-%d")
                    t = date.today()
                    age = t.year - new_bd.year - ((t.month, t.day) < (new_bd.month, new_bd.day))
                    pdf.loc[pdf["球員"] == who, "年紀"] = str(age) if age >= 0 else ""
                    pdf.loc[pdf["球員"] == who, "身高"] = str(int(new_h)) if new_h else ""
                    pdf.loc[pdf["球員"] == who, "性別"] = new_g
                    pdf.loc[pdf["球員"] == who, "體重"] = str(int(new_w)) if new_w else ""
                    save_players_df(pdf)
                    if new_photo is not None:
                        (IMAGE_DIR / f"{who}.jpg").write_bytes(new_photo.read())
                    st.success("✅ 球員資料已更新！")
    else:
        st.write("尚未有球員登錄。")

    # 移除球員（永遠顯示）
    st.subheader("🗑️ 移除球員")
    pdf = load_players_df()
    if not pdf.empty:
        del_opts = normalize_player_series(pdf["球員"]).dropna().unique().tolist()
        del_opts = [str(x) for x in del_opts]
        del_opts.sort()
        del_names = st.multiselect("選擇要移除的球員", del_opts)
        if st.button("移除選定球員"):
            if del_names:
                remain = pdf[~pdf["球員"].isin(del_names)].copy()
                save_players_df(remain)
                for n in del_names:
                    p = IMAGE_DIR / f"{n}.jpg"
                    if p.exists():
                        p.unlink()
                st.success("已移除選定的球員：" + ", ".join(del_names))
    else:
        st.write("尚未有球員登錄。")

def download_data_section() -> None:
    st.header("📁 備份 / 下載資料")
    with open(DATA_FILE, "rb") as f:
        st.download_button("⬇️ 下載 CSV 備份", f, file_name="basketball_data.csv", mime="text/csv")

def player_management_section() -> None:
    st.header("👤 球員登錄")
    st.subheader("新增球員")
    with st.form("add_player_form"):
        name = st.text_input("姓名").strip()
        birthday = st.date_input("生日", min_value=date(1925,1,1), max_value=date.today())
        height = st.number_input("身高 (cm)", min_value=0.0, step=1.0)
        gender = st.selectbox("性別", ["男","女","其他"])
        weight = st.number_input("體重 (kg)", min_value=0.0, step=1.0)
        photo = st.file_uploader("上傳頭像（可選）", type=["jpg","jpeg","png"])
        ok = st.form_submit_button("新增球員")
        if ok:
            if not name:
                st.warning("請輸入球員姓名")
            elif name in get_player_names():
                st.warning("此球員已登錄")
            else:
                dfp = load_players_df()
                try:
                    birth_date = birthday
                    t = date.today()
                    age = t.year - birth_date.year - ((t.month, t.day) < (birth_date.month, birth_date.day))
                except Exception:
                    age = ""
                new = {
                    "球員": name,
                    "生日": birthday.strftime("%Y-%m-%d"),
                    "年紀": str(age) if age != "" else "",
                    "身高": str(int(height)) if height else "",
                    "性別": gender,
                    "體重": str(int(weight)) if weight else "",
                }
                dfp = pd.concat([dfp, pd.DataFrame([new])], ignore_index=True)
                save_players_df(dfp)
                if photo is not None:
                    (IMAGE_DIR / f"{name}.jpg").write_bytes(photo.read())
                st.success("✅ 成功新增球員！")
    st.info("如需修改或刪除球員，請前往『登錄修改』頁面。")

# ========== Main ==========
def main() -> None:
    st.set_page_config(page_title="🏀 籃球比賽紀錄系統", page_icon="🏀", layout="wide")
    if TEAM_LOGO_FILE.exists():
        st.sidebar.image(str(TEAM_LOGO_FILE), width=120)
    page = st.sidebar.radio("", ("球員登錄","新增紀錄","球員資訊","多人比較","登錄修改","備份資料"))

    df = load_data()  # always latest

    if page == "新增紀錄":
        add_record_section()
    elif page == "球員資訊":
        player_statistics_section(df)
    elif page == "多人比較":
        compare_players_section(df)
    elif page == "登錄修改":
        edit_records_section(df)
    elif page == "備份資料":
        download_data_section()
    elif page == "球員登錄":
        player_management_section()

if __name__ == "__main__":
    main()
