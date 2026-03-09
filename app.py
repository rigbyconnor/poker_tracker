# ============================
# ======== BLOCK 1 ===========
# ===== START OF BLOCK 1 =====
# ============================

import streamlit as st
from supabase import create_client
from datetime import datetime
import json

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
st.header("Log a Hand")

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
    hand_types = [
        "High Card", "Pair", "Two Pair", "Trips", "Straight",
        "Flush", "Full House", "Quads", "Straight Flush", "No Showdown"
    ]
    hand_type = st.radio("", hand_types, key=f"handtype_radio_{active_session['id']}")

with col4:
    st.subheader("Pot Size")
    pot_sizes = ["S", "M", "L"]
    pot_size = st.radio("", pot_sizes, key=f"potsize_radio_{active_session['id']}")

st.subheader("All-In")
all_in = st.checkbox("All-In", key=f"allin_toggle_{active_session['id']}")

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

eliminated_players = []
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

# ---------------------------------------------------------
# 5. Session Leaderboard
# ---------------------------------------------------------
with st.expander("Session Leaderboard"):

    # Initialize stats
    stats = {p: {
        "wins": 0,
        "sd_wins": 0,
        "sd_total": 0,
        "big_pots": 0,
        "folds": 0,
        "eliminated_hand": None,
        "hands_played": 0
    } for p in players_in_game}

    chronological = list(reversed(hands))  # oldest → newest
    total_hands = len(chronological)

    for idx, h in enumerate(chronological, start=1):
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

        # Hands Played = player was alive at start of hand
        for p in h["players_in_game"]:
            if p in stats:
                stats[p]["hands_played"] += 1

        # Wins
        if winner in stats:
            stats[winner]["wins"] += 1

        # Showdown stats
        is_showdown = (street == "River" and hand_type != "No Showdown")
        if is_showdown:
            if winner in stats:
                stats[winner]["sd_wins"] += 1
                stats[winner]["sd_total"] += 1

            for p in showdown_losers:
                if p in stats:
                    stats[p]["sd_total"] += 1

        # Folds
        for p in h["players_in_game"]:
            if (
                p != winner
                and p not in showdown_losers
                and p not in eliminated
            ):
                stats[p]["folds"] += 1

        # Eliminated Hand
        for p in eliminated:
            if p in stats and stats[p]["eliminated_hand"] is None:
                stats[p]["eliminated_hand"] = idx

    # Build leaderboard rows
    leaderboard_rows = []
    for p in players_in_game:
        played = stats[p]["hands_played"]
        wins = stats[p]["wins"]

        win_pct = f"{round((wins / played) * 100)}%" if played > 0 else "—"

        sd_total = stats[p]["sd_total"]
        sd_win_pct = (
            f"{round((stats[p]['sd_wins'] / sd_total) * 100)}%"
            if sd_total > 0 else "—"
        )

        elim = stats[p]["eliminated_hand"] if stats[p]["eliminated_hand"] else "—"

        leaderboard_rows.append({
            "Player": p,
            "Hands Played": played,
            "Hands Won": wins,
            "Folds": stats[p]["folds"],
            "Win %": win_pct,
            "SD Win %": sd_win_pct,
            "Eliminated Hand": elim
        })

    st.dataframe(leaderboard_rows, hide_index=True)

# ============================
# ===== END OF BLOCK 2 =======
# ============================