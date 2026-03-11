# ============================
# ======== BLOCK 1 ===========
# ===== START OF BLOCK 1 =====
# ============================

import streamlit as st
from supabase import create_client
from datetime import datetime
import json
import pandas as pd

# ---------------------------------------------------------
# Supabase Connection
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

st.set_page_config(page_title="Poker Night Tracker", layout="centered")


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def load_players():
    response = supabase.table("players").select("*").order("name").execute()
    return response.data if response.data else []


def add_player(name):
    supabase.table("players").insert({"name": name}).execute()


def load_sessions():
    response = (
        supabase.table("sessions")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data if response.data else []


def create_session(name, players):
    response = (
        supabase.table("sessions")
        .insert({"name": name, "players": players})
        .execute()
    )
    return response.data[0]


def update_session_players(session_id, players):
    supabase.table("sessions").update({"players": players}).eq("id", session_id).execute()


def load_hands_for_session(session_name):
    response = (
        supabase.table("hands")
        .select("*")
        .eq("game_name", session_name)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data if response.data else []


# ---------------------------------------------------------
# Checkbox Grid Helper
# ---------------------------------------------------------
def checkbox_grid(label, options, key_prefix, session_id, columns=2, prechecked=None):
    st.write(f"### {label}")
    selected = []

    if prechecked is None:
        prechecked = []

    rows = (len(options) + columns - 1) // columns
    idx = 0

    for _ in range(rows):
        cols = st.columns(columns)
        for c in range(columns):
            if idx < len(options):
                name = options[idx]
                key = f"{key_prefix}_{session_id}_{label}_{name}"
                checked = cols[c].checkbox(name, key=key, value=(name in prechecked))
                if checked:
                    selected.append(name)
                idx += 1

    return selected


# ---------------------------------------------------------
# Load Base Data
# ---------------------------------------------------------
players = load_players()
player_names = [p["name"] for p in players]

sessions = load_sessions()
session_names = [s["name"] for s in sessions]

CREATE_NEW = "➕ Create New Session…"
session_dropdown_options = session_names + [CREATE_NEW]


# ---------------------------------------------------------
# Remember Last Session
# ---------------------------------------------------------
if "active_session_id" not in st.session_state:
    st.session_state["active_session_id"] = None


# ---------------------------------------------------------
# 1. Session Selector
# ---------------------------------------------------------


st.header("Game Session")

if st.session_state["active_session_id"]:
    active_session = next(
        (s for s in sessions if s["id"] == st.session_state["active_session_id"]),
        None
    )
    default_name = active_session["name"] if active_session else None
else:
    default_name = None

selected_session_name = st.selectbox(
    "Select or Create New Session",
    session_dropdown_options,
    index=session_dropdown_options.index(default_name)
    if default_name in session_dropdown_options else 0,
)


# ---------------------------------------------------------
# Create New Session Flow
# ---------------------------------------------------------
if selected_session_name == CREATE_NEW:

    st.subheader("Create New Session")

    suggested_name = f"{datetime.now():%B %Y} Poker Night"
    new_session_name = st.text_input("Session Name", value=suggested_name)

    new_session_players = st.multiselect(
        "Select players for this session:",
        options=player_names,
    )

    if st.button("Create Session", type="primary"):
        if new_session_name.strip() and new_session_players:
            created = create_session(new_session_name.strip(), new_session_players)
            st.session_state["active_session_id"] = created["id"]
            st.success("Session created!")
            st.rerun()

    st.stop()


# ---------------------------------------------------------
# Load Selected Session
# ---------------------------------------------------------
active_session = next((s for s in sessions if s["name"] == selected_session_name), None)

if active_session:
    st.session_state["active_session_id"] = active_session["id"]

    raw_players = active_session["players"]
    players_in_game = raw_players if isinstance(raw_players, list) else json.loads(raw_players)
else:
    players_in_game = []


# ---------------------------------------------------------
# Edit Session Players
# ---------------------------------------------------------
with st.expander("Edit Session Players"):

    edited_players = st.multiselect(
        "Players in this session:",
        options=player_names,
        default=players_in_game,
        key=f"edit_players_{active_session['id']}"
    )

    st.markdown("---")

    st.subheader("Add New Player")
    new_player_name = st.text_input("New Player Name", key=f"new_player_{active_session['id']}")

    if st.button("Add Player to List", key=f"add_player_btn_{active_session['id']}"):
        cleaned = new_player_name.strip()

        if cleaned:
            if cleaned in player_names:
                st.warning(f"{cleaned} already exists in the global player list.")
            else:
                add_player(cleaned)
                st.success(f"Added {cleaned}")
                st.rerun()

    st.markdown("---")

    if st.button("Save Session Players", key=f"save_players_{active_session['id']}"):
        update_session_players(active_session["id"], edited_players)
        st.success("Session players updated!")
        st.rerun()


# ---------------------------------------------------------
# 2. Determine Alive Players (for NEW hands)
# ---------------------------------------------------------
hands = load_hands_for_session(active_session["name"])

eliminated_so_far = set()
chronological = list(reversed(hands))  # oldest → newest

for h in chronological:
    eliminated = h.get("eliminated_player") or []
    if isinstance(eliminated, str):
        eliminated = [eliminated]
    for p in eliminated:
        eliminated_so_far.add(p)

alive_players = [p for p in players_in_game if p not in eliminated_so_far]


# ---------------------------------------------------------
# 3. Log a Hand
# ---------------------------------------------------------
with st.expander("Log a Hand", expanded=False):

    if not active_session:
        st.info("Select or create a session to begin.")
        st.stop()

    if not alive_players:
        st.info("All players have been eliminated.")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Winner")
        winner = st.radio("", alive_players, key=f"winner_radio_{active_session['id']}")

    with col2:
        st.subheader("Street")
        streets = ["Preflop", "Flop", "Turn", "River"]
        street = st.radio("", streets, key=f"street_radio_{active_session['id']}")

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Hand Type")

        if street != "River":
            allowed_hand_types = ["No Showdown"]
        else:
            allowed_hand_types = [
                "High Card", "Pair", "Two Pair", "Trips", "Straight",
                "Flush", "Full House", "Quads", "Straight Flush"
            ]

        hand_type = st.radio(
            "",
            allowed_hand_types,
            key=f"handtype_radio_{active_session['id']}"
        )

    with col4:
        st.subheader("Pot Size")
        pot_sizes = ["S", "M", "L"]
        pot_size = st.radio("", pot_sizes, key=f"potsize_radio_{active_session['id']}")

    showdown_losers = []
    if street == "River" and hand_type != "No Showdown":
        showdown_options = [p for p in alive_players if p != winner]
        showdown_losers = checkbox_grid(
            "Showdown Losers",
            showdown_options,
            key_prefix="losers",
            session_id=active_session["id"],
            columns=2
        )

    all_in = False
    eliminated_players = []

    if street == "River":
        st.subheader("All-In")
        all_in = st.checkbox("All-In", key=f"allin_toggle_{active_session['id']}")

        if all_in:
            elim_options = [p for p in alive_players if p != winner]
            eliminated_players = checkbox_grid(
                "Eliminated Player(s)",
                elim_options,
                key_prefix="elim",
                session_id=active_session["id"],
                columns=2
            )

    if st.button("Submit Hand", type="primary"):

        if street == "River" and hand_type != "No Showdown" and len(showdown_losers) == 0:
            st.error("At least one showdown loser is required for a River showdown hand.")
            st.stop()

        data = {
            "hand_number": int(datetime.utcnow().timestamp()),
            "winner": winner,
            "street": street,
            "hand_type": hand_type,
            "pot_size": pot_size,
            "all_in": all_in,
            "eliminated_player": eliminated_players,
            "showdown_losers": showdown_losers,
            "players_in_game": players_in_game,
            "game_name": active_session["name"],
            "created_at": datetime.utcnow().isoformat(),
        }

        supabase.table("hands").insert(data).execute()
        st.success("Hand logged!")
        st.rerun()

# ============================
# ===== END OF BLOCK 1 =======
# ============================


# ============================
# ======== BLOCK 2 ===========
# ===== START OF BLOCK 2 =====
# ============================

#=============================
#Player Matrix DataFrame
#=============================


def build_player_hand_matrix(hands, players_in_game):
    """
    Build a full per-player-per-hand dataset with:
    - all players represented for every hand
    - kitchen-sink analytics
    - 'N/A' for non-applicable fields
    - cumulative metrics frozen after elimination
    """

    chronological = list(reversed(hands))  # oldest → newest
    matrix_rows = []

    # Pot size → numeric value
    pot_value_map = {"S": 1, "M": 2, "L": 3}

    # Track cumulative stats per player
    cum = {
        p: {
            "wins": 0,
            "folds": 0,
            "showdown_wins": 0,
            "elims": 0,
            "win_streak": 0,
            "loss_streak": 0,
            "alive": True,
            "cumulative_pot_value": 0,   # NEW
        }
        for p in players_in_game
    }

    # Track timing
    last_time = None
    cumulative_session_seconds = 0

    for idx, h in enumerate(chronological, start=1):

        # Hand metadata
        hand_id = h["id"]
        winner = h["winner"]
        street = h["street"]
        hand_type = h["hand_type"]
        pot_size = h["pot_size"]
        all_in = h["all_in"]
        eliminated = h.get("eliminated_player") or []
        showdown_losers = h.get("showdown_losers") or []

        if isinstance(eliminated, str):
            eliminated = [eliminated]
        if isinstance(showdown_losers, str):
            showdown_losers = [showdown_losers]

        # Alive players BEFORE this hand
        alive_before = {p: cum[p]["alive"] for p in players_in_game}

        # Timing
        created_at = datetime.fromisoformat(h["created_at"])
        if last_time is None:
            time_since_last = 0
        else:
            time_since_last = (created_at - last_time).total_seconds()

        cumulative_session_seconds += time_since_last
        last_time = created_at

        # Determine aggressive win
        aggressive_win = (street != "River")

        # Update cumulative stats for winner
        if cum[winner]["alive"]:
            cum[winner]["wins"] += 1

        # Showdown logic
        is_showdown = (street == "River" and hand_type != "No Showdown")
        if is_showdown and cum[winner]["alive"]:
            cum[winner]["showdown_wins"] += 1

        # Fold logic
        for p in players_in_game:
            if cum[p]["alive"]:
                if (
                    p != winner
                    and p not in showdown_losers
                    and p not in eliminated
                ):
                    cum[p]["folds"] += 1

        # Eliminations
        for p in eliminated:
            if cum[p]["alive"]:
                cum[p]["alive"] = False
                cum[winner]["elims"] += 1

        # Streak logic
        for p in players_in_game:
            if not cum[p]["alive"]:
                continue

            if p == winner:
                cum[p]["win_streak"] += 1
                cum[p]["loss_streak"] = 0
            else:
                cum[p]["loss_streak"] += 1
                cum[p]["win_streak"] = 0

        # Alive AFTER this hand
        alive_after = {p: cum[p]["alive"] for p in players_in_game}

        # Determine pot value for this hand
        pot_val = pot_value_map.get(pot_size, 0)

        # Build rows: one per player
        for p in players_in_game:

            if alive_before[p]:
                folded = (
                    p != winner
                    and p not in showdown_losers
                    and p not in eliminated
                )
                showdown_participation = (
                    is_showdown and (p == winner or p in showdown_losers)
                )
                showdown_loser = (p in showdown_losers)
                eliminated_flag = (p in eliminated)
                aggressive_flag = (p == winner and aggressive_win)
            else:
                folded = "N/A"
                showdown_participation = "N/A"
                showdown_loser = "N/A"
                eliminated_flag = "N/A"
                aggressive_flag = "N/A"

            # -----------------------------
            # NEW: Pot value change logic
            # -----------------------------
            if alive_before[p]:
                if p == winner:
                    pot_change = pot_val
                elif p in showdown_losers:
                    pot_change = -pot_val
                else:
                    pot_change = 0
            else:
                pot_change = "N/A"

            # Update cumulative pot value (freeze after elimination)
            if isinstance(pot_change, int):
                cum[p]["cumulative_pot_value"] += pot_change

            matrix_rows.append({
                "hand_id": hand_id,
                "hand_number": idx,
                "created_at": created_at,
                "time_since_last_hand": time_since_last,
                "cumulative_session_seconds": cumulative_session_seconds,

                "player": p,
                "alive_before": alive_before[p],
                "alive_after": alive_after[p],

                "winner": (p == winner) if alive_before[p] else "N/A",
                "folded": folded,
                "showdown_participation": showdown_participation,
                "showdown_loser": showdown_loser,
                "eliminated": eliminated_flag,
                "aggressive_win": aggressive_flag,

                "street": street,
                "hand_type": hand_type,
                "pot_size": pot_size,
                "all_in": all_in,

                # Cumulative stats (frozen after elimination)
                "cumulative_wins": cum[p]["wins"],
                "cumulative_folds": cum[p]["folds"],
                "cumulative_showdown_wins": cum[p]["showdown_wins"],
                "cumulative_eliminations": cum[p]["elims"],
                "win_streak_after_hand": cum[p]["win_streak"],
                "loss_streak_after_hand": cum[p]["loss_streak"],

                # NEW: Pot momentum fields
                "pot_value_change": pot_change,
                "cumulative_pot_value": cum[p]["cumulative_pot_value"],

                # Context
                "num_players_alive": sum(alive_before.values()),
                "num_players_eliminated": sum(1 for x in alive_before.values() if not x),
                "num_showdown_losers": len(showdown_losers),
            })

    return pd.DataFrame(matrix_rows)
#=============================
#Player Matrix DataFrame End
#=============================



# ---------------------------------------------------------
# 4. Session Data (Tap‑to‑Expand Actions)
# ---------------------------------------------------------
st.header("Session Data")



# ---------------------------------------------------------
# 6. Session Game Stats (Hardened + Sortable Tables)
# ---------------------------------------------------------
with st.expander("Session Game Stats"):

    if len(hands) < 2:
        st.info("Not enough hands logged to compute game stats yet.")

    else:
        import altair as alt

        chronological = list(reversed(hands))  # oldest → newest
        total_hands = len(chronological)

        # ---------------------------------------------------------
        # Initialize Player Stats
        # ---------------------------------------------------------
        player_stats = {
            p: {
                "alive": True,
                "hands_played": 0,
                "wins": 0,
                "folds": 0,
                "showdown_wins": 0,
                "showdown_total": 0,
                "showdown_participation": 0,
                "pots_won_S": 0,
                "pots_won_M": 0,
                "pots_won_L": 0,
                "elim_wins": 0,
                "busted_on_hand": None,
                "busted_by": None,
                "aggressive_wins": 0,
                "current_win_streak": 0,
                "current_loss_streak": 0,
                "max_win_streak": 0,
                "max_loss_streak": 0,
            }
            for p in players_in_game
        }

        # ---------------------------------------------------------
        # Average Hand Time (Hardened)
        # ---------------------------------------------------------
        try:
            times = [datetime.fromisoformat(h["created_at"]) for h in chronological]
            deltas = [(times[i + 1] - times[i]).total_seconds() for i in range(len(times) - 1)]
            avg_hand_time = sum(deltas) / len(deltas)

            mins = int(avg_hand_time // 60)
            secs = int(avg_hand_time % 60)

            if mins > 0:
                avg_hand_time_str = f"{mins} min {secs}s"
            else:
                avg_hand_time_str = f"{secs}s"

        except Exception as e:
            print("Error computing average hand time:", e)
            avg_hand_time_str = "—"
        # ---------------------------------------------------------
        # Process Hands (FULLY HARDENED)
        # ---------------------------------------------------------
        for idx, h in enumerate(chronological, start=1):
            try:
                players_list = h.get("players_in_game")
                if not isinstance(players_list, list):
                    print(f"Skipping hand #{idx}: players_in_game invalid")
                    continue

                alive_players = [
                    p for p in players_list
                    if p in player_stats and player_stats[p]["alive"]
                ]

                # Hands played
                for p in alive_players:
                    player_stats[p]["hands_played"] += 1

                # Winner
                winner = h.get("winner")
                if winner not in player_stats:
                    print(f"Skipping hand #{idx}: invalid winner {winner}")
                    continue

                if player_stats[winner]["alive"]:
                    player_stats[winner]["wins"] += 1

                # Street
                street = h.get("street", "Unknown")

                # Aggressive wins
                if street != "River" and player_stats[winner]["alive"]:
                    player_stats[winner]["aggressive_wins"] += 1

                # Pot size
                pot_size = h.get("pot_size")
                if pot_size == "S":
                    player_stats[winner]["pots_won_S"] += 1
                elif pot_size == "M":
                    player_stats[winner]["pots_won_M"] += 1
                elif pot_size == "L":
                    player_stats[winner]["pots_won_L"] += 1

                # Showdown logic
                hand_type = h.get("hand_type", "No Showdown")
                showdown_losers = h.get("showdown_losers") or []
                if isinstance(showdown_losers, str):
                    showdown_losers = [showdown_losers]

                is_showdown = (street == "River" and hand_type != "No Showdown")

                if is_showdown:
                    if player_stats[winner]["alive"]:
                        player_stats[winner]["showdown_participation"] += 1
                        player_stats[winner]["showdown_wins"] += 1
                        player_stats[winner]["showdown_total"] += 1

                    for p in showdown_losers:
                        if p in player_stats and player_stats[p]["alive"]:
                            player_stats[p]["showdown_participation"] += 1
                            player_stats[p]["showdown_total"] += 1

                # Folds
                for p in alive_players:
                    if (
                        p != winner
                        and p not in showdown_losers
                        and p not in (h.get("eliminated_player") or [])
                    ):
                        player_stats[p]["folds"] += 1

                # Eliminations
                eliminated = h.get("eliminated_player") or []
                if isinstance(eliminated, str):
                    eliminated = [eliminated]

                for p in eliminated:
                    if p in player_stats and player_stats[p]["alive"]:
                        player_stats[winner]["elim_wins"] += 1
                        player_stats[p]["alive"] = False
                        player_stats[p]["busted_on_hand"] = idx
                        player_stats[p]["busted_by"] = winner

                # Streak logic
                for p in players_in_game:
                    if p not in player_stats or not player_stats[p]["alive"]:
                        continue

                    if p == winner:
                        player_stats[p]["current_win_streak"] += 1
                        player_stats[p]["current_loss_streak"] = 0
                        player_stats[p]["max_win_streak"] = max(
                            player_stats[p]["max_win_streak"],
                            player_stats[p]["current_win_streak"]
                        )
                    else:
                        player_stats[p]["current_loss_streak"] += 1
                        player_stats[p]["current_win_streak"] = 0
                        player_stats[p]["max_loss_streak"] = max(
                            player_stats[p]["max_loss_streak"],
                            player_stats[p]["current_loss_streak"]
                        )

            except Exception as e:
                print(f"Skipping malformed hand #{idx}: {e}")
                continue

        # ---------------------------------------------------------
        # Summary Metrics (Hardened)
        # ---------------------------------------------------------
        try:
            showdown_hands = sum(
                1 for h in chronological
                if h.get("street") == "River" and h.get("hand_type") != "No Showdown"
            )
            showdown_pct = f"{round((showdown_hands / total_hands) * 100)}%"
        except:
            showdown_pct = "—"

        try:
            allin_hands = sum(1 for h in chronological if h.get("all_in"))
            allin_pct = f"{round((allin_hands / total_hands) * 100)}%"
        except:
            allin_pct = "—"

        try:
            elim_hands = sum(1 for h in chronological if h.get("eliminated_player"))
            elim_pct = f"{round((elim_hands / total_hands) * 100)}%"
        except:
            elim_pct = "—"

        st.subheader("Game Summary Metrics")

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Hands", total_hands)
        c2.metric("Avg Hand Time", avg_hand_time_str)
        c3.metric("Showdown %", showdown_pct)

        c4, c5 = st.columns(2)
        c4.metric("All-In %", allin_pct)
        c5.metric("Elimination Rate", elim_pct)

        # ---------------------------------------------------------
        # Leaderboard (Sortable + Hardened)
        # ---------------------------------------------------------
        st.subheader("Session Leaderboard")

        leaderboard_rows = []

        try:
            for p, s in player_stats.items():

                played = s["hands_played"]
                wins = s["wins"]
                folds = s["folds"]

                win_pct = round((wins / played) * 100) if played > 0 else 0
                sd_pct = (
                    round((s["showdown_wins"] / s["showdown_total"]) * 100)
                    if s["showdown_total"] > 0 else 0
                )

                if s["busted_on_hand"]:
                    busted_display = f"{s['busted_on_hand']} ({s['busted_by']})"
                else:
                    busted_display = "—"

                leaderboard_rows.append({
                    "Player": p,
                    "Hands Played": played,
                    "Hands Won": wins,
                    "Folds": folds,
                    "Win %": win_pct,
                    "SD Win %": sd_pct,
                    "KOs": s["elim_wins"],
                    "Busted On": busted_display
                })

        except Exception as e:
            print("Error building leaderboard_rows:", e)

        try:
            leaderboard_df = pd.DataFrame(leaderboard_rows).sort_values(
                by="Hands Won", ascending=False
            )
            st.dataframe(leaderboard_df, use_container_width=True)
        except Exception as e:
            print("Error rendering leaderboard table:", e)
            st.write("Leaderboard unavailable.")



        # ---------------------------------------------------------
        # Build Player-Hand Matrix (for trendlines + advanced stats)
        # ---------------------------------------------------------
        matrix_df = build_player_hand_matrix(hands, players_in_game)

        # ---------------------------------------------------------
        # Win Progression Trendline
        # ---------------------------------------------------------
        st.write("### Win Progression Trendline")

        try:
            # Remove eliminated-player placeholder rows for the chart
            trend_df = matrix_df[matrix_df["winner"] != "N/A"]

            win_chart = (
                alt.Chart(trend_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("hand_number:Q", title="Hand Number"),
                    y=alt.Y("cumulative_wins:Q", title="Cumulative Wins"),
                    color=alt.Color("player:N", title="Player"),
                    tooltip=[
                        "player",
                        "hand_number",
                        "cumulative_wins",
                        "winner",
                    ],
                )
                .properties(height=300)
            )

            st.altair_chart(win_chart, use_container_width=True)

        except Exception as e:
            st.write("Could not generate win progression chart.")
            print("Trendline error:", e)


        # ---------------------------------------------------------
        # Chip Stack Proxy Trendline (Chip Proxy)
        # ---------------------------------------------------------
        st.write("### Chip Stack Proxy Trendline")
        st.caption("Pot Size Proxy Values: S = 1 • M = 2 • L = 3")

        try:
            # Filter out eliminated players' frozen rows
            pot_df = matrix_df[matrix_df["pot_value_change"] != "N/A"]

            pot_chart = (
                alt.Chart(pot_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("hand_number:Q", title="Hand Number"),
                    y=alt.Y("cumulative_pot_value:Q", title="Cumulative Stack Value"),
                    color=alt.Color("player:N", title="Player"),
                    tooltip=[
                        "player",
                        "hand_number",
                        "pot_value_change",
                        "cumulative_pot_value",
                        "pot_size",
                        "winner",
                    ],
                )
                .properties(height=300)
            )

            st.altair_chart(pot_chart, use_container_width=True)

        except Exception as e:
            st.write("Could not generate Chip Stack Proxy Trendline.")
            print("Chip Stack Proxy trendline error:", e)




        # ---------------------------------------------------------
        # Charts (Hardened)
        # ---------------------------------------------------------
        st.subheader("Pot Size Distribution")

        try:
            pot_sizes = [h.get("pot_size") for h in chronological]
            pot_counts = pd.Series(pot_sizes).value_counts()
            pot_order = ["S", "M", "L"]

            pot_df_chart = pd.DataFrame({
                "Pot Size": pot_order,
                "Count": [pot_counts.get(x, 0) for x in pot_order]
            })

            pot_df_chart["Pot Size"] = pd.Categorical(
                pot_df_chart["Pot Size"],
                categories=pot_order,
                ordered=True
            )

            st.altair_chart(
                alt.Chart(pot_df_chart).mark_bar().encode(
                    y=alt.Y("Pot Size:N", sort=pot_order),
                    x=alt.X("Count:Q", axis=alt.Axis(tickMinStep=1))
                ),
                use_container_width=True
            )

        except Exception as e:
            print("Error rendering pot size chart:", e)

        st.subheader("Winning Hand Type Distribution")

        try:
            hand_order = [
                "High Card", "Pair", "Two Pair", "Trips", "Straight",
                "Flush", "Full House", "Quads", "Straight Flush", "No Showdown"
            ]

            hand_types = [h.get("hand_type") for h in chronological]
            hand_counts = pd.Series(hand_types).value_counts()

            hand_df_chart = pd.DataFrame({
                "Hand Type": hand_order,
                "Count": [hand_counts.get(x, 0) for x in hand_order]
            })

            hand_df_chart["Hand Type"] = pd.Categorical(
                hand_df_chart["Hand Type"],
                categories=hand_order,
                ordered=True
            )

            st.altair_chart(
                alt.Chart(hand_df_chart).mark_bar().encode(
                    y=alt.Y("Hand Type:N", sort=hand_order),
                    x=alt.X("Count:Q", axis=alt.Axis(tickMinStep=1))
                ),
                use_container_width=True
            )

        except Exception as e:
            print("Error rendering hand type chart:", e)

        st.subheader("Street End Distribution")

        try:
            street_order = ["Preflop", "Flop", "Turn", "River"]
            streets = [h.get("street") for h in chronological]
            street_counts = pd.Series(streets).value_counts()

            street_df_chart = pd.DataFrame({
                "Street": street_order,
                "Count": [street_counts.get(x, 0) for x in street_order]
            })

            street_df_chart["Street"] = pd.Categorical(
                street_df_chart["Street"],
                categories=street_order,
                ordered=True
            )
            st.altair_chart(
                alt.Chart(street_df_chart).mark_bar().encode(
                    y=alt.Y("Street:N", sort=street_order),
                    x=alt.X("Count:Q", axis=alt.Axis(tickMinStep=1))
                ),
                use_container_width=True
            )

        except Exception as e:
            print("Error rendering street chart:", e)

        # ---------------------------------------------------------
        # Pot Size Distribution by Player (Wins Only)
        # ---------------------------------------------------------
        st.subheader("Pot Size Distribution by Player (Wins Only)")

        pot_rows = []
        try:
            for p, s in player_stats.items():
                S = s["pots_won_S"]
                M = s["pots_won_M"]
                L = s["pots_won_L"]
                total = S + M + L

                pot_rows.append({
                    "Player": p,
                    "S": S,
                    "M": M,
                    "L": L,
                    "Total": total
                })

        except Exception as e:
            print("Error building pot_rows:", e)

        try:
            pot_df = pd.DataFrame(pot_rows).sort_values(
                by="Total", ascending=False
            )
            st.dataframe(pot_df, use_container_width=True)

        except Exception as e:
            print("Error rendering pot table:", e)
            st.write("Pot size table unavailable.")

        # ---------------------------------------------------------
        # Awards (Hardened)
        # ---------------------------------------------------------
        st.subheader("Awards")

        def get_clear_winner(key):
            try:
                values = [s[key] for s in player_stats.values()]
                max_val = max(values)
                if values.count(max_val) == 1 and max_val > 0:
                    for p, s in player_stats.items():
                        if s[key] == max_val:
                            return p, max_val
            except Exception as e:
                print(f"Award error ({key}):", e)
            return None, None

        # Heater Award
        try:
            heater_p, heater_v = get_clear_winner("max_win_streak")
            if heater_p:
                st.write(f"🔥 **Heater Award:** {heater_p} peaked with a {heater_v}-hand win streak.")
            else:
                st.write("🔥 **Heater Award:**")
        except Exception as e:
            print("Error computing Heater Award:", e)

        # Ice Cold Award
        try:
            cold_p, cold_v = get_clear_winner("max_loss_streak")
            if cold_p:
                st.write(f"❄️ **Ice Cold Award:** {cold_p} suffered a {cold_v}-hand losing streak.")
            else:
                st.write("❄️ **Ice Cold Award:**")
        except Exception as e:
            print("Error computing Ice Cold Award:", e)

        # Fastest Bustout
        try:
            elim_order = []
            for idx, h in enumerate(chronological, start=1):
                eliminated = h.get("eliminated_player") or []
                if isinstance(eliminated, str):
                    eliminated = [eliminated]
                for p in eliminated:
                    elim_order.append((p, idx))

            if elim_order:
                fb_p, fb_h = elim_order[0]
                st.write(f"💀 **Fastest Bustout:** {fb_p} was eliminated on Hand #{fb_h}.")
            else:
                st.write("💀 **Fastest Bustout:**")

        except Exception as e:
            print("Error computing Fastest Bustout:", e)


        # ---------------------------------------------------------
        # Showdown Win Percentage Awards
        # ---------------------------------------------------------
        try:
            sd_candidates = []
            for p, s in player_stats.items():
                sd_played = s["showdown_participation"]
                sd_won = s["showdown_wins"]

                if sd_played >= 5:
                    pct = (sd_won / sd_played) * 100
                    sd_candidates.append((p, pct, sd_played, sd_won))

            if sd_candidates:
                # Sort by showdown win %
                sd_sorted = sorted(sd_candidates, key=lambda x: x[1], reverse=True)

                # Best showdown performer
                best_p, best_pct, best_played, best_wins = sd_sorted[0]
                if sum(1 for x in sd_sorted if x[1] == best_pct) == 1:
                    st.write(
                        f"🎯 **The Closer:** {best_p} won {best_pct:.0f}% of showdowns "
                        f"({best_wins} wins in {best_played} showdowns, min 5)."
                    )
                else:
                    st.write("🎯 **The Closer:**")

                # Worst showdown performer
                worst_p, worst_pct, worst_played, worst_wins = sd_sorted[-1]
                if sum(1 for x in sd_sorted if x[1] == worst_pct) == 1:
                    st.write(
                        f"🫣 **I Should Have Folded:** {worst_p} won {worst_pct:.0f}% of showdowns "
                        f"({worst_wins} wins in {worst_played} showdowns, min 5)."
                    )
                else:
                    st.write("🫣 **I Should Have Folded:**")

            else:
                st.write("🎯 **The Closer:**")
                st.write("🫣 **I Should Have Folded:**")

        except Exception as e:
            print("Error computing showdown awards:", e)


        # Most Active
        try:
            active_p, active_v = get_clear_winner("showdown_participation")
            if active_p:
                st.write(f"📈 **Most Active Player:** {active_p} participated in {active_v} showdowns.")
            else:
                st.write("📈 **Most Active Player:**")
        except Exception as e:
            print("Error computing Most Active Award:", e)

        # Most Passive
        try:
            passive_p, passive_v = get_clear_winner("folds")
            if passive_p:
                st.write(f"🪫 **Most Passive Player:** {passive_p} folded {passive_v} times.")
            else:
                st.write("🪫 **Most Passive Player:**")
        except Exception as e:
            print("Error computing Most Passive Award:", e)

        # Aggression Award
        try:
            agg_p, agg_v = get_clear_winner("aggressive_wins")
            if agg_p:
                st.write(f"⚔️ **Aggression Award:** {agg_p} won {agg_v} pots before the river.")
            else:
                st.write("⚔️ **Aggression Award:**")
        except Exception as e:
            print("Error computing Aggression Award:", e)

        # Most Dominant Player
        try:
            dom_candidates = [
                (p, s) for p, s in player_stats.items()
                if s["hands_played"] >= 5
            ]

            if dom_candidates:
                win_rates = [(p, s["wins"] / s["hands_played"]) for p, s in dom_candidates]
                max_rate = max(v for _, v in win_rates)

                if sum(1 for _, v in win_rates if v == max_rate) == 1:
                    dom_p = next(p for p, v in win_rates if v == max_rate)
                    dom_pct = round(max_rate * 100)
                    st.write(f"🏆 **Most Dominant Player:** {dom_p} leads with a {dom_pct}% win rate.")
                else:
                    st.write("🏆 **Most Dominant Player:**")
            else:
                st.write("🏆 **Most Dominant Player:**")

        except Exception as e:
            print("Error computing Dominant Player Award:", e)




with st.expander("Hand History", expanded=False):

    total_hands = len(hands)

    # ---------------------------------------------------------
    # Helper: compute historical alive players for a given hand
    # ---------------------------------------------------------
    def get_alive_players_at_hand(target_hand_id):
        eliminated_before = set()
        chronological = list(reversed(hands))  # oldest → newest

        for h in chronological:
            if h["id"] == target_hand_id:
                break

            eliminated = h.get("eliminated_player") or []
            if isinstance(eliminated, str):
                eliminated = [eliminated]

            for p in eliminated:
                eliminated_before.add(p)

        return [p for p in players_in_game if p not in eliminated_before]

    # ---------------------------------------------------------
    # Render a single hand (tap‑to‑expand)
    # ---------------------------------------------------------
    def render_hand(h, hand_number):

        winner = h["winner"]
        street = h["street"]
        hand_type = h["hand_type"]
        pot_size = h["pot_size"]

        showdown_losers = h.get("showdown_losers") or []
        eliminated = h.get("eliminated_player") or []

        if isinstance(showdown_losers, str):
            showdown_losers = [showdown_losers]
        if isinstance(eliminated, str):
            eliminated = [eliminated]

        # Build summary line
        line = (
            f"Hand #{hand_number} — {winner} won with {hand_type} "
            f"on the {street} (Pot: {pot_size})"
        )

        if showdown_losers:
            line += f" — Showdown Losers: {', '.join(showdown_losers)}"
        if eliminated:
            line += f" — Eliminated: {', '.join(eliminated)}"

        # Tappable row
        if st.button(line, key=f"tap_{h['id']}", use_container_width=True):
            st.session_state["open_hand"] = (
                None if st.session_state.get("open_hand") == h["id"] else h["id"]
            )

        # Expanded actions
        if st.session_state.get("open_hand") == h["id"]:

            with st.expander(f"Actions for Hand #{hand_number}", expanded=True):

                # Delete
                if st.button(f"Delete Hand #{hand_number}", key=f"delete_{h['id']}"):
                    st.session_state["confirm_delete"] = h["id"]

                if st.session_state.get("confirm_delete") == h["id"]:
                    st.warning("Are you sure you want to delete this hand?")

                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button("Yes, Delete", key=f"yes_delete_{h['id']}"):
                            supabase.table("hands").delete().eq("id", h["id"]).execute()
                            st.success("Hand deleted.")
                            st.session_state["confirm_delete"] = None
                            st.session_state["open_hand"] = None
                            st.rerun()

                    with c2:
                        if st.button("Cancel", key=f"cancel_delete_{h['id']}"):
                            st.session_state["confirm_delete"] = None

                # Edit
                if st.button(f"Edit Hand #{hand_number}", key=f"edit_{h['id']}"):
                    st.session_state["editing_hand"] = h["id"]

                # Edit form
                if st.session_state.get("editing_hand") == h["id"]:

                    with st.expander(f"Editing Hand #{hand_number}", expanded=True):

                        alive_at_time = get_alive_players_at_hand(h["id"])

                        new_winner = st.radio(
                            "Winner",
                            alive_at_time,
                            index=alive_at_time.index(h["winner"]),
                            key=f"edit_winner_{h['id']}"
                        )

                        streets = ["Preflop", "Flop", "Turn", "River"]
                        new_street = st.radio(
                            "Street",
                            streets,
                            index=streets.index(h["street"]),
                            key=f"edit_street_{h['id']}"
                        )

                        hand_types = [
                            "High Card", "Pair", "Two Pair", "Trips", "Straight",
                            "Flush", "Full House",                            "Quads", "Straight Flush", "No Showdown"
                        ]
                        new_hand_type = st.radio(
                            "Hand Type",
                            hand_types,
                            index=hand_types.index(h["hand_type"]),
                            key=f"edit_handtype_{h['id']}"
                        )

                        pot_sizes = ["S", "M", "L"]
                        new_pot_size = st.radio(
                            "Pot Size",
                            pot_sizes,
                            index=pot_sizes.index(h["pot_size"]),
                            key=f"edit_potsize_{h['id']}"
                        )

                        new_all_in = st.checkbox(
                            "All-In",
                            value=h["all_in"],
                            key=f"edit_allin_{h['id']}"
                        )

                        new_showdown_losers = []
                        if new_street == "River" and new_hand_type != "No Showdown":
                            loser_options = [p for p in alive_at_time if p != new_winner]
                            new_showdown_losers = checkbox_grid(
                                "Showdown Losers",
                                loser_options,
                                key_prefix="edit_losers",
                                session_id=h["id"],
                                prechecked=h.get("showdown_losers") or []
                            )

                        new_eliminated = []
                        if new_all_in:
                            elim_options = [p for p in alive_at_time if p != new_winner]
                            new_eliminated = checkbox_grid(
                                "Eliminated Player(s)",
                                elim_options,
                                key_prefix="edit_elim",
                                session_id=h["id"],
                                prechecked=h.get("eliminated_player") or []
                            )

                        if st.button("Save Changes", key=f"save_edit_{h['id']}"):
                            updated = {
                                "winner": new_winner,
                                "street": new_street,
                                "hand_type": new_hand_type,
                                "pot_size": new_pot_size,
                                "all_in": new_all_in,
                                "showdown_losers": new_showdown_losers,
                                "eliminated_player": new_eliminated,
                            }

                            supabase.table("hands").update(updated).eq("id", h["id"]).execute()

                            st.success("Hand updated.")
                            st.session_state["editing_hand"] = None
                            st.session_state["open_hand"] = None
                            st.rerun()

    # Render ALL hands
    for index, h in enumerate(hands):
        hand_number = total_hands - index
        render_hand(h, hand_number)



# ---------------------------------------------------------
# 7. Admin Tools (Bottom of Page)
# ---------------------------------------------------------

st.header("Admin")
with st.expander("Admin Tools (Danger Zone)"):

    st.write("### Download Data")

    # ---- Raw Hands CSV ----
    try:
        raw_df = pd.DataFrame(hands)
        raw_csv = raw_df.to_csv(index=False)

        st.download_button(
            label="Download Raw Hands CSV",
            data=raw_csv,
            file_name=f"{active_session['name']}_raw_hands.csv",
            mime="text/csv",
            key="download_raw_csv"
        )
    except Exception as e:
        st.write("Could not generate raw hands CSV.")
        print("Raw CSV error:", e)

    st.write("### Download Player-Hand Matrix")

    try:
        matrix_df = build_player_hand_matrix(hands, players_in_game)
        matrix_csv = matrix_df.to_csv(index=False)

        st.download_button(
            label="Download Player-Hand Matrix CSV",
            data=matrix_csv,
            file_name=f"{active_session['name']}_player_hand_matrix.csv",
            mime="text/csv",
            key="download_matrix_csv"
        )
    except Exception as e:
        st.write("Could not generate player-hand matrix CSV.")
        print("Matrix CSV error:", e)


    st.markdown("---")

    st.write("### Delete a Global Player")

    player_to_delete = st.selectbox(
        "Select player to delete:",
        player_names,
        key="delete_player_select"
    )

    if st.button("Delete Player", key="delete_player_btn"):
        st.session_state["confirm_delete_player"] = player_to_delete

    if st.session_state.get("confirm_delete_player") == player_to_delete:
        st.warning(f"Are you sure you want to delete '{player_to_delete}' from the global list?")

        c1, c2 = st.columns(2)

        with c1:
            if st.button("Yes, Delete Player", key="confirm_delete_player_yes"):
                supabase.table("players").delete().eq("name", player_to_delete).execute()
                st.success(f"Deleted player '{player_to_delete}'.")
                st.session_state["confirm_delete_player"] = None
                st.rerun()

        with c2:
            if st.button("Cancel", key="confirm_delete_player_no"):
                st.session_state["confirm_delete_player"] = None

    st.markdown("---")

    st.write("### Delete an Entire Session")

    session_to_delete = st.selectbox(
        "Select session to delete:",
        session_names,
        key="delete_session_select"
    )

    if st.button("Delete Session", key="delete_session_btn"):
        st.session_state["confirm_delete_session"] = session_to_delete

    if st.session_state.get("confirm_delete_session") == session_to_delete:
        st.warning(f"Delete session '{session_to_delete}' and ALL hands in it?")

        c1, c2 = st.columns(2)

        with c1:
            if st.button("Yes, Delete Session", key="confirm_delete_session_yes"):
                supabase.table("hands").delete().eq("game_name", session_to_delete).execute()
                supabase.table("sessions").delete().eq("name", session_to_delete).execute()

                st.success(f"Session '{session_to_delete}' deleted.")
                st.session_state["confirm_delete_session"] = None
                st.session_state["active_session_id"] = None
                st.rerun()

        with c2:
            if st.button("Cancel", key="confirm_delete_session_no"):
                st.session_state["confirm_delete_session"] = None

# ============================
# ===== END OF BLOCK 2 =======
# ============================
