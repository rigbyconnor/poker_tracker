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
# Checkbox grid helper (session‑namespaced keys)
# ---------------------------------------------------------
def checkbox_grid(label, options, key_prefix, session_id, columns=2):
    st.write(f"### {label}")
    selected = []

    rows = (len(options) + columns - 1) // columns
    idx = 0

    for _ in range(rows):
        cols = st.columns(columns)
        for c in range(columns):
            if idx < len(options):
                name = options[idx]
                key = f"{key_prefix}_{session_id}_{name}"
                checked = cols[c].checkbox(name, key=key)
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

if "form_reset_counter" not in st.session_state:
    st.session_state["form_reset_counter"] = 0


# ---------------------------------------------------------
# 1. Session Selector
# ---------------------------------------------------------
st.title("Poker Night Tracker")
st.subheader("Select Game Session")

# Determine default selection
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

    if st.button("Save Session Players", key=f"save_players_{active_session['id']}"):
        update_session_players(active_session["id"], edited_players)
        st.success("Session players updated!")
        st.rerun()


# ---------------------------------------------------------
# 2. Log a Hand (wrapped in dynamic container)
# ---------------------------------------------------------
st.header("Log a Hand")

if not active_session:
    st.info("Select or create a session to begin.")
    st.stop()

sid = str(active_session["id"])

form_key = f"hand_form_{sid}_{st.session_state['form_reset_counter']}"
with st.container(key=form_key):

    if not players_in_game:
        st.info("This session has no players. Edit the session to add players.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Winner")
            winner = st.radio("", players_in_game, key=f"winner_radio_{sid}")

        with col2:
            st.subheader("Street")
            streets = ["Preflop", "Flop", "Turn", "River"]
            street = st.radio("", streets, key=f"street_radio_{sid}")

        col3, col4 = st.columns(2)

        with col3:
            st.subheader("Hand Type")
            hand_types = [
                "High Card", "Pair", "Two Pair", "Trips", "Straight",
                "Flush", "Full House", "Quads", "Straight Flush", "No Showdown"
            ]
            hand_type = st.radio("", hand_types, key=f"handtype_radio_{sid}")

        with col4:
            st.subheader("Pot Size")
            pot_sizes = ["S", "M", "L"]
            pot_size = st.radio("", pot_sizes, key=f"potsize_radio_{sid}")

        st.subheader("All-In")
        all_in = st.checkbox("All-In", key=f"allin_toggle_{sid}")

        showdown_losers = []
        if street == "River" and hand_type != "No Showdown":
            showdown_losers = checkbox_grid(
                "Showdown Losers",
                players_in_game,
                key_prefix="losers",
                session_id=sid,
                columns=2
            )

        eliminated_player = None
        if all_in:
            eliminated_list = checkbox_grid(
                "Eliminated Player",
                players_in_game,
                key_prefix="elim",
                session_id=sid,
                columns=2
            )
            if len(eliminated_list) > 0:
                eliminated_player = eliminated_list[0]

        if st.button("Submit Hand", type="primary"):
            data = {
                "hand_number": int(datetime.utcnow().timestamp()),
                "winner": winner,
                "street": street,
                "hand_type": hand_type,
                "pot_size": pot_size,
                "all_in": all_in,
                "eliminated_player": eliminated_player,
                "showdown_losers": showdown_losers,
                "players_in_game": players_in_game,
                "game_name": active_session["name"],
                "created_at": datetime.utcnow().isoformat(),
            }
            supabase.table("hands").insert(data).execute()

            # Increment reset counter
            st.session_state["form_reset_counter"] += 1

            st.success("Hand logged!")
            st.rerun()


# ---------------------------------------------------------
# 3. Hand History
# ---------------------------------------------------------
st.header("Hand History")

hands = load_hands_for_session(active_session["name"])

if not hands:
    st.info("No hands logged yet.")
else:
    total_hands = len(hands)

    for index, h in enumerate(hands):
        hand_number = total_hands - index

        winner = h["winner"]
        street = h["street"]
        hand_type = h["hand_type"]
        pot_size = h["pot_size"]
        eliminated = h["eliminated_player"]

        line = (
            f"**Hand #{hand_number} — {winner} won with {hand_type} "
            f"on the {street} (Pot: {pot_size})**"
        )

        if eliminated:
            line += f" — Eliminated: {eliminated}"

        st.write(line)


# ---------------------------------------------------------
# 4. Add Player
# ---------------------------------------------------------
with st.expander("Add Player"):
    new_player = st.text_input("New Player Name")
    if st.button("Add Player"):
        if new_player.strip():
            add_player(new_player.strip())
            st.success(f"Added {new_player}")
            st.rerun()