import streamlit as st
import pandas as pd
from pathlib import Path
import uuid
from datetime import date
from PIL import Image
import altair as alt

"""
A simplified and improved version of the basketball record keeping Streamlit app.

This refactoring breaks the app into discrete, well‑named functions, reuses shared
code and constants, and employs pathlib for file handling. It keeps all
original functionality—record creation with optional photo uploads, per‑player
statistics, multi‑player comparisons, batch editing of records, and data
download—while presenting the UI more cleanly.
"""

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
    if df.empty:
        return

    st.header("📊 單人統計")
    players = sorted(df["球員"].unique())
    selected_player = st.selectbox("選擇球員：", players)
    player_df = df[df["球員"] == selected_player]

    # Display the player's image if it exists
    img_path = IMAGE_DIR / f"{selected_player}.jpg"
    if img_path.exists():
        st.image(Image.open(img_path), width=120)

    # Aggregate statistics
    total_games = len(player_df)
    total_shots = player_df["投籃數"].sum()
    total_made = player_df["命中數"].sum()
    accuracy = calc_accuracy(total_shots, total_made)
    win_rate = (
        (player_df["是否贏球"] == "✅ 是").sum() / total_games * 100 if total_games else 0
    )

    st.write(f"比賽場數：{total_games}")
    st.write(f"總投籃：{total_shots}，命中：{total_made}")
    st.write(f"命中率：{accuracy:.2f}%，贏球率：{win_rate:.2f}%")

    # Prepare data for the line chart aggregated by date (ignoring hours)
    chart_data = (
        player_df.groupby("日期")["命中率"].mean().reset_index()
    )
    chart_data["日期"] = pd.to_datetime(chart_data["日期"])
    chart_data = chart_data.sort_values("日期")

    # Create the line chart with explicit axis titles (daily granularity)
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("日期:T", title="日期"),
            y=alt.Y("命中率:Q", title="命中率 (%)"),
        )
        .properties(width=600)
    )
    st.subheader("📈 命中率趨勢圖 (以日期為單位)")
    st.altair_chart(chart, use_container_width=True)


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
        chart_df["日期"] = pd.to_datetime(chart_df["日期"])
        chart_df = chart_df.sort_values("日期")
        # Draw a line for each player with a distinct color and tooltips
        chart = (
            alt.Chart(chart_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("日期:T", title="日期"),
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

    # We drop the calculated "命中率" column for editing to avoid user confusion.
    editable_df = df.drop(columns=["命中率"]).copy()
    edited_df = st.data_editor(
        editable_df, num_rows="dynamic", use_container_width=True, key="editor"
    )

    if st.button("💾 儲存全部修改"):
        # Recalculate the accuracy for each row
        edited_df["命中率"] = edited_df.apply(
            lambda r: calc_accuracy(r["投籃數"], r["命中數"]), axis=1
        )
        save_data(edited_df)
        st.success("✅ 所有修改已儲存")


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
    A section to register and manage players. Users can add new players
    with detailed information (photo, name, birthday, height, gender, weight)
    and remove existing players. Player details are stored in a CSV file
    and photos are saved in the images directory.
    """
    st.header("👤 球員登錄")

    # Form to add a new player
    st.subheader("新增球員")
    with st.form("add_player_form"):
        name = st.text_input("姓名").strip()
        birthday = st.date_input("生日", key="birthday")
        # Age input to allow manual age entry; will override computed age if provided
        age_input = st.number_input("年紀 (可自動計算)", min_value=0, step=1, value=0)
        height = st.number_input("身高 (cm)", min_value=0.0, step=1.0)
        gender = st.selectbox("性別", ["男", "女", "其他"])
        weight = st.number_input("體重 (kg)", min_value=0.0, step=1.0)
        photo = st.file_uploader("上傳頭像（可選）", type=["jpg", "jpeg", "png"], key="player_photo")
        submit_new = st.form_submit_button("新增球員")

        if submit_new:
            if not name:
                st.warning("請輸入球員姓名")
            elif name in get_player_names():
                st.warning("此球員已登錄")
            else:
                # Format birthday string and prepare other fields; compute age from input if provided
                birthday_str = birthday.strftime("%Y-%m-%d")
                age_str = str(int(age_input)) if age_input else ""
                height_str = str(int(height)) if height else ""
                weight_str = str(int(weight)) if weight else ""
                add_player_details(
                    name,
                    birthday=birthday_str,
                    age=age_str,
                    height=height_str,
                    gender=gender,
                    weight=weight_str,
                )
                if photo is not None:
                    img_path = IMAGE_DIR / f"{name}.jpg"
                    img_path.write_bytes(photo.read())
                st.success("✅ 成功新增球員！")

    # Section to remove players
    st.subheader("移除球員")
    players_df = load_players_df()
    if not players_df.empty:
        names = players_df["球員"].dropna().tolist()
        to_delete = st.multiselect("選擇要移除的球員", names, key="delete_players")
        if st.button("移除選定球員"):
            if to_delete:
                # Remove selected players from the DataFrame
                remaining_df = players_df[~players_df["球員"].isin(to_delete)].copy()
                remaining_df.to_csv(PLAYERS_FILE, index=False)
                # Remove headshot files for deleted players
                for del_name in to_delete:
                    img_path = IMAGE_DIR / f"{del_name}.jpg"
                    if img_path.exists():
                        img_path.unlink()
                st.success("已移除選定的球員：" + ", ".join(to_delete))
    else:
        st.write("尚未有球員登錄。")


def main() -> None:
    """
    The primary entry point for the Streamlit app. Provides a sidebar menu
    for navigating between sections (add records, single-player stats,
    multi-player trend comparison, batch editing, and data backup).
    Each page loads the latest data when displayed.
    """
    # Configure the page (title, icon, and layout)
    st.set_page_config(
        page_title="🏀 籃球比賽紀錄系統", page_icon="🏀", layout="wide"
    )
    # Display team logo (if available) alongside the title at the top of the page
    if TEAM_LOGO_FILE.exists():
        logo_col, title_col = st.columns([1, 8])
        with logo_col:
            # Display the logo with a fixed width
            st.image(str(TEAM_LOGO_FILE), width=60)
        with title_col:
            st.markdown(
                "<h1 style='padding-left: 0.5rem;'>🏀 籃球比賽紀錄系統</h1>",
                unsafe_allow_html=True,
            )
    else:
        st.title("🏀 籃球比賽紀錄系統")

    # Sidebar for navigation
    st.sidebar.title("功能選單")
    page = st.sidebar.radio(
        "選擇功能",
        (
            "球員登錄",  # put player registration first
            "新增紀錄",
            "單人統計",
            "趨勢比較",
            "批次修改",
            "備份資料",
        ),
    )

    # Always work with the most up‑to‑date data
    df = load_data()

    # Render the appropriate section based on user selection
    if page == "新增紀錄":
        add_record_section()
    elif page == "單人統計":
        player_statistics_section(df)
    elif page == "趨勢比較":
        compare_players_section(df)
    elif page == "批次修改":
        edit_records_section(df)
    elif page == "備份資料":
        download_data_section()
    elif page == "球員登錄":
        player_management_section()


if __name__ == "__main__":
    main()
