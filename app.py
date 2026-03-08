import streamlit as st
from supabase import create_client
from datetime import datetime

# ---------------------------------------------------------
# Supabase connection
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

st.set_page_config(page_title="Poker Night Tracker", layout="centered")


# ---------------------------------------------------------
# Database helpers
# ---------------------------------------------------------
def load_players():
    response = supabase.table("players").select("*").order("name").execute()
    return response.data if response.data else []


def add_player(name):
    supabase.table("players").insert({"name": name}).execute()


CORE_PLAYERS = ["Michael L.", "Connor R.", "Devin P.", "Cody R.", "Preston R."]


def ensure_core_players():
    existing = [p["name"] for p in load_players()]
    for name in CORE_PLAYERS:
        if name not in existing:
            add_player(name)


ensure_core_players()
players = load_players()
player_names = [p["name"] for p in players]


# ---------------------------------------------------------
# Checkbox grid helper
# ---------------------------------------------------------
def checkbox_grid(label, options, key_prefix, columns=2):
    st.write(f"### {label}")
    selected = []

    rows = (len(options) + columns - 1) // columns
    idx = 0

    for _ in range(rows):
        cols = st.columns(columns)
        for c in range(columns):
            if idx < len(options):
                name = options[idx]
                checked = cols[c].checkbox(name, key=f"{key_prefix}_{name}")
                if checked:
                    selected.append(name)
                idx += 1

    return selected


# ---------------------------------------------------------
# Initialize session state for players_in_tonights_game
# ---------------------------------------------------------
if "players_in_tonights_game" not in st.session_state:
    st.session_state["players_in_tonights_game"] = []


# ---------------------------------------------------------
# UI: Log a hand (always at the top)
# ---------------------------------------------------------
st.title("Poker Night Tracker")
st.header("Log a Hand")

players_in_game = st.session_state["players_in_tonights_game"]


# ---------------------------------------------------------
# Log Hand fields (ABOVE the visible dropdown)
# ---------------------------------------------------------
if not players_in_game:
    st.info("Select players in tonight's game to begin logging a hand.")
else:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Winner")
        winner = st.radio("", players_in_game, key="winner_radio")

    with col2:
        st.subheader("Street")
        streets = ["Preflop", "Flop", "Turn", "River"]
        street = st.radio("", streets, key="street_radio")

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Hand Type")
        hand_types = [
            "High Card", "Pair", "Two Pair", "Trips", "Straight",
            "Flush", "Full House", "Quads", "Straight Flush", "No Showdown"
        ]
        hand_type = st.radio("", hand_types, key="handtype_radio")

    with col4:
        st.subheader("Pot Size")
        pot_sizes = ["S", "M", "L"]
        pot_size = st.radio("", pot_sizes, key="potsize_radio")

    st.subheader("All-In")
    all_in = st.checkbox("All-In", key="allin_toggle")

    showdown_losers = []
    if street == "River" and hand_type != "No Showdown":
        showdown_losers = checkbox_grid(
            "Showdown Losers",
            players_in_game,
            key_prefix="losers",
            columns=2
        )

    eliminated_player = None
    if all_in:
        eliminated_list = checkbox_grid(
            "Eliminated Player",
            players_in_game,
            key_prefix="elim",
            columns=2
        )
        if len(eliminated_list) > 0:
            eliminated_player = eliminated_list[0]

    st.subheader("Game Name")
    game_name = st.text_input("", value=f"{datetime.now():%B %Y} Poker Night")

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
            "game_name": game_name,
            "created_at": datetime.utcnow().isoformat(),
        }
        supabase.table("hands").insert(data).execute()
        st.success("Hand logged!")
        st.rerun()


# ---------------------------------------------------------
# Hand History (simple feed)
# ---------------------------------------------------------
st.header("Hand History")

hands = (
    supabase.table("hands")
    .select("*")
    .eq("game_name", game_name if "game_name" in locals() else "")
    .order("created_at", desc=True)
    .execute()
    .data
)

if not hands:
    st.info("No hands logged yet.")
else:
    total_hands = len(hands)

    for index, h in enumerate(hands):
        hand_number = total_hands - index  # Hand #1 is oldest
        winner = h["winner"]
        hand_type = h["hand_type"]

        st.write(f"**Hand #{hand_number} — {winner} won with {hand_type}**")


# ---------------------------------------------------------
# VISIBLE DROPDOWN (ONLY ONE WIDGET)
# ---------------------------------------------------------
with st.expander("Players in Tonight's Game"):
    st.multiselect(
        "Select players in tonight's game:",
        options=player_names,
        key="players_in_tonights_game"
    )


# ---------------------------------------------------------
# Add Player (collapsible)
# ---------------------------------------------------------
with st.expander("Add Player"):
    new_player = st.text_input("New Player Name")
    if st.button("Add Player"):
        if new_player.strip():
            add_player(new_player.strip())
            st.success(f"Added {new_player}")
            st.rerun()