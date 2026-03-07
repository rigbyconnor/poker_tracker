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
# CHIP HELPERS
# ---------------------------------------------------------

def chip_single(label, options, key):
    """Single-select chip row using segmented control."""
    st.write(f"### {label}")
    return st.segmented_control(
        key=key,
        options=options,
        selection_mode="single"
    )


def chip_multi(label, options, key):
    """Multi-select chip row using fast toggle buttons."""
    st.write(f"### {label}")

    if key not in st.session_state:
        st.session_state[key] = []

    selected = st.session_state[key]

    cols = st.columns(4)

    for i, opt in enumerate(options):
        col = cols[i % 4]
        is_selected = opt in selected

        # Slightly rounded rectangle chip look
        style = (
            "background-color:#4CAF50;color:white;border-radius:8px;padding:6px 12px;"
            if is_selected else
            "background-color:#EEEEEE;color:#333;border-radius:8px;padding:6px 12px;"
        )

        if col.button(opt, key=f"{key}_{opt}", help="", use_container_width=True):
            if is_selected:
                selected = [x for x in selected if x != opt]
            else:
                selected = selected + [opt]
            st.session_state[key] = selected

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
# UI: Log a hand (CHIP UI)
# ---------------------------------------------------------
st.header("Log a Hand")

winner = chip_single("Winner", player_names, "winner_chip")

streets = ["Preflop", "Flop", "Turn", "River", "Showdown"]
street = chip_single("Street", streets, "street_chip")

hand_types = [
    "High Card", "Pair", "Two Pair", "Trips", "Straight",
    "Flush", "Full House", "Quads", "Straight Flush"
]
hand_type = chip_single("Hand Type", hand_types, "handtype_chip")

pot_sizes = ["S", "M", "L"]
pot_size = chip_single("Pot Size", pot_sizes, "potsize_chip")

showdown_losers = chip_multi("Showdown Losers", player_names, "losers_chip")

eliminated = chip_single("Eliminated Player (optional)", ["None"] + player_names, "elim_chip")
eliminated = None if eliminated == "None" else eliminated

players_in_game = chip_multi("Players in Game", player_names, "playersingame_chip")

game_name = st.text_input("Game Name", value=f"{datetime.now():%B %Y} Poker Night")


# ---------------------------------------------------------
# Submit hand
# ---------------------------------------------------------
if st.button("Submit Hand", type="primary"):
    data = {
        "hand_number": int(datetime.utcnow().timestamp()),
        "winner": winner,
        "street": street,
        "hand_type": hand_type,
        "pot_size": pot_size,
        "all_in": False,
        "eliminated_player": eliminated,
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