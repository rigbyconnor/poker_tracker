import streamlit as st
from supabase import create_client
from datetime import datetime

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

st.set_page_config(page_title="Poker Night Tracker", layout="centered")

# ---------------------------------------------------------
# Load players from Supabase
# ---------------------------------------------------------
def load_players():
    response = supabase.table("players").select("*").order("name").execute()
    return response.data if response.data else []

def add_player(name):
    supabase.table("players").insert({"name": name}).execute()

# Preloaded core players
CORE_PLAYERS = ["Michael L.", "Connor R.", "Devin P.", "Cody R.", "Preston R."]

def ensure_core_players():
    existing = [p["name"] for p in load_players()]
    for name in CORE_PLAYERS:
        if name not in existing:
            add_player(name)

ensure_core_players()
players = load_players()

# ---------------------------------------------------------
# UI Helpers — CLICKABLE PILLS
# ---------------------------------------------------------
def chip_row(options, selected, multi=False, key_prefix=""):
    st.write("")  # spacing
    cols = st.columns(len(options))

    for i, opt in enumerate(options):
        is_selected = opt in selected

        # Style for selected vs unselected
        style = (
            "padding:10px 16px;border-radius:20px;margin:4px;font-size:16px;"
            "border:1px solid #ccc;cursor:pointer;text-align:center;"
        )
        if is_selected:
            style += "background-color:#4CAF50;color:white;border-color:#4CAF50;"
        else:
            style += "background-color:#f2f2f2;color:#333;"

        # Render pill as a button
        if cols[i].button(opt, key=f"{key_prefix}_{opt}"):
            if multi:
                if opt in selected:
                    selected.remove(opt)
                else:
                    selected.append(opt)
            else:
                selected.clear()
                selected.append(opt)

        # Display pill
        cols[i].markdown(f"<div style='{style}'>{opt}</div>", unsafe_allow_html=True)

    return selected

# ---------------------------------------------------------
# UI: Add Player
# ---------------------------------------------------------
st.title("Poker Night Tracker")

with st.expander("Add Player"):
    new_player = st.text_input("New Player Name")
    if st.button("Add Player"):
        if new_player.strip():
            add_player(new_player.strip())
            st.success(f"Added {new_player}")
            st.rerun()

players = load_players()
player_names = [p["name"] for p in players]

# ---------------------------------------------------------
# UI: Log a Hand
# ---------------------------------------------------------
st.header("Log a Hand")

# Winner
st.subheader("Winner")
winner = st.session_state.get("winner", [])
winner = chip_row(player_names, winner, multi=False, key_prefix="winner")

# Street
st.subheader("Street")
streets = ["Preflop", "Flop", "Turn", "River", "Showdown"]
street = st.session_state.get("street", [])
street = chip_row(streets, street, multi=False, key_prefix="street")

# Hand Type
st.subheader("Hand Type")
hand_types = ["High Card", "Pair", "Two Pair", "Trips", "Straight", "Flush", "Full House", "Quads", "Straight Flush"]
hand_type = st.session_state.get("hand_type", [])
hand_type = chip_row(hand_types, hand_type, multi=False, key_prefix="handtype")

# Pot Size
st.subheader("Pot Size")
pot_sizes = ["S", "M", "L"]
pot_size = st.session_state.get("pot_size", [])
pot_size = chip_row(pot_sizes, pot_size, multi=False, key_prefix="potsize")

# Showdown Losers
st.subheader("Showdown Losers")
showdown_losers = st.session_state.get("showdown_losers", [])
showdown_losers = chip_row(player_names, showdown_losers, multi=True, key_prefix="losers")

# Eliminated Player
st.subheader("Eliminated Player (optional)")
eliminated = st.session_state.get("eliminated", [])
eliminated = chip_row(player_names, eliminated, multi=False, key_prefix="elim")

# Players in Game
st.subheader("Players in Game")
players_in_game = st.session_state.get("players_in_game", player_names.copy())
players_in_game = chip_row(player_names, players_in_game, multi=True, key_prefix="playersingame")

# Game Name
game_name = st.text_input("Game Name", value=f"{datetime.now():%B %Y} Poker Night")

# Submit
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
            "winner": winner[0],
            "street": street[0],
            "hand_type": hand_type[0],
            "pot_size": pot_size[0],
            "all_in": False,
            "eliminated_player": eliminated[0] if eliminated else None,
            "showdown_losers": showdown_losers,
            "players_in_game": players_in_game,
            "game_name": game_name,
            "created_at": datetime.utcnow().isoformat(),
        }
        supabase.table("hands").insert(data).execute()
        st.success("Hand logged!")
        st.rerun()

# ---------------------------------------------------------
# Hand History
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