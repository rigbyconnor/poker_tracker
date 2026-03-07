import json
from pathlib import Path
import sqlite3
from datetime import datetime

import streamlit as st

# ---------------------------------------------------------
# App Setup
# ---------------------------------------------------------

st.set_page_config(page_title="Poker Night Tracker", layout="centered")

PLAYERS_FILE = Path("players.json")
DB_FILE = Path("poker_night.db")

# ---------------------------------------------------------
# Player Persistence
# ---------------------------------------------------------

def load_players() -> list[str]:
    if PLAYERS_FILE.exists():
        with open(PLAYERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return ["Connor", "Cody", "Devin", "Michael", "Preston", "Tim"]

def save_players(players: list[str]) -> None:
    with open(PLAYERS_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)

# ---------------------------------------------------------
# SQLite Helpers
# ---------------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hand_number INTEGER,
            created_at TEXT NOT NULL,
            winner TEXT NOT NULL,
            street TEXT NOT NULL,
            hand_type TEXT NOT NULL,
            pot_size TEXT NOT NULL,
            all_in INTEGER NOT NULL,
            eliminated_player TEXT,
            showdown_losers TEXT NOT NULL,
            players_in_game TEXT NOT NULL,
            game_name TEXT
        )
        """
    )

    # Ensure new column exists
    cur.execute("PRAGMA table_info(hands)")
    cols = [row[1] for row in cur.fetchall()]
    if "hand_number" not in cols:
        cur.execute("ALTER TABLE hands ADD COLUMN hand_number INTEGER")

    conn.commit()
    conn.close()

def get_next_hand_number(game_name: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(hand_number) FROM hands WHERE game_name = ?", (game_name,))
    result = cur.fetchone()[0]
    conn.close()
    return 1 if result is None else result + 1

def save_hand_to_db(hand_record: dict) -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO hands (
            hand_number,
            created_at,
            winner,
            street,
            hand_type,
            pot_size,
            all_in,
            eliminated_player,
            showdown_losers,
            players_in_game,
            game_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            hand_record["hand_number"],
            datetime.utcnow().isoformat(),
            hand_record["winner"],
            hand_record["street"],
            hand_record["hand_type"],
            hand_record["pot_size"],
            1 if hand_record["all_in"] else 0,
            json.dumps(hand_record["eliminated_player"]),
            json.dumps(hand_record["showdown_losers"]),
            json.dumps(hand_record["players_in_game"]),
            hand_record["game_name"],
        ),
    )

    conn.commit()
    conn.close()

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------

if "all_players" not in st.session_state:
    st.session_state.all_players = load_players()

if "game_players" not in st.session_state:
    st.session_state.game_players = ["Connor", "Cody", "Devin"]

if "form_version" not in st.session_state:
    st.session_state.form_version = 0

if "new_player_name" not in st.session_state:
    st.session_state.new_player_name = ""

if "selected_month" not in st.session_state:
    st.session_state.selected_month = ""

# Initialize DB
init_db()

# ---------------------------------------------------------
# TITLE (only after month is selected)
# ---------------------------------------------------------

selected_month = st.session_state.selected_month

if selected_month:
    current_year = datetime.now().year
    game_name = f"{selected_month} {current_year} Poker Night"
    st.title(game_name)

# ---------------------------------------------------------
# LOG HAND (directly under title)
# ---------------------------------------------------------

if selected_month:
    st.header("Log a Hand")

    suffix = f"_{st.session_state.form_version}"

    winner = st.pills(
        "Winner",
        st.session_state.game_players,
        selection_mode="single",
        key=f"winner{suffix}"
    )

    street = st.pills(
        "Street Ended",
        ["Preflop", "Flop", "Turn", "River"],
        selection_mode="single",
        key=f"street{suffix}"
    )

    hand_type = st.pills(
        "Winning Hand",
        [
            "No Showdown",
            "High Card",
            "Pair",
            "Two Pair",
            "Trips",
            "Straight",
            "Flush",
            "Full House",
            "Quads",
            "Straight Flush"
        ],
        selection_mode="single",
        key=f"hand_type{suffix}"
    )

    pot_size = st.pills(
        "Pot Size",
        ["Small", "Medium", "Large"],
        selection_mode="single",
        key=f"pot_size{suffix}"
    )

    all_in = st.checkbox("All In", key=f"all_in{suffix}")

    eliminated_player = []
    if all_in and winner:
        elimination_options = [p for p in st.session_state.game_players if p != winner]
        eliminated_player = st.pills(
            "Eliminated Player(s)",
            elimination_options,
            selection_mode="multi",
            key=f"eliminated{suffix}"
        )

    showdown_allowed = (
        street == "River"
        and hand_type is not None
        and hand_type != "No Showdown"
        and winner is not None
    )

    losers = []
    if showdown_allowed:
        loser_options = [p for p in st.session_state.game_players if p != winner]
        losers = st.pills(
            "Showdown Losers",
            loser_options,
            selection_mode="multi",
            key=f"losers{suffix}"
        )
    else:
        st.caption("Showdown losers only appear for river showdowns with a real shown hand.")

    if st.button("Log Hand", key=f"log_hand{suffix}"):
        if not winner or not street or not hand_type or not pot_size:
            st.error("Please fill out winner, street, winning hand, and pot size.")
        else:
            next_hand_number = get_next_hand_number(game_name)

            hand_record = {
                "hand_number": next_hand_number,
                "winner": winner,
                "street": street,
                "hand_type": hand_type,
                "pot_size": pot_size,
                "all_in": all_in,
                "eliminated_player": eliminated_player,
                "showdown_losers": losers,
                "players_in_game": st.session_state.game_players,
                "game_name": game_name,
            }

            save_hand_to_db(hand_record)

            st.success(f"Hand #{next_hand_number} logged.")
            st.write(hand_record)

            st.session_state.form_version += 1
            st.rerun()

    # ---------------------------------------------------------
    # HAND TRACKER — LIVE FEED + FULL TABLE
    # ---------------------------------------------------------

    st.divider()
    st.header("Hand Tracker")

    conn = get_connection()
    cur = conn.cursor()

    # Fetch last 10 hands for this game
    cur.execute("""
        SELECT hand_number, winner, street, hand_type, pot_size, all_in,
               eliminated_player, showdown_losers
        FROM hands
        WHERE game_name = ?
        ORDER BY hand_number DESC
        LIMIT 10
    """, (game_name,))
    recent_hands = cur.fetchall()

    # -------------------------
    # LIVE FEED (Last 10 Hands)
    # -------------------------

    st.subheader("Recent Hands")

    if recent_hands:
        for hand in recent_hands:
            eliminated = json.loads(hand["eliminated_player"]) if hand["eliminated_player"] else []
            showdown_losers = json.loads(hand["showdown_losers"]) if hand["showdown_losers"] else []

            line = (
                f"**Hand #{hand['hand_number']}** — {hand['winner']} won with "
                f"**{hand['hand_type']}** on the **{hand['street']}** "
                f"({hand['pot_size']} pot)"
            )

            if hand["all_in"]:
                line += " — **All‑In**"

            if eliminated:
                line += f" — Eliminated: {', '.join(eliminated)}"

            if showdown_losers:
                line += f" — Showdown Losers: {', '.join(showdown_losers)}"

            st.markdown(line)
    else:
        st.caption("No hands logged yet.")

    # -------------------------
    # FULL TABLE VIEW
    # -------------------------

    with st.expander("Full Hand History"):
        cur.execute("""
            SELECT hand_number, created_at, winner, street, hand_type, pot_size, all_in,
                   eliminated_player, showdown_losers
            FROM hands
            WHERE game_name = ?
            ORDER BY hand_number DESC
        """, (game_name,))
        rows = cur.fetchall()

        if rows:
            import pandas as pd

            columns = [
                "hand_number",
                "created_at",
                "winner",
                "street",
                "hand_type",
                "pot_size",
                "all_in",
                "eliminated_player",
                "showdown_losers"
            ]

            df = pd.DataFrame(rows, columns=columns)

            def parse_list(val):
                if not val:
                    return ""
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return ", ".join(parsed)
                    return str(parsed)
                except:
                    return str(val)

            df["eliminated_player"] = df["eliminated_player"].apply(parse_list)
            df["showdown_losers"] = df["showdown_losers"].apply(parse_list)
            df["all_in"] = df["all_in"].apply(lambda x: "Yes" if int(x) == 1 else "No")

            # Remove timestamp from display
            df_display = df.drop(columns=["created_at"])

            # Hide index column
            st.dataframe(df_display, use_container_width=True, hide_index=True)

        else:
            st.caption("No hands logged yet.")

    conn.close()

# ---------------------------------------------------------
# SELECT PLAYERS (always visible)
# ---------------------------------------------------------

st.divider()
st.header("Select Players in This Game")

selected_players = st.multiselect(
    "Who is playing tonight?",
    st.session_state.all_players,
    default=st.session_state.game_players,
    key="game_players_multiselect"
)

st.session_state.game_players = selected_players

with st.expander("Add a new player / guest"):
    st.text_input("New player name", key="new_player_name")
    if st.button("Add Player"):
        new_player = st.session_state.new_player_name.strip()
        if new_player and new_player not in st.session_state.all_players:
            st.session_state.all_players.append(new_player)
            st.session_state.all_players = sorted(st.session_state.all_players)
            save_players(st.session_state.all_players)
            st.success(f"Added {new_player}")
        st.session_state.new_player_name = ""

# ---------------------------------------------------------
# MONTH SELECTOR (bottom of flow)
# ---------------------------------------------------------

st.divider()
st.header("Select Poker Night Month")

months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

new_month = st.selectbox(
    "Select Month",
    [""] + months,
    index=([""] + months).index(selected_month) if selected_month else 0
)

if new_month != selected_month:
    st.session_state.selected_month = new_month
    st.rerun()

if not selected_month:
    st.stop()