    players_df = pd.concat([players_df, pd.DataFrame([player_info])], ignore_index=True)
    players_df.to_csv(PLAYERS_FILE, index=False)