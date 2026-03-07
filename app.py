import streamlit as st
from supabase import create_client
from datetime import datetime

# ---------------------------------------------------------
# Supabase Connection
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

st.set_page_config(page_title="Poker Night Tracker", layout="centered")


# ---------------------------------------------------------
# Database Helpers
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
# CLICKABLE PILL SYSTEM (HTML‑safe, final)
# ---------------------------------------------------------
def chip_row(label, options, selected, multi=False, key_prefix=""):
    st.write(f"### {label}")

    container = st.container()

    # Read query params (new Streamlit API)
    params = dict(st.query_params)
    clicked = params.get(f"{key_prefix}_clicked", None)

    # Update selection
    if clicked in options:
        if multi:
            if clicked in selected:
                selected.remove(clicked)
            else:
                selected.append(clicked)
        else:
            selected.clear()
            selected.append(clicked)

        # Clear the click param
        if f"{key_prefix}_clicked" in st.query_params:
            st.query_params.pop(f"{key_prefix}_clicked")

    # Build pills
    html_parts = ["<div style='display:flex;flex-wrap:wrap;gap:6px;'>"]

    for opt in options:
        is_selected = opt in selected

        bg = "#4CAF50" if is_selected else "#FFFFFF"
        color = "#FFFFFF" if is_selected else "#555555"
        shadow = "" if is_selected else "box-shadow:0px 1px 3px rgba(0,0,0,0.15);"

        pill = f"""
        <a href='?{key_prefix}_clicked={opt}' style='text-decoration:none;'>
            <div style="
                background:{bg};
                color:{color};
                padding:8px 14px;
                border-radius:10px;
                font-size:16px;
                {shadow}
                display:inline-block;
            ">
                {opt}
            </div>
        </a>
        """

        html_parts.append(pill)

    html_parts.append("</div>")
    html = "\n".join(html_parts)

    # FORCE HTML RENDERING — this is the key
    container.markdown(html, unsafe_allow_html=True)

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


# ---------------------------------------------------------
# UI: Log a Hand
# ---------------------------------------------------------
st.header("Log a Hand")

# Winner
winner = st.session_state.get("winner", [])
winner = chip_row("Winner", player_names, winner, multi=False, key_prefix="winner")

# Street
streets = ["Preflop", "Flop", "Turn", "River", "Showdown"]
street = st.session_state.get("street", [])
street = chip_row("Street", streets, street, multi=False, key_prefix="street")

# Hand Type
hand_types = [
    "High Card", "Pair", "Two Pair", "Trips", "Straight",
    "Flush", "Full House", "Quads", "Straight Flush"
]
hand_type = st.session_state.get("hand_type", [])
hand_type = chip_row("Hand Type", hand_types, hand_type, multi=False, key_prefix="handtype")

# Pot Size
pot_sizes = ["S", "M", "L"]
pot_size = st.session_state.get("pot_size", [])
pot_size = chip_row("Pot Size", pot_sizes, pot_size, multi=False, key_prefix="potsize")

# Showdown Losers
showdown_losers = st.session_state.get("showdown_losers", [])
showdown_losers = chip_row("Showdown Losers", player_names, showdown_losers, multi=True, key_prefix="losers")

# Eliminated Player
eliminated = st.session_state.get("eliminated", [])
eliminated = chip_row("Eliminated Player (optional)", player_names, eliminated, multi=False, key_prefix="elim")

# Players in Game
players_in_game = st.session_state.get("players_in_game", player_names.copy())
players_in_game = chip_row("Players in Game", player_names, players_in_game, multi=True, key_prefix="playersingame")

# Game Name
game_name = st.text_input("Game Name", value=f"{datetime.now():%B %Y} Poker Night")


# ---------------------------------------------------------
# Submit Hand
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