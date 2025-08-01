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
    with st.form("add_record"):
        col1, col2 = st.columns(2)
        with col1:
            game_date = st.date_input("比賽日期", value=date.today())
        with col2:
            player = st.text_input("球員姓名").strip()
        shots = st.number_input("投籃次數", min_value=0, step=1)
        made = st.number_input("命中次數", min_value=0, step=1)
        win = st.selectbox("這場是否贏球？", ["✅ 是", "❌ 否"])
        uploaded_file = st.file_uploader("上傳球員頭像（可選）", type=["jpg", "jpeg", "png"])
        submit = st.form_submit_button("新增紀錄")

        if submit:
            # Validate user inputs
            if not player:
                st.warning("請輸入球員姓名")
            elif made > shots:
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
                # Save the uploaded image if provided
                if uploaded_file:
                    image_path = IMAGE_DIR / f"{player}.jpg"
                    image_path.write_bytes(uploaded_file.read())
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

    # Prepare data for the line chart
    chart_data = player_df[["日期", "命中率"]].copy()
    chart_data["日期"] = pd.to_datetime(chart_data["日期"])
    chart_data = chart_data.sort_values("日期")

    # Create the line chart with explicit axis titles
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("日期:T", title="日期"),
            y=alt.Y("命中率:Q", title="命中率 (%)"),
        )
        .properties(width=600)
    )
    st.subheader("📈 命中率趨勢圖")
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

    st.header("📊 多人命中率比較")
    players = sorted(df["球員"].unique())
    selected_players = st.multiselect("選擇球員進行比較：", players)

    if selected_players:
        compare_df = df[df["球員"].isin(selected_players)]
        avg_df = compare_df.groupby("球員")["命中率"].mean().reset_index()
        # Create a bar chart with axis titles
        chart = (
            alt.Chart(avg_df)
            .mark_bar()
            .encode(
                x=alt.X("球員:N", title="球員"),
                y=alt.Y("命中率:Q", title="平均命中率 (%)"),
                color="球員:N",
            )
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


def main() -> None:
    """
    The primary entry point for the Streamlit app. Responsible for
    orchestrating each UI section and refreshing data after new records
    are added or edits are saved.
    """
    st.title("🏀 籃球比賽紀錄系統 App")
    add_record_section()
    # Reload data after potentially adding new records
    df = load_data()
    player_statistics_section(df)
    compare_players_section(df)
    edit_records_section(df)
    download_data_section()


if __name__ == "__main__":
    main()
