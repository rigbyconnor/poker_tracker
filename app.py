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
# UI: Log a hand (polished native layout)
# ---------------------------------------------------------
st.header("Log a Hand")

with st.container():
    st.subheader("Winner")
    winner = st.radio("", player_names, key="winner_radio")

    st.subheader("Street")
    streets = ["Preflop", "Flop", "Turn", "River", "Showdown"]
    street = st.radio("", streets, key="street_radio")

    st.subheader("Hand Type")
    hand_types = [
        "High Card", "Pair", "Two Pair", "Trips", "Straight",
        "Flush", "Full House", "Quads", "Straight Flush"
    ]
    hand_type = st.radio("", hand_types, key="handtype_radio")

    st.subheader("Pot Size")
    pot_sizes = ["S", "M", "L"]
    pot_size = st.radio("", pot_sizes, key="potsize_radio")

    st.subheader("Showdown Losers")
    showdown_losers = st.multiselect("", player_names, key="losers_multi")

    st.subheader("Eliminated Player (optional)")
    eliminated = st.selectbox("", ["None"] + player_names, key="elim_select")
    eliminated = None if eliminated == "None" else eliminated

    st.subheader("Players in Game")
    players_in_game = st.multiselect("", player_names, default=player_names, key="playersingame_multi")

    st.subheader("Game Name")
    game_name = st.text_input("", value=f"{datetime.now():%B %Y} Poker Night")


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