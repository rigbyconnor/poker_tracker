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
# Supabase connection
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

st.set_page_config(page_title="Poker Night Tracker", layout="centered")


# ---------------------------------------------------------
# Helpers
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
# Checkbox grid helper
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
# Load base data
# ---------------------------------------------------------
players = load_players()
player_names = [p["name"] for p in players]

sessions = load_sessions()
session_names = [s["name"] for s in sessions]

CREATE_NEW = "➕ Create New Session…"
session_dropdown_options = session_names + [CREATE_NEW]


# ---------------------------------------------------------
# Remember last session
# ---------------------------------------------------------
if "active_session_id" not in st.session_state:
    st.session_state["active_session_id"] = None


# ---------------------------------------------------------
# 1. Session Selector
# ---------------------------------------------------------
st.markdown(
    "<h3 style='text-align: center; margin-bottom: 0;'>Poker Night Tracker</h3>",
    unsafe_allow_html=True
)

st.subheader("Select Game Session")

if st.session_state["active_session_id"]:
    active_session = next(
        (s for s in sessions if s["id"] == st.session_state["active_session_id"]),
        None
    )
    default_name = active_session["name"] if active_session else None
else:
    default_name = None

selected_session_name = st.selectbox(
    "Game Session",
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
# Load selected session
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

        # Hand Type gating
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

    # Showdown Losers
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

    # All-In only on River
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

    # Submit
    if st.button("Submit Hand", type="primary"):

        # Require showdown losers on River
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



# ---------------------------------------------------------
# 4. Session Dashboard (Tabbed Interface)
# ---------------------------------------------------------
st.header("Session Dashboard")

tab_history, tab_stats, tab_admin = st.tabs(["History", "Stats", "Admin Tools"])



# -------------------------
# HISTORY TAB
# -------------------------
with tab_history:

    st.subheader("Hand History")

    with st.expander("Show Full Hand History", expanded=False):

        total_hands = len(hands)

        # Helper: compute historical alive players for a given hand
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

        # Render a single hand (tap‑to‑expand)
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

            line = (
                f"Hand #{hand_number} — {winner} won with {hand_type} "
                f"on the {street} (Pot: {pot_size})"
            )

            if showdown_losers:
                line += f" — Showdown Losers: {', '.join(showdown_losers)}"
            if eliminated:
                line += f" — Eliminated: {', '.join(eliminated)}"

            if st.button(line, key=f"tap_{h['id']}", use_container_width=True):
                st.session_state["open_hand"] = (
                    None if st.session_state.get("open_hand") == h["id"] else h["id"]
                )

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
                                "Flush", "Full House", "Quads", "Straight Flush", "No Showdown"
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

        # Render all hands
        for index, h in enumerate(hands):
            hand_number = total_hands - index
            render_hand(h, hand_number)


# -------------------------
# STATS TAB
# -------------------------
with tab_stats:

    st.subheader("Session Game Stats")

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
            deltas = [(times[i+1] - times[i]).total_seconds() for i in range(len(times)-1)]
            avg_hand_time = sum(deltas) / len(deltas)
            avg_hand_time_str = f"{round(avg_hand_time)} sec"
        except Exception:
            avg_hand_time_str = "—"

        # ---------------------------------------------------------
        # Process Hands (FULLY HARDENED)
        # ---------------------------------------------------------
        for idx, h in enumerate(chronological, start=1):
            try:
                players_list = h.get("players_in_game")
                if not isinstance(players_list, list):
                    continue

                alive_players_at_time = [
                    p for p in players_list
                    if p in player_stats and player_stats[p]["alive"]
                ]

                # Hands played
                for p in alive_players_at_time:
                    player_stats[p]["hands_played"] += 1

                # Winner
                winner = h.get("winner")
                if winner not in player_stats:
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
                for p in alive_players_at_time:
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

            except Exception:
                continue

        # ---------------------------------------------------------
        # Summary Metrics
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
        # Leaderboard
        # ---------------------------------------------------------
        st.subheader("Session Leaderboard")

        leaderboard_rows = []
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

        leaderboard_df = pd.DataFrame(leaderboard_rows).sort_values(
            by="Hands Won", ascending=False
        )
        st.dataframe(leaderboard_df, use_container_width=True)

        # ---------------------------------------------------------
        # Charts
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
                pot_df_chart["Pot Size"], categories=pot_order, ordered=True
            )

            st.altair_chart(
                alt.Chart(pot_df_chart).mark_bar().encode(
                    y=alt.Y("Pot Size:N", sort=pot_order),
                    x=alt.X("Count:Q", axis=alt.Axis(tickMinStep=1))
                ),
                use_container_width=True
            )
        except Exception:
            pass

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
                hand_df_chart["Hand Type"], categories=hand_order, ordered=True
            )

            st.altair_chart(
                alt.Chart(hand_df_chart).mark_bar().encode(
                    y=alt.Y("Hand Type:N", sort=hand_order),
                    x=alt.X("Count:Q", axis=alt.Axis(tickMinStep=1))
                ),
                use_container_width=True
            )
        except Exception:
            pass


# -------------------------
# ADMIN TOOLS TAB
# -------------------------
with tab_admin:

    st.subheader("Admin Tools (Danger Zone)")

    st.warning("These actions cannot be undone. Proceed carefully.")

    # -------------------------
    # Delete Entire Session
    # -------------------------
    if st.button("Delete Entire Session", type="secondary"):
        st.session_state["confirm_delete_session"] = True

    if st.session_state.get("confirm_delete_session"):
        st.error("Are you sure you want to delete this entire session and all hands?")
        c1, c2 = st.columns(2)

        with c1:
            if st.button("Yes, Delete Session"):
                # Delete all hands for this session
                supabase.table("hands").delete().eq("game_name", active_session["name"]).execute()

                # Delete the session itself
                supabase.table("sessions").delete().eq("id", active_session["id"]).execute()

                st.success("Session deleted.")
                st.session_state["confirm_delete_session"] = None
                st.session_state["active_session_id"] = None
                st.rerun()

        with c2:
            if st.button("Cancel Delete Session"):
                st.session_state["confirm_delete_session"] = None

    st.markdown("---")

    # -------------------------
    # Reset Eliminations
    # -------------------------
    st.subheader("Reset Eliminations")

    st.write("This will restore all players to 'alive' status without deleting hands.")

    if st.button("Reset Eliminations"):
        # Reload all hands
        all_hands = load_hands_for_session(active_session["name"])

        # Remove eliminated_player field from all hands
        for h in all_hands:
            supabase.table("hands").update({"eliminated_player": []}).eq("id", h["id"]).execute()

        st.success("All eliminations reset.")
        st.rerun()

    st.markdown("---")

    # -------------------------
    # Export Data (Optional Future Feature)
    # -------------------------
    st.subheader("Export Session Data")

    st.info("Coming soon: CSV / JSON export for hands and stats.")