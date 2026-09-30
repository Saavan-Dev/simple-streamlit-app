import streamlit as st
import logging
import random
import string
from datetime import date, datetime, timedelta
from io import BytesIO
from gtts import gTTS

# configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------------- Config ----------------
MOVIES = {
    "The Last Lighthouse": {"emoji": "🌊", "genre": "Drama", "duration": "2h 10m", "rating": "U/A", "base_price": 180},
    "Neon Streets": {"emoji": "🌃", "genre": "Action / Thriller", "duration": "2h 25m", "rating": "A", "base_price": 220},
    "Galaxy Runners": {"emoji": "🚀", "genre": "Sci-Fi", "duration": "2h 40m", "rating": "U/A", "base_price": 250},
    "Laugh Out Loud": {"emoji": "😂", "genre": "Comedy", "duration": "1h 55m", "rating": "U", "base_price": 160},
    "Whispering Woods": {"emoji": "🌲", "genre": "Horror", "duration": "1h 50m", "rating": "A", "base_price": 200},
}

SHOWTIMES = ["10:00 AM", "01:30 PM", "05:00 PM", "09:00 PM"]

ROWS = list("ABCDEFGH")
SEATS_PER_ROW = 10

# Seat class by row: (name, price multiplier)
SEAT_CLASSES = {
    "A": ("Silver", 1.0), "B": ("Silver", 1.0), "C": ("Silver", 1.0),
    "D": ("Gold", 1.5), "E": ("Gold", 1.5), "F": ("Gold", 1.5),
    "G": ("Recliner", 2.2), "H": ("Recliner", 2.2),
}

CONVENIENCE_FEE = 30   # per ticket
GST_RATE = 0.18
MAX_SEATS_PER_BOOKING = 10


# ---------------- Helpers ----------------
def init_state():
    ss = st.session_state
    if "booked_seats" not in ss:
        ss.booked_seats = {}        # show_key -> set of seats
    if "bookings" not in ss:
        ss.bookings = []            # list of booking dicts
    if "seat_form_version" not in ss:
        ss.seat_form_version = 0    # bump to reset seat checkboxes
    if "last_booking" not in ss:
        ss.last_booking = None


def show_key(movie, show_date, show_time):
    return f"{movie}|{show_date.isoformat()}|{show_time}"


def seat_price(movie, seat):
    row = seat[0]
    return round(MOVIES[movie]["base_price"] * SEAT_CLASSES[row][1])


def sort_seats(seats):
    return sorted(seats, key=lambda s: (s[0], int(s[1:])))


def generate_booking_id():
    return "BK" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def calculate_bill(movie, seats):
    subtotal = sum(seat_price(movie, s) for s in seats)
    fee = CONVENIENCE_FEE * len(seats)
    gst = round((subtotal + fee) * GST_RATE, 2)
    total = round(subtotal + fee + gst, 2)
    return subtotal, fee, gst, total


@st.cache_data(show_spinner=False)
def text_to_speech(text, lang="en"):
    """Convert text to MP3 bytes with gTTS."""
    try:
        logging.info("Generating booking confirmation audio")
        tts = gTTS(text=text, lang=lang)
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        logging.error(f"gTTS Error: {e}")
        return None


def build_ticket_text(b):
    line = "=" * 40
    return (
        f"{line}\n"
        f"        🎬 CINEMAX MOVIE TICKET\n"
        f"{line}\n"
        f"Booking ID : {b['id']}\n"
        f"Name       : {b['name']}\n"
        f"Phone      : {b['phone']}\n"
        f"Movie      : {b['movie']}\n"
        f"Date       : {b['date']}\n"
        f"Showtime   : {b['time']}\n"
        f"Seats      : {', '.join(b['seats'])}\n"
        f"Tickets    : {len(b['seats'])}\n"
        f"{'-' * 40}\n"
        f"Subtotal   : Rs. {b['subtotal']:.2f}\n"
        f"Conv. fee  : Rs. {b['fee']:.2f}\n"
        f"GST (18%)  : Rs. {b['gst']:.2f}\n"
        f"TOTAL      : Rs. {b['total']:.2f}\n"
        f"{line}\n"
        f"Booked on  : {b['booked_at']}\n"
        f"Please arrive 15 minutes before showtime.\n"
    )


def show_confirmation(b):
    st.success(f"🎉 Booking confirmed! Your booking ID is **{b['id']}**")
    st.code(build_ticket_text(b), language=None)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Download ticket",
            data=build_ticket_text(b),
            file_name=f"ticket_{b['id']}.txt",
            mime="text/plain",
        )
    with col2:
        if st.button("🎟️ Book another ticket"):
            st.session_state.last_booking = None
            st.rerun()

    st.subheader("🔊 Audio confirmation")
    speech = (
        f"Booking confirmed for {b['name']}. "
        f"{len(b['seats'])} tickets for {b['movie']} on {b['date']} at {b['time']}. "
        f"Your seats are {', '.join(b['seats'])}. "
        f"Total amount is {b['total']:.0f} rupees. Enjoy your movie!"
    )
    with st.spinner("Generating audio..."):
        audio = text_to_speech(speech)
    if audio:
        st.audio(audio, format="audio/mp3")
    else:
        st.warning("Couldn't generate audio right now.")


# ---------------- Pages ----------------
def booking_page():
    ss = st.session_state

    if ss.last_booking:
        show_confirmation(ss.last_booking)
        return

    col1, col2, col3 = st.columns(3)
    movie = col1.selectbox("🎞️ Movie", list(MOVIES.keys()))
    show_date = col2.date_input(
        "📅 Date",
        value=date.today(),
        min_value=date.today(),
        max_value=date.today() + timedelta(days=6),
    )
    show_time = col3.selectbox("⏰ Showtime", SHOWTIMES)

    info = MOVIES[movie]
    st.markdown(f"## {info['emoji']} {movie}")
    st.caption(f"{info['genre']} • {info['duration']} • Rated {info['rating']}")

    # Price legend
    st.markdown(
        f"**Silver** (A–C): ₹{round(info['base_price'] * 1.0)} &nbsp;|&nbsp; "
        f"**Gold** (D–F): ₹{round(info['base_price'] * 1.5)} &nbsp;|&nbsp; "
        f"**Recliner** (G–H): ₹{round(info['base_price'] * 2.2)}"
    )

    key = show_key(movie, show_date, show_time)
    booked = ss.booked_seats.get(key, set())
    v = ss.seat_form_version

    st.subheader("💺 Select your seats")
    st.markdown(
        "<div style='text-align:center; padding:6px; margin-bottom:12px; "
        "background:linear-gradient(90deg,#444,#aaa,#444); color:white; "
        "border-radius:6px; font-weight:bold; letter-spacing:6px;'>SCREEN</div>",
        unsafe_allow_html=True,
    )
    st.caption("Greyed-out seats are already booked.")

    selected = []
    for row in ROWS:
        cols = st.columns([0.6] + [1] * SEATS_PER_ROW)
        cols[0].markdown(f"**{row}**")
        for n in range(1, SEATS_PER_ROW + 1):
            seat = f"{row}{n}"
            with cols[n]:
                widget_key = f"{key}|{seat}|{v}"
                if seat in booked:
                    st.checkbox(seat, value=True, disabled=True, key=widget_key)
                elif st.checkbox(seat, key=widget_key):
                    selected.append(seat)

    st.divider()

    if not selected:
        st.info("Select one or more seats to continue.")
        return

    selected = sort_seats(selected)
    subtotal, fee, gst, total = calculate_bill(movie, selected)

    st.subheader("🧾 Booking summary")
    left, right = st.columns(2)
    with left:
        st.write(f"**Seats:** {', '.join(selected)}")
        st.write(f"**Tickets:** {len(selected)}")
        for s in selected:
            st.write(f"- {s} ({SEAT_CLASSES[s[0]][0]}): ₹{seat_price(movie, s)}")
    with right:
        st.write(f"Subtotal: ₹{subtotal:.2f}")
        st.write(f"Convenience fee: ₹{fee:.2f}")
        st.write(f"GST (18%): ₹{gst:.2f}")
        st.markdown(f"### Total: ₹{total:.2f}")

    st.subheader("👤 Your details")
    name = st.text_input("Full name")
    phone = st.text_input("Phone number (10 digits)")

    if st.button("✅ Confirm booking", type="primary"):
        if not name.strip():
            st.error("Please enter your name.")
        elif not (phone.isdigit() and len(phone) == 10):
            st.error("Please enter a valid 10-digit phone number.")
        elif len(selected) > MAX_SEATS_PER_BOOKING:
            st.error(f"You can book at most {MAX_SEATS_PER_BOOKING} seats at once.")
        else:
            booking = {
                "id": generate_booking_id(),
                "name": name.strip(),
                "phone": phone,
                "movie": movie,
                "date": show_date.strftime("%A, %d %B %Y"),
                "time": show_time,
                "show_key": key,
                "seats": selected,
                "subtotal": subtotal,
                "fee": fee,
                "gst": gst,
                "total": total,
                "booked_at": datetime.now().strftime("%d-%m-%Y %H:%M"),
            }
            ss.booked_seats.setdefault(key, set()).update(selected)
            ss.bookings.append(booking)
            ss.last_booking = booking
            ss.seat_form_version += 1   # clears the checkboxes
            logging.info(f"Booking {booking['id']} confirmed: {movie} {key} seats={selected}")
            st.rerun()


def my_bookings_page():
    ss = st.session_state
    if not ss.bookings:
        st.info("You haven't booked any tickets yet.")
        return

    st.write(f"You have **{len(ss.bookings)}** booking(s).")
    for b in reversed(ss.bookings):
        with st.expander(f"{b['id']} — {b['movie']} • {b['date']} • {b['time']}"):
            st.code(build_ticket_text(b), language=None)
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "⬇️ Download",
                    data=build_ticket_text(b),
                    file_name=f"ticket_{b['id']}.txt",
                    mime="text/plain",
                    key=f"dl_{b['id']}",
                )
            with c2:
                if st.button("❌ Cancel booking", key=f"cancel_{b['id']}"):
                    ss.booked_seats.get(b["show_key"], set()).difference_update(b["seats"])
                    ss.bookings = [x for x in ss.bookings if x["id"] != b["id"]]
                    if ss.last_booking and ss.last_booking["id"] == b["id"]:
                        ss.last_booking = None
                    ss.seat_form_version += 1
                    logging.info(f"Booking {b['id']} cancelled")
                    st.rerun()


def main():
    st.set_page_config(page_title="Movie Ticket Booking", page_icon="🎬", layout="wide")
    init_state()

    st.title("🎬 CineMax Movie Ticket Booking")

    tab_book, tab_mine = st.tabs(["🎟️ Book tickets", "📋 My bookings"])
    with tab_book:
        booking_page()
    with tab_mine:
        my_bookings_page()


if __name__ == "__main__":
    main()
