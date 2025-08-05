
import streamlit as st
import pandas as pd
from pathlib import Path
import uuid
from datetime import date
from PIL import Image
import altair as alt


# Define constants for the data file and image directory using pathlib
DATA_FILE = Path("data.csv")
IMAGE_DIR = Path("images")

# Path to store registered players and their details.
PLAYERS_FILE = Path("players.csv")

# Define the columns for the players file
PLAYERS_COLUMNS = ["球員", "生日", "年紀", "身高", "性別", "體重"]

# Ensure the players file exists and has all required columns
if not PLAYERS_FILE.exists():
    pd.DataFrame(columns=PLAYERS_COLUMNS).to_csv(PLAYERS_FILE, index=False)
else:
    # If the file exists but lacks columns, add them
    existing_df = pd.read_csv(PLAYERS_FILE)
    missing_cols = [col for col in PLAYERS_COLUMNS if col not in existing_df.columns]
    if missing_cols:
        for col in missing_cols:
            existing_df[col] = ""
        existing_df.to_csv(PLAYERS_FILE, index=False)

# Define a path for a team logo. Place your logo file at this path
TEAM_LOGO_FILE = IMAGE_DIR / "team_logo.png"

# Ensure the image directory exists; if the data file is missing create an empty CSV
IMAGE_DIR.mkdir(exist_ok=True)
if not DATA_FILE.exists():
    empty_df = pd.DataFrame(
        columns=["record_id", "日期", "球員", "投籃數", "命中數", "是否贏球", "命中率"]
    )
    empty_df.to_csv(DATA_FILE, index=False)


def load_data() -> pd.DataFrame:
    """
    Load the records from the CSV file into a DataFrame.

    Returns:
        pd.DataFrame: The current basketball records.
    """
    return pd.read_csv(DATA_FILE)


# Player management helpers
def load_players_df() -> pd.DataFrame:
    """
    Load the registered players DataFrame from the players CSV.

    Returns:
        pd.DataFrame: DataFrame containing player details.
    """
    return pd.read_csv(PLAYERS_FILE)


def get_player_names() -> list:
    """
    Get a list of all registered player names.

    Returns:
        list[str]: List of player names.
    """
    dfp = load_players_df()
    return dfp["球員"].dropna().astype(str).tolist()


def load_players() -> list:
    """
    Alias for backward compatibility. Returns the list of player names.
    """
    return get_player_names()


def add_player(name: str) -> None:
    """
    Register a new player by appending their name to the players CSV,
    ensuring no duplicates.

    Args:
        name (str): The player's name.
    """
    # Deprecated: this function now accepts additional fields through add_player_details.
    name = name.strip()
    if not name:
        return
    current_players = set(get_player_names())
    if name in current_players:
        return
    # Append a new player with empty details
    df_existing = load_players_df()
    new_record = {col: "" for col in PLAYERS_COLUMNS}
    new_record["球員"] = name
    df_new = pd.concat([df_existing, pd.DataFrame([new_record])], ignore_index=True)
    df_new.to_csv(PLAYERS_FILE, index=False)


def add_player_details(name: str, birthday: str = "", age: str = "", height: str = "",
                       gender: str = "", weight: str = "") -> None:
    """
    Register a new player with full details, ensuring no duplicates.

    Args:
        name (str): Player's name.
        birthday (str): Birthday in YYYY-MM-DD format.
        age (str): Age (will be computed from birthday if empty).
        height (str): Height in cm.
        gender (str): Gender description.
        weight (str): Weight in kg.
    """
    name = name.strip()
    if not name:
        return
    current_players = set(get_player_names())
    if name in current_players:
        return
    df_existing = load_players_df()
    # If age is empty and birthday provided, compute age
    if not age and birthday:
        try:
            birth_date = pd.to_datetime(birthday)
            today = pd.to_datetime(date.today())
            age = str(today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day)))
        except Exception:
            age = ""
    new_record = {
        "球員": name,
        "生日": birthday,
        "年紀": age,
        "身高": height,
        "性別": gender,
        "體重": weight,
    }
    df_new = pd.concat([df_existing, pd.DataFrame([new_record])], ignore_index=True)
    df_new.to_csv(PLAYERS_FILE, index=False)


def save_data(df: pd.DataFrame) -> None:
    """
    Save the DataFrame back to disk.

    Args:
        df (pd.DataFrame): Data to persist.
    """
    df.to_csv(DATA_FILE, index=False)


def calc_accuracy(shots: float, made: float) -> float:
    """
    Compute a shooting percentage as a percentage value. If shots is zero,
    return 0 to avoid division by zero.

    Args:
        shots (float): Number of shot attempts.
        made (float): Number of successful shots.

    Returns:
        float: Shooting accuracy as a percentage rounded to two decimals.
    """
    return round((made / shots) * 100, 2) if shots else 0.0


# Medal computation helper
def compute_monthly_medals(df: pd.DataFrame) -> dict:
    """
    Compute monthly medals for a given player's records based on their shooting accuracy.

    A bronze medal is awarded for a monthly accuracy between 35% and 49% (inclusive),
    silver for 50%–59%, and gold for 60% or higher.

    Args:
        df (pd.DataFrame): Records for a single player.

    Returns:
        dict: A dictionary with keys '金', '銀', '銅' mapping to the count of medals earned.
    """
    medals = {"金": 0, "銀": 0, "銅": 0}
    if df.empty:
        return medals
    # Copy the DataFrame to avoid modifying the original
    tmp = df.copy()
    # Convert the date column to datetime and extract the month period
    tmp["日期_dt"] = pd.to_datetime(tmp["日期"])
    tmp["month"] = tmp["日期_dt"].dt.to_period("M")
    # Aggregate total shots and made per month
    aggregated = tmp.groupby("month").agg({"投籃數": "sum", "命中數": "sum"})
    # Compute monthly accuracy
    aggregated["accuracy"] = aggregated["命中數"] / aggregated["投籃數"] * 100
    # Determine medal counts based on accuracy thresholds
    for acc in aggregated["accuracy"]:
        if acc >= 60:
            medals["金"] += 1
        elif acc >= 50:
            medals["銀"] += 1
        elif acc >= 35:
            medals["銅"] += 1
    return medals


def add_record_section() -> None:
    """
    Render the form for adding a new game record. Validates inputs,
    computes the accuracy, saves the new record, and optionally writes
    the uploaded player image to disk.
    """
    st.header("📥 新增紀錄")
    players = load_players()
    if not players:
        st.warning("尚未有球員登錄，請先到『球員登錄』頁面登錄球員。")
        return
    with st.form("add_record"):
        col1, col2 = st.columns(2)
        with col1:
            game_date = st.date_input("比賽日期", value=date.today())
        with col2:
            # Select from registered players
            player = st.selectbox("選擇球員", players)
        
        shots = st.number_input("投籃次數", min_value=0, step=1)
        made = st.number_input("命中次數", min_value=0, step=1)
        win = st.selectbox("這場是否贏球？", ["✅ 是", "❌ 否"])
        submit = st.form_submit_button("新增紀錄")

        if submit:
            # Validate user inputs
            if made > shots:
                st.warning("命中不能大於投籃")
            else:
                # Compute accuracy and build the new record
                accuracy = calc_accuracy(shots, made)
                new_record = {
                    "record_id": str(uuid.uuid4()),
                    "日期": game_date.strftime("%Y-%m-%d"),
                    "球員": player,
                    "投籃數": shots,
                    "命中數": made,
                    "是否贏球": win,
                    "命中率": accuracy,
                }
                # Load current data, append the new record, and save
                df = load_data()
                df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
                save_data(df)
                st.success("✅ 紀錄新增成功！")


def player_statistics_section(df: pd.DataFrame) -> None:
    """
    Display statistics and a trend chart for a single player, including
    the player's photo if available. This section will only show when
    there is at least one record.

    Args:
        df (pd.DataFrame): The full record DataFrame.
    """
    st.header("📊 球員資訊")
    registered_players = sorted(get_player_names())
    if not registered_players:
        st.write("尚未有球員登錄。")
        return
    
    selected_player = st.selectbox("選擇球員：", registered_players)

    # Use columns to display player's image and basic info side-by-side
    col_img, col_info = st.columns([1, 2])
    with col_img:
        img_path = IMAGE_DIR / f"{selected_player}.jpg"
        if img_path.exists():
            st.image(Image.open(img_path), width=120)
        else:
            st.write("無頭像")
    
    with col_info:
        players_df = load_players_df()
        details_df = players_df[players_df["球員"] == selected_player]
        if not details_df.empty:
            info = details_df.iloc[0]
            st.subheader(f"{info['球員']}")
            
            def display_value(val, suffix=""):
                if pd.isna(val) or str(val).strip() == "":
                    return "未填寫"
                return f"{val}{suffix}"
            
            st.markdown(f"**生日**：{display_value(info['生日'])}")
            st.markdown(f"**年紀**：{display_value(info['年紀'])}")
            st.markdown(f"**身高**：{display_value(info['身高'], ' cm')}")
            st.markdown(f"**性別**：{display_value(info['性別'])}")
            st.markdown(f"**體重**：{display_value(info['體重'], ' kg')}")

    # Display key metrics
    st.subheader("數據總覽")
    player_df = df[df["球員"] == selected_player] if not df.empty else pd.DataFrame()
    total_games = len(player_df)
    total_shots = player_df["投籃數"].sum() if not player_df.empty else 0
    total_made = player_df["命中數"].sum() if not player_df.empty else 0
    accuracy = calc_accuracy(total_shots, total_made) if not player_df.empty else 0
    win_rate = ((player_df["是否贏球"] == "✅ 是").sum() / total_games * 100) if total_games else 0

    col_stats_1, col_stats_2, col_stats_3, col_stats_4 = st.columns(4)
    with col_stats_1:
        st.metric("比賽場數", total_games)
    with col_stats_2:
        st.metric("總投籃 / 命中", f"{total_shots} / {total_made}")
    with col_stats_3:
        st.metric("命中率", f"{accuracy:.2f}%")
    with col_stats_4:
        st.metric("贏球率", f"{win_rate:.2f}%")

    # Display medal statistics
    medals = compute_monthly_medals(player_df)
    st.subheader("🏅 勳章統計")
    if any(medals.values()):
        col_medals_1, col_medals_2, col_medals_3 = st.columns(3)
        with col_medals_1:
            st.metric("金勳章", medals['金'])
        with col_medals_2:
            st.metric("銀勳章", medals['銀'])
        with col_medals_3:
            st.metric("銅勳章", medals['銅'])
    else:
        st.write("尚未獲得任何勳章")
        
    # Display line chart
    if not player_df.empty:
        st.subheader("📈 命中率趨勢圖 (以日期為單位)")
        # Aggregate and reindex by the full date range
        aggregated = player_df.groupby("日期")["命中率"].mean().reset_index()
        aggregated["日期"] = pd.to_datetime(aggregated["日期"]).dt.date
        start_date = aggregated["日期"].min()
        end_date = aggregated["日期"].max()
        full_range = pd.date_range(start=start_date, end=end_date)
        chart_data = (
            aggregated.set_index("日期").reindex(full_range).rename_axis("日期").reset_index()
        )
        chart_data.rename(columns={"命中率": "命中率"}, inplace=True)
        chart_data["日期"] = pd.to_datetime(chart_data["日期"])
        chart = (
            alt.Chart(chart_data)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "日期:T",
                    title="日期",
                    scale=alt.Scale(domain=[pd.to_datetime(start_date), pd.to_datetime(end_date)]),
                ),
                y=alt.Y("命中率:Q", title="命中率 (%)"),
            )
            .properties(width=600)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("該球員尚無比賽紀錄。")


def compare_players_section(df: pd.DataFrame) -> None:
    """
    Render a bar chart that compares the average shooting percentage
    across multiple players. This section will only display when
    at least two distinct players exist in the data.

    Args:
        df (pd.DataFrame): The full record DataFrame.
    """
    if df["球員"].nunique() < 2:
        return

    st.header("📊 多人命中率比較（趨勢圖）")
    players = sorted(df["球員"].unique())
    selected_players = st.multiselect("選擇球員進行比較：", players)

    if selected_players:
        # Prepare data for a multi-line trend chart aggregated by date for each player
        chart_df = (
            df[df["球員"].isin(selected_players)]
            .groupby(["球員", "日期"])["命中率"]
            .mean()
            .reset_index()
        )
        # Convert date strings to date objects for range computation
        chart_df["日期"] = pd.to_datetime(chart_df["日期"]).dt.date
        # Determine the overall date range across selected players
        start_date = chart_df["日期"].min()
        end_date = chart_df["日期"].max()
        full_range = pd.date_range(start=start_date, end=end_date)
        # Build a complete DataFrame with all player/date combinations
        idx = pd.MultiIndex.from_product([selected_players, full_range], names=["球員", "日期"])
        full_df = pd.DataFrame(index=idx).reset_index()
        # Merge with actual data
        merged_df = full_df.merge(chart_df, how="left", on=["球員", "日期"])
        # Convert 日期 back to datetime for Altair
        merged_df["日期"] = pd.to_datetime(merged_df["日期"])
        # Plot multi-line chart with explicit domain across full range
        chart = (
            alt.Chart(merged_df)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "日期:T",
                    title="日期",
                    scale=alt.Scale(domain=[pd.to_datetime(start_date), pd.to_datetime(end_date)]),
                ),
                y=alt.Y("命中率:Q", title="命中率 (%)"),
                color=alt.Color("球員:N", title="球員"),
                tooltip=["日期:T", "球員:N", "命中率:Q"],
            )
            .properties(width=600)
        )
        st.altair_chart(chart, use_container_width=True)


def edit_records_section(df: pd.DataFrame) -> None:
    """
    Present an editable table of existing records. Upon saving,
    recalculate the accuracy for each record and persist the changes.

    Args:
        df (pd.DataFrame): The full record DataFrame.
    """
    st.header("✏️ 批次修改紀錄")
    if df.empty:
        st.info("沒有紀錄可修改")
        return

    players = sorted(df["球員"].unique())
    selected_player = st.selectbox("選擇球員進行修改：", players)
    df_filtered = df[df["球員"] == selected_player] if selected_player else df

    # Drop the calculated "命中率" column for editing to avoid user confusion.
    editable_df = df_filtered.drop(columns=["命中率"]).copy()
    edited_df = st.data_editor(
        editable_df, num_rows="dynamic", use_container_width=True, key="editor_records"
    )

    if st.button("💾 儲存全部修改"):
        # Recalculate the accuracy for each row in the edited subset
        edited_df["命中率"] = edited_df.apply(
            lambda r: calc_accuracy(r["投籃數"], r["命中數"]), axis=1
        )
        # Load the full data to update it
        full_df = df.copy()
        # Replace the rows corresponding to the edited player's records
        for _, row in edited_df.iterrows():
            full_df.loc[full_df["record_id"] == row["record_id"], full_df.columns] = row
        # Save the updated full data
        save_data(full_df)
        st.success("✅ 所有修改已儲存")

    # --- Player management: edit basic information ---
    st.subheader("🔧 修改球員基本資料")
    players_df = load_players_df()
    if not players_df.empty:
        edit_name = st.selectbox(
            "選擇要修改的球員", players_df["球員"].dropna().astype(str).tolist(), key="edit_player_select_batch"
        )
        if edit_name:
            current_row = players_df[players_df["球員"] == edit_name].iloc[0]
            try:
                default_birthday = date.fromisoformat(str(current_row["生日"])) if str(current_row["生日"]) else date.today()
            except Exception:
                default_birthday = date.today()
            if pd.notna(current_row["身高"]) and str(current_row["身高"]).strip():
                try:
                    default_height = float(current_row["身高"])
                    if pd.isna(default_height):
                        default_height = 0.0
                except Exception:
                    default_height = 0.0
            else:
                default_height = 0.0
            if pd.notna(current_row["體重"]) and str(current_row["體重"]).strip():
                try:
                    default_weight = float(current_row["體重"])
                    if pd.isna(default_weight):
                        default_weight = 0.0
                except Exception:
                    default_weight = 0.0
            else:
                default_weight = 0.0
            gender_options = ["男", "女", "其他"]
            if pd.notna(current_row["性別"]) and str(current_row["性別"]).strip() in gender_options:
                default_gender = str(current_row["性別"]).strip()
            else:
                default_gender = gender_options[0]
            default_gender_index = gender_options.index(default_gender) if default_gender in gender_options else 0
            with st.form("edit_player_form_batch"):
                st.markdown(f"**姓名：{edit_name}**")
                new_birthday = st.date_input(
                    "生日",
                    value=default_birthday,
                    key="edit_birthday_batch",
                    min_value=date(1925, 1, 1),
                    max_value=date.today(),
                )
                new_height = st.number_input(
                    "身高 (cm)", min_value=0.0, step=1.0, value=default_height, key="edit_height_batch"
                )
                new_gender = st.selectbox(
                    "性別", gender_options, index=default_gender_index, key="edit_gender_batch"
                )
                new_weight = st.number_input(
                    "體重 (kg)", min_value=0.0, step=1.0, value=default_weight, key="edit_weight_batch"
                )
                new_photo = st.file_uploader(
                    "更新頭像（可選）", type=["jpg", "jpeg", "png"], key="edit_player_photo_batch"
                )
                submit_edit = st.form_submit_button("保存球員修改")
                if submit_edit:
                    players_df.loc[players_df["球員"] == edit_name, "生日"] = new_birthday.strftime(
                        "%Y-%m-%d"
                    )
                    today_date = date.today()
                    age_value = today_date.year - new_birthday.year - (
                        (today_date.month, today_date.day) < (new_birthday.month, new_birthday.day)
                    )
                    players_df.loc[players_df["球員"] == edit_name, "年紀"] = str(age_value) if age_value else ""
                    players_df.loc[players_df["球員"] == edit_name, "身高"] = (
                        str(int(new_height)) if new_height else ""
                    )
                    players_df.loc[players_df["球員"] == edit_name, "性別"] = new_gender
                    players_df.loc[players_df["球員"] == edit_name, "體重"] = (
                        str(int(new_weight)) if new_weight else ""
                    )
                    players_df.to_csv(PLAYERS_FILE, index=False)
                    if new_photo is not None:
                        img_path = IMAGE_DIR / f"{edit_name}.jpg"
                        img_path.write_bytes(new_photo.read())
                    st.success("✅ 球員資料已更新！")
    else:
        st.write("尚未有球員登錄。")

    # --- Player management: remove players ---
    st.subheader("🗑️ 移除球員")
    players_df = load_players_df()
    if not players_df.empty:
        del_names = st.multiselect(
            "選擇要移除的球員", players_df["球員"].dropna().astype(str).tolist(), key="delete_players_batch"
        )
        if st.button("移除選定球員", key="delete_players_button_batch"):
            if del_names:
                remaining_df = players_df[~players_df["球員"].isin(del_names)].copy()
                remaining_df.to_csv(PLAYERS_FILE, index=False)
                for del_name in del_names:
                    img_path = IMAGE_DIR / f"{del_name}.jpg"
                    if img_path.exists():
                        img_path.unlink()
                st.success("已移除選定的球員：" + ", ".join(del_names))
    else:
        st.write("尚未有球員登錄。")


def download_data_section() -> None:
    """
    Provide a button for users to download the current CSV data.
    """
    st.header("📁 備份 / 下載資料")
    with open(DATA_FILE, "rb") as f:
        st.download_button(
            "⬇️ 下載 CSV 備份", f, file_name="basketball_data.csv", mime="text/csv"
        )


def player_management_section() -> None:
    """
    A section to register and manage players.
    """
    st.header("👤 球員登錄")

    st.subheader("新增球員")
    with st.form("add_player_form"):
        name = st.text_input("姓名").strip()
        col1, col2, col3 = st.columns(3)
        with col1:
            birthday = st.date_input("生日", key="birthday", min_value=date(1925, 1, 1), max_value=date.today())
        with col2:
            height = st.number_input("身高 (cm)", min_value=0.0, step=1.0)
        with col3:
            weight = st.number_input("體重 (kg)", min_value=0.0, step=1.0)
        
        gender = st.selectbox("性別", ["男", "女", "其他"])
        photo = st.file_uploader("上傳頭像（可選）", type=["jpg", "jpeg", "png"], key="player_photo")
        submit_new = st.form_submit_button("新增球員")

        if submit_new:
            if not name:
                st.warning("請輸入球員姓名")
            elif name in get_player_names():
                st.warning("此球員已登錄")
            else:
                birthday_str = birthday.strftime("%Y-%m-%d")
                height_str = str(int(height)) if height else ""
                weight_str = str(int(weight)) if weight else ""
                add_player_details(
                    name,
                    birthday=birthday_str,
                    age="",
                    height=height_str,
                    gender=gender,
                    weight=weight_str,
                )
                if photo is not None:
                    img_path = IMAGE_DIR / f"{name}.jpg"
                    img_path.write_bytes(photo.read())
                st.success("✅ 成功新增球員！")
    
    st.info("如需修改或刪除球員，請前往『批次修改』頁面。")
    return


def main() -> None:
    """
    The primary entry point for the Streamlit app. Provides a sidebar menu
    for navigating between sections (add records, single-player stats,
    multi-player trend comparison, batch editing, and data backup).
    Each page loads the latest data when displayed.
    """
    st.set_page_config(
        page_title="🏀 籃球比賽紀錄系統", page_icon="🏀", layout="wide"
    )

    st.markdown(
        """
        <style>
        /* Import a mechanical-style font (Orbitron) from Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');

        /* Set global background and text colors for a dark theme */
        html, body, .stApp {
            background-color: #0a192f;
            color: #c8d4e3;
        }

        /* Style the sidebar with a darker shade and a blue accent border */
        [data-testid="stSidebar"] {
            background-color: #112240 !important;
            border-right: 2px solid #00BFFF !important;
        }

        /* Increase the sidebar menu text size, apply mechanical font and accent color */
        [data-testid="stSidebar"] label {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 32px !important;
            font-weight: 600 !important;
            letter-spacing: 1px;
            color: #00BFFF !important;
        }
        
        /* Style the st.radio in sidebar */
        .st-emotion-cache-1pxx76s .st-bb .st-bg:hover,
        .st-emotion-cache-1pxx76s .st-bb .st-bg:focus-visible {
            background-color: #00BFFF !important;
            color: #112240 !important;
        }
        .st-emotion-cache-1pxx76s .st-bb .st-bg {
            background-color: #112240 !important;
        }


        /* Input focus glow effect with accent color */
        input:focus, textarea:focus, select:focus {
            border-color: #00BFFF !important;
            box-shadow: 0 0 6px #00BFFF !important;
            outline: none !important;
        }

        /* Change st.info and st.warning colors to fit the theme */
        .stAlert {
            color: #c8d4e3 !important;
            background-color: #2a3c5a !important; /* Dark blue background */
            border-left: 5px solid #00BFFF !important;
        }
        
        .stAlert [data-testid="stAlertContent"] {
            color: #c8d4e3 !important; /* Text color */
        }
        
        /* Specific styles for different alert types */
        .st-emotion-cache-1tq993s { /* .stAlert.info */
            background-color: #112240 !important;
            border-left-color: #00BFFF !important;
        }
        .st-emotion-cache-1p6f5j7 { /* .stAlert.warning */
            background-color: #2a3c5a !important;
            border-left-color: #ffcc00 !important;
        }
        
        /* Improve button style */
        .st-emotion-cache-1x4m24e button {
            background-color: #00BFFF !important;
            color: #0a192f !important;
            border: 2px solid #00BFFF !important;
            font-weight: bold;
            transition: all 0.3s ease-in-out;
        }
        .st-emotion-cache-1x4m24e button:hover {
            background-color: transparent !important;
            color: #00BFFF !important;
        }
        
        /* Streamlit metric component style */
        .stMetric .st-emotion-cache-v06144 { /* Metric value */
            font-size: 2rem !important;
            color: #00BFFF !important;
            font-family: 'Orbitron', sans-serif !important;
        }
        .stMetric .st-emotion-cache-121p55b { /* Metric label */
            font-size: 1rem !important;
            color: #c8d4e3 !important;
            font-weight: bold;
        }
        
        /* Enhance headers */
        h1, h2, h3, h4 {
            color: #00BFFF !important;
            font-family: 'Orbitron', sans-serif !important;
        }
        
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # --- Sidebar for navigation ---
    st.sidebar.image(str(TEAM_LOGO_FILE), width=150)
    st.sidebar.title("🏀 紀錄系統")

    menu_options = {
        "新增紀錄": "add_record_section",
        "球員資訊": "player_statistics_section",
        "多人比較": "compare_players_section",
        "批次修改": "edit_records_section",
        "球員登錄": "player_management_section",
        "下載備份": "download_data_section",
    }
    selection = st.sidebar.radio("選擇功能：", list(menu_options.keys()))

    # --- Main content area based on selection ---
    df = load_data()
    # Use a loading spinner for a better user experience
    with st.spinner("載入中..."):
        if selection == "新增紀錄":
            add_record_section()
        elif selection == "球員資訊":
            player_statistics_section(df)
        elif selection == "多人比較":
            compare_players_section(df)
        elif selection == "批次修改":
            edit_records_section(df)
        elif selection == "球員登錄":
            player_management_section()
        elif selection == "下載備份":
            download_data_section()


if __name__ == "__main__":
    main()

```