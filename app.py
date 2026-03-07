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
# Chip-like helpers (native widgets)
# ---------------------------------------------------------
def chip_row_single(label, options, state_key):
    st.write(f"### {label}")
    if state_key not in st.session_state:
        st.session_state[state_key] = None

    selected = st.session_state[state_key]

    cols = st.columns(len(options)) if len(options) <= 4 else st.columns(4)

    for i, opt in enumerate(options):
        col = cols[i % len(cols)]
        is_selected = (opt == selected)
        # D: "green selected, white unselected" – we emulate via label
        label_text = f"✅ {opt}" if is_selected else opt
        if col.button(label_text, key=f"{state_key}_{opt}"):
            selected = opt
            st.session_state[state_key] = opt

    return selected


def chip_row_multi(label, options, state_key):
    st.write(f"### {label}")
    if state_key not in st.session_state:
        st.session_state[state_key] = []

    selected = st.session_state[state_key]

    cols = st.columns(4 if len(options) >= 4 else len(options))

    for i, opt in enumerate(options):
        col = cols[i % len(cols)]
        is_selected = opt in selected
        label_text = f"✅ {opt}" if is_selected else opt
        if col.button(label_text, key=f"{state_key}_{opt}"):
            if is_selected:
                selected = [x for x in selected if x != opt]
            else:
                selected = selected + [opt]
            st.session_state[state_key] = selected

    return selected


# ---------------------------------------------------------
# UI: Add player
# ---------------------------------------------------------
st.title("Poker Night Tracker")

with st.expander("Add Player"):
    new_player = st.text_input("New Player Name")
    if st.button("Add Player"):
        if new_player.strip():
            add_player(new_player.strip())
            st.success(f"Added {new_player}")
            st.rerun()


# ---------------------------------------------------------
# UI: Log a hand
# ---------------------------------------------------------
st.header("Log a Hand")

# Winner (single-select chips)
winner = chip_row_single("Winner", player_names, "winner_chip")

# Street (single-select chips)
streets = ["Preflop", "Flop", "Turn", "River", "Showdown"]
street = chip_row_single("Street", streets, "street_chip")

# Hand type (single-select chips)
hand_types = [
    "High Card", "Pair", "Two Pair", "Trips", "Straight",
    "Flush", "Full House", "Quads", "Straight Flush"
]
hand_type = chip_row_single("Hand Type", hand_types, "handtype_chip")

# Pot size (single-select chips)
pot_sizes = ["S", "M", "L"]
pot_size = chip_row_single("Pot Size", pot_sizes, "potsize_chip")

# Showdown losers (multi-select chips)
showdown_losers = chip_row_multi("Showdown Losers", player_names, "losers_chip")

# Eliminated player (single-select chips, optional)
eliminated = chip_row_single("Eliminated Player (optional)", player_names, "elim_chip")

# Players in game (multi-select chips)
players_in_game = chip_row_multi("Players in Game", player_names, "playersingame_chip")

# Game name
game_name = st.text_input("Game Name", value=f"{datetime.now():%B %Y} Poker Night")


# ---------------------------------------------------------
# Submit hand
# ---------------------------------------------------------
if st.button("Submit Hand", type="primary"):
    if not winner:
        st.error("Select a winner")
    elif not street:
        st.error("Select a street")
    elif not hand_type:
        st.error("Select a hand type")
    elif not pot_size:
        st.error("Select a pot size")
    else:
        data = {
            "hand_number": int(datetime.utcnow().timestamp()),
            "winner": winner,
            "street": street,
            "hand_type": hand_type,
            "pot_size": pot_size,
            "all_in": False,
            "eliminated_player": eliminated if eliminated else None,
            "showdown_losers": showdown_losers,
            "players_in_game": players_in_game,
            "game_name": game_name,
            "created_at": datetime.utcnow().isoformat(),
        }
        supabase.table("hands").insert(data).execute()
        st.success("Hand logged!")
        st.rerun()


# ---------------------------------------------------------
# Hand history
# ---------------------------------------------------------
st.header("Hand History")

hands = supabase.table("hands").select("*").order("id", desc=True).execute().data

if not hands:
    st.info("No hands logged yet.")
else:
    for h in hands:
        st.markdown(
            f"""
            <div style='padding:12px;border-radius:10px;background:#f7f7f7;margin-bottom:10px;'>
                <strong>Winner:</strong> {h['winner']}<br>
                <strong>Street:</strong> {h['street']}<br>
                <strong>Hand:</strong> {h['hand_type']}<br>
                <strong>Pot:</strong> {h['pot_size']}<br>
                <strong>Game:</strong> {h['game_name']}<br>
                <small>{h['created_at']}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )