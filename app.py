import streamlit as st
from supabase import create_client
from datetime import datetime

# Connect to Supabase using Streamlit secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

st.set_page_config(page_title="Poker Night Tracker", layout="centered")

st.title("Poker Night Tracker")

# ---------------------------
# Helper: Insert a hand
# ---------------------------
def insert_hand(data):
    response = supabase.table("hands").insert(data).execute()
    return response


# ---------------------------
# Helper: Fetch all hands
# ---------------------------
def fetch_hands():
    response = supabase.table("hands").select("*").order("id", desc=True).execute()
    return response.data


# ---------------------------
# UI: Log a new hand
# ---------------------------
st.header("Log a Hand")

hand_number = st.number_input("Hand Number", min_value=1, step=1)
winner = st.text_input("Winner")
street = st.selectbox("Street", ["Preflop", "Flop", "Turn", "River", "Showdown"])
hand_type = st.text_input("Hand Type (e.g., Flush, Two Pair)")
pot_size = st.text_input("Pot Size")
all_in = st.checkbox("All-In?")
eliminated_player = st.text_input("Eliminated Player (optional)")
showdown_losers = st.text_input("Showdown Losers (comma-separated)")
players_in_game = st.text_input("Players in Game (comma-separated)")
game_name = st.text_input("Game Name", value=f"{datetime.now():%B %Y} Poker Night")

if st.button("Submit Hand"):
    data = {
        "hand_number": hand_number,
        "winner": winner,
        "street": street,
        "hand_type": hand_type,
        "pot_size": pot_size,
        "all_in": all_in,
        "eliminated_player": eliminated_player.split(",") if eliminated_player else None,
        "showdown_losers": showdown_losers.split(",") if showdown_losers else None,
        "players_in_game": players_in_game.split(",") if players_in_game else [],
        "game_name": game_name,
        "created_at": datetime.utcnow().isoformat()
    }

    insert_hand(data)
    st.success("Hand logged successfully!")


# ---------------------------
# UI: Display hand history
# ---------------------------
st.header("Hand History")

hands = fetch_hands()

if not hands:
    st.info("No hands logged yet.")
else:
    st.dataframe(hands)