# =====================================================================
# 🎬 CineMax Movie Ticket Booking App (Streamlit + gTTS)
# ---------------------------------------------------------------------
# HOW STREAMLIT WORKS (read this first!):
#   Streamlit re-runs this ENTIRE script from top to bottom every time
#   the user interacts with a widget (clicks a checkbox, types text,
#   presses a button...). That's called a "rerun".
#
#   Because of that, normal Python variables are reset on every rerun.
#   To remember things between reruns (like which seats are booked),
#   we store them in `st.session_state`, a dictionary-like object that
#   survives reruns for as long as the browser tab stays open.
#
# REQUIREMENTS HANDLED IN THIS VERSION:
#   ✅ Mobile / email validation              -> validate_contact()
#   ✅ Children 5–12  -> ₹100                  -> AGE_CATEGORIES
#   ✅ Adult   14–50  -> ₹200                  -> AGE_CATEGORIES
#   ✅ Senior  61+    -> ₹100                  -> AGE_CATEGORIES
#   ✅ Explicit validation for ages 13, 51–60 -> UNCOVERED_AGE_RANGES + validate_age_brackets()
#   (Also handled: ages under 5, which the spec doesn't price -> lap child, no seat)
#
# Run locally with:   streamlit run movie_ticket_app.py
# Packages needed:    pip install streamlit gTTS
# =====================================================================

# ---------------- Imports ----------------
import streamlit as st            # the web-app framework
import logging                    # prints info/errors to the terminal (useful for debugging)
import random                     # used to generate random booking IDs
import re                         # regular expressions - pattern matching for mobile/email validation
import string                     # ready-made character sets: string.ascii_uppercase, string.digits
from datetime import date, datetime, timedelta   # date handling (today, +6 days, current time)
from io import BytesIO            # an in-memory "file" - lets us create audio without saving to disk
from gtts import gTTS             # Google Text-to-Speech: converts text into spoken MP3 audio

# Logging setup: logging.info(...) / logging.error(...) print timestamped lines
# in the terminal. On Streamlit Cloud they appear under "Manage app" -> logs.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# =====================================================================
# PRICING MODES
# ---------------------------------------------------------------------
# The app supports two ways of pricing, chosen in the sidebar:
#   FLAT -> the assignment spec: price depends ONLY on age category
#           (Child ₹100, Adult ₹200, Senior ₹100), all taxes included.
#   PVR  -> realistic PVR INOX-style pricing: seat class, format (2D/IMAX/4DX),
#           weekday/weekend, Tuesday offer, GST slabs, convenience fee,
#           plus a % discount for children and seniors.
# =====================================================================
MODE_FLAT = "Flat age-based (₹100 / ₹200 / ₹100)"
MODE_PVR = "PVR-style (seat class, format, day, GST)"
PRICING_MODES = [MODE_FLAT, MODE_PVR]      # first one is the default


# =====================================================================
# AGE RULES  (this is where the spec lives)
# =====================================================================

# A list of tuples. Each tuple = (category, min age, max age, flat price ₹, PVR-mode discount)
AGE_CATEGORIES = [
    ("Child",   5, 12,  100, 0.20),    # Children 5–12  -> ₹100
    ("Adult",  14, 50,  200, 0.00),    # Adult   14–50  -> ₹200
    ("Senior", 61, 120, 100, 0.20),    # Senior  61+    -> ₹100
]

# Ages the spec deliberately leaves OUT of every category.
# We list them explicitly so they get a clear, specific error message
# instead of silently falling into some default price.
# Each tuple = (from age, to age), inclusive.
UNCOVERED_AGE_RANGES = [
    (13, 13),
    (51, 60),
]

MIN_SEAT_AGE = 5                   # under 5 = sits on an adult's lap, no seat/ticket
MAX_AGE = 120
MAX_LAP_KIDS_PER_ADULT = 1
ADULT_AGE_FOR_SUPERVISION = 18     # legal adult (for A-rating & accompanying kids)
# NOTE: "Adult" PRICE category starts at 14, but for rating rules and
# accompanying children, a person must be 18+. These are two different ideas.

# CBFC (India's censor board) certificates.
#   - U/A ratings are ADVISORY: younger kids can watch WITH a parent.
#   - A rating is STRICT: nobody under 18 is allowed.
RATINGS = {
    "U":       {"min_age": 0,  "strict": False, "desc": "Universal - all ages"},
    "U/A 7+":  {"min_age": 7,  "strict": False, "desc": "Parental guidance under 7"},
    "U/A 13+": {"min_age": 13, "strict": False, "desc": "Parental guidance under 13"},
    "U/A 16+": {"min_age": 16, "strict": False, "desc": "Parental guidance under 16"},
    "A":       {"min_age": 18, "strict": True,  "desc": "Adults only - 18+"},
}


# =====================================================================
# PVR-MODE PRICING (approx. PVR INOX metro-city pricing, Sep 2026)
# Base prices are per seat, BEFORE GST, for Mon–Thu shows.
# Only used when the sidebar is set to PVR mode.
# =====================================================================
PRICE_TABLE = {
    "2D":   {"Classic": 220, "Prime": 270, "Recliner": 550},   # ~₹260 / ~₹320 / ~₹650 incl. GST
    "IMAX": {"Classic": 480, "Prime": 550, "Recliner": 800},   # ~₹565 / ~₹650 / ~₹945 incl. GST
    "4DX":  {"Classic": 700, "Prime": 700, "Recliner": 700},   # ~₹825 incl. GST (single class)
}
WEEKEND_MULTIPLIER = 1.15          # Fri–Sun shows cost 15% more

TUESDAY_PROMO_BASE = 92            # ₹92 + 5% GST = ₹95
TUESDAY_PROMO_FORMATS = {"2D"}     # sets -> fast "is X in here?" checks
TUESDAY_PROMO_CLASSES = {"Classic", "Prime"}

GST_THRESHOLD = 100                # India: 5% GST if ticket <= ₹100, else 18%
GST_LOW = 0.05
GST_HIGH = 0.18

CONVENIENCE_FEE = 30               # per ticket, online booking (PVR mode only)
CONVENIENCE_GST = 0.18


# =====================================================================
# CONTACT VALIDATION PATTERNS (regular expressions)
# ---------------------------------------------------------------------
# re.compile() prepares a pattern once so it can be reused quickly.
#   ^ ... $     -> the WHOLE string must match (not just part of it)
#   [6-9]       -> one digit from 6 to 9 (Indian mobiles start with 6/7/8/9)
#   \d{9}       -> exactly 9 more digits
#   (?:\+91)?   -> optional "+91" country code  ((?: ) is a non-capturing group, ? = optional)
#   [\w.+-]+    -> one or more letters/digits/underscore/dot/plus/hyphen
#   [A-Za-z]{2,} -> a domain ending of at least 2 letters (.in, .com, .org)
# =====================================================================
MOBILE_PATTERN = re.compile(r"^(?:\+91|91|0)?[6-9]\d{9}$")
EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,49}$")   # letters, spaces, . ' -  (2–50 chars)


# =====================================================================
# MOVIES & THEATRE LAYOUT
# =====================================================================
MOVIES = {
    "The Last Lighthouse": {"emoji": "🌊", "genre": "Drama",            "duration": "2h 10m", "rating": "U/A 13+", "format": "2D"},
    "Neon Streets":        {"emoji": "🌃", "genre": "Action / Thriller", "duration": "2h 25m", "rating": "A",       "format": "IMAX"},
    "Galaxy Runners":      {"emoji": "🚀", "genre": "Sci-Fi",            "duration": "2h 40m", "rating": "U/A 7+",  "format": "IMAX"},
    "Laugh Out Loud":      {"emoji": "😂", "genre": "Comedy",            "duration": "1h 55m", "rating": "U",       "format": "2D"},
    "Whispering Woods":    {"emoji": "🌲", "genre": "Horror",            "duration": "1h 50m", "rating": "A",       "format": "2D"},
    "Storm Chasers":       {"emoji": "🌪️", "genre": "Adventure",         "duration": "2h 05m", "rating": "U/A 16+", "format": "4DX"},
}

SHOWTIMES = ["10:00 AM", "01:30 PM", "05:00 PM", "09:00 PM"]

ROWS = list("ABCDEFGH")            # list("ABC") -> ['A', 'B', 'C']
SEATS_PER_ROW = 10
ROW_CLASS = {                      # which seat class each row belongs to
    "A": "Classic", "B": "Classic", "C": "Classic",
    "D": "Prime", "E": "Prime", "F": "Prime",
    "G": "Recliner", "H": "Recliner",
}
MAX_SEATS_PER_BOOKING = 10


# =====================================================================
# SMALL HELPERS
# =====================================================================

def init_state():
    """Create session_state entries on first load.
    setdefault() only sets a value if the key doesn't exist yet,
    so saved data is NOT overwritten on later reruns."""
    ss = st.session_state
    ss.setdefault("booked_seats", {})      # show_key -> set of booked seats
    ss.setdefault("bookings", [])          # list of booking dictionaries
    ss.setdefault("seat_form_version", 0)  # bump to reset all widgets (see seat map comments)
    ss.setdefault("last_booking", None)    # most recent booking (for the confirmation screen)


def show_key(movie, show_date, show_time):
    """Unique ID for one show, e.g. 'Neon Streets|2026-09-30|09:00 PM'.
    Seats are tracked PER SHOW: A1 at 10 AM is not the same as A1 at 9 PM."""
    return f"{movie}|{show_date.isoformat()}|{show_time}"


def sort_seats(seats):
    """Natural sort: A1, A2, ..., A10 (not A1, A10, A2).
    'A10' -> key ('A', 10), so we sort by row letter, then seat NUMBER."""
    return sorted(seats, key=lambda s: (s[0], int(s[1:])))


def generate_booking_id():
    """Random ID like 'BK7G2QX9LA' (8 random characters from A–Z and 0–9)."""
    return "BK" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def is_weekend(d):
    """True for Fri/Sat/Sun. weekday(): Monday=0 ... Sunday=6."""
    return d.weekday() >= 4


def is_tuesday_promo(movie, seat_class, d):
    """True if the ₹95 Tuesday offer applies (PVR mode only)."""
    return (
        d.weekday() == 1
        and MOVIES[movie]["format"] in TUESDAY_PROMO_FORMATS
        and seat_class in TUESDAY_PROMO_CLASSES
    )


# =====================================================================
# AGE HANDLING
# =====================================================================

def age_category(age):
    """Return the category tuple for an age, or None if no category covers it.

    Returning None (instead of guessing 'Adult') is important: it forces the
    caller to deal with uncovered ages explicitly.
    """
    for category in AGE_CATEGORIES:
        label, lo, hi, flat_price, disc = category      # tuple unpacking
        if lo <= age <= hi:                             # chained comparison
            return category
    return None


def uncovered_range_for(age):
    """If the age is in one of the explicitly excluded ranges, return that
    (from, to) tuple; otherwise return None."""
    for lo, hi in UNCOVERED_AGE_RANGES:
        if lo <= age <= hi:
            return (lo, hi)
    return None


def category_summary():
    """Text like 'Child 5–12, Adult 14–50, Senior 61+' for error messages."""
    parts = []
    for label, lo, hi, _, _ in AGE_CATEGORIES:        # _ = "value I don't need"
        parts.append(f"{label} {lo}+" if hi >= MAX_AGE else f"{label} {lo}–{hi}")
    return ", ".join(parts)


def validate_age_brackets(ages_by_seat):
    """Check EVERY seat's age against the pricing brackets.

    ages_by_seat: dict like {"D4": 35, "D5": 13}
    Returns a list of error messages (empty list = all ages valid).

    Handled explicitly:
      - under 5          -> no seat needed, use the lap-child field instead
      - 13 and 51–60     -> explicitly excluded by the spec
      - above MAX_AGE    -> not realistic
      - anything else not in a category -> safety net
    """
    errors = []
    for seat, age in ages_by_seat.items():
        if age < MIN_SEAT_AGE:
            errors.append(
                f"Seat {seat}: age {age} is under {MIN_SEAT_AGE}. Children under {MIN_SEAT_AGE} "
                f"don't get a seat ticket - remove this seat and add them as a lap child below."
            )
        elif age > MAX_AGE:
            errors.append(f"Seat {seat}: age {age} is not valid (max {MAX_AGE}).")
        elif (gap := uncovered_range_for(age)) is not None:
            # `:=` is the "walrus operator": it assigns AND tests in one step.
            gap_text = f"{gap[0]}" if gap[0] == gap[1] else f"{gap[0]}–{gap[1]}"
            errors.append(
                f"Seat {seat}: age {age} falls in the excluded age group ({gap_text}). "
                f"Tickets are only available for {category_summary()}."
            )
        elif age_category(age) is None:
            # Safety net: catches any gap we forgot to list in UNCOVERED_AGE_RANGES
            errors.append(
                f"Seat {seat}: age {age} doesn't match any ticket category ({category_summary()})."
            )
    return errors


def validate_rating_rules(movie, ages, lap_kids):
    """Check ages against the movie's certificate and format.
    Returns (errors, warnings): errors BLOCK the booking, warnings don't."""
    errors, warnings = [], []
    rating = MOVIES[movie]["rating"]
    rule = RATINGS[rating]
    fmt = MOVIES[movie]["format"]

    # List comprehension: keep only ages 18+
    adults = [a for a in ages if a >= ADULT_AGE_FOR_SUPERVISION]

    # --- Rule 1: the certificate ---
    if rule["strict"]:
        minors = sorted(a for a in ages if a < 18)
        if minors:
            errors.append(
                f"'{movie}' is rated **A (adults only)**. Every viewer must be 18+ "
                f"(found age(s): {', '.join(map(str, minors))})."   # map(str, ...) -> ints to strings
            )
        if lap_kids:
            errors.append("Children under 5 are not allowed in A-rated movies.")
    else:
        under = sorted(a for a in ages if a < rule["min_age"])
        if under:
            if not adults:
                errors.append(
                    f"'{movie}' is rated **{rating}**. Viewers under {rule['min_age']} "
                    f"must be accompanied by a parent/guardian (18+)."
                )
            else:
                warnings.append(
                    f"Rated {rating}: parental guidance advised for viewer(s) aged "
                    f"{', '.join(map(str, under))}."
                )

    # --- Rule 2: children (≤12) always need an adult ---
    if not errors and any(a <= 12 for a in ages) and not adults:
        errors.append("Children aged 12 or below must be accompanied by an adult (18+).")

    # --- Rule 3: 4DX ---
    if fmt == "4DX" and lap_kids:
        errors.append("Lap children are not allowed in 4DX motion seats.")

    # --- Rule 4: lap kids need adults ---
    if lap_kids and not adults:
        errors.append("Children under 5 must sit with an adult (18+).")
    elif lap_kids > len(adults) * MAX_LAP_KIDS_PER_ADULT:
        errors.append(f"Maximum {MAX_LAP_KIDS_PER_ADULT} lap child per adult.")

    return errors, warnings


# =====================================================================
# CONTACT VALIDATION
# =====================================================================

def normalize_mobile(mobile):
    """Remove spaces and hyphens so '+91 98765-43210' becomes '+919876543210'."""
    return re.sub(r"[\s-]", "", mobile)          # re.sub(pattern, replacement, text)


def validate_contact(name, mobile, email):
    """Validate name, mobile and email. Returns a list of error messages."""
    errors = []

    if not name.strip():
        errors.append("Please enter your name.")
    elif not NAME_PATTERN.match(name.strip()):
        errors.append("Name should be 2–50 characters and contain only letters, spaces, . ' or -")

    m = normalize_mobile(mobile)
    if not m:
        errors.append("Please enter your mobile number.")
    elif not MOBILE_PATTERN.match(m):
        errors.append(
            "Enter a valid Indian mobile number: 10 digits starting with 6, 7, 8 or 9 "
            "(optionally with +91)."
        )

    e = email.strip()
    if not e:
        errors.append("Please enter your email address.")
    elif not EMAIL_PATTERN.match(e):
        errors.append("Enter a valid email address, e.g. name@example.com")

    return errors


# =====================================================================
# PRICING
# =====================================================================

def price_ticket(movie, seat, age, show_date, mode):
    """Price ONE seat for ONE viewer. Only call this with a VALID age
    (i.e. after validate_age_brackets() returned no errors)."""
    fmt = MOVIES[movie]["format"]
    seat_class = ROW_CLASS[seat[0]]                  # "D5"[0] -> "D" -> "Prime"
    category, _, _, flat_price, disc = age_category(age)
    promo = False

    if mode == MODE_FLAT:
        # Spec pricing: the price depends only on the age category, taxes included
        base, discount, gst_rate, gst = flat_price, 0, 0.0, 0.0
    else:
        promo = is_tuesday_promo(movie, seat_class, show_date)
        if promo:
            base, discount = TUESDAY_PROMO_BASE, 0   # promo already cheapest - no stacking
        else:
            base = PRICE_TABLE[fmt][seat_class]      # nested dictionary lookup
            if is_weekend(show_date):
                base = round(base * WEEKEND_MULTIPLIER)
            discount = round(base * disc)            # child/senior % discount
        taxable = base - discount
        # Ternary expression: value_if_true if condition else value_if_false
        gst_rate = GST_LOW if taxable <= GST_THRESHOLD else GST_HIGH
        gst = round(taxable * gst_rate, 2)

    taxable = base - discount
    return {
        "seat": seat,
        "age": age,
        "category": category,
        "seat_class": seat_class,
        "base": base,
        "discount": discount,
        "taxable": taxable,
        "gst_rate": gst_rate,
        "gst": gst,
        "total": round(taxable + gst, 2),
        "promo": promo,
    }


def adult_price(movie, seat_class, show_date, mode):
    """Adult price for a seat class - used in the price legend.
    Finds the first row of that class (e.g. 'D'), makes seat 'D1',
    and reuses price_ticket() with an adult age (30)."""
    seat = next(r for r, c in ROW_CLASS.items() if c == seat_class) + "1"
    return price_ticket(movie, seat, 30, show_date, mode)["total"]


def calculate_bill(lines, mode):
    """Add up the per-seat prices. Generator expressions like
    sum(l["gst"] for l in lines) add values without building a list."""
    n = len(lines)
    conv_fee = 0 if mode == MODE_FLAT else CONVENIENCE_FEE * n
    conv_gst = round(conv_fee * CONVENIENCE_GST, 2)
    ticket_subtotal = sum(l["taxable"] for l in lines)
    ticket_gst = round(sum(l["gst"] for l in lines), 2)
    return {
        "ticket_subtotal": ticket_subtotal,
        "discounts": sum(l["discount"] for l in lines),
        "ticket_gst": ticket_gst,
        "conv_fee": conv_fee,
        "conv_gst": conv_gst,
        "total": round(ticket_subtotal + ticket_gst + conv_fee + conv_gst, 2),
    }


# =====================================================================
# TEXT-TO-SPEECH (gTTS)
# =====================================================================

# @st.cache_data remembers the result for the same arguments, so we don't
# call Google's TTS service again on every rerun.
@st.cache_data(show_spinner=False)
def text_to_speech(text, lang="en"):
    """Convert text to MP3 audio bytes."""
    try:
        logging.info("Generating booking confirmation audio")
        tts = gTTS(text=text, lang=lang)   # needs internet
        buf = BytesIO()                    # empty in-memory file
        tts.write_to_fp(buf)               # write MP3 data into it
        buf.seek(0)                        # rewind to the start before reading
        return buf.getvalue()
    except Exception as e:                 # don't crash the app if TTS fails
        logging.error(f"gTTS Error: {e}")
        return None


# =====================================================================
# TICKET OUTPUT
# =====================================================================

def build_ticket_text(b):
    """Plain-text ticket from booking dict `b`.
    f-string specs: {x:<4} left-align in 4 chars, {x:>8.2f} right-align, 2 decimals."""
    line = "=" * 50
    bill = b["bill"]
    seat_lines = "\n".join(
        f"  {l['seat']:<4} {l['category']:<7} age {l['age']:<3} {l['seat_class']:<9} Rs.{l['total']:>8.2f}"
        + ("  (Tue offer)" if l["promo"] else "")
        for l in b["lines"]
    )
    lap_line = f"Lap kids   : {b['lap_kids']} (under 5, free)\n" if b["lap_kids"] else ""

    if b["mode"] == MODE_FLAT:
        bill_text = f"TOTAL (all taxes included) : Rs. {bill['total']:.2f}\n"
    else:
        bill_text = (
            f"Tickets (after discounts) : Rs. {bill['ticket_subtotal']:.2f}\n"
            f"  Age discounts applied   : Rs. {bill['discounts']:.2f}\n"
            f"GST on tickets            : Rs. {bill['ticket_gst']:.2f}\n"
            f"Convenience fee           : Rs. {bill['conv_fee']:.2f}\n"
            f"GST on convenience fee    : Rs. {bill['conv_gst']:.2f}\n"
            f"TOTAL                     : Rs. {bill['total']:.2f}\n"
        )

    return (
        f"{line}\n"
        f"             🎬 CINEMAX MOVIE TICKET\n"
        f"{line}\n"
        f"Booking ID : {b['id']}\n"
        f"Name       : {b['name']}\n"
        f"Mobile     : {b['mobile']}\n"
        f"Email      : {b['email']}\n"
        f"Movie      : {b['movie']} ({b['rating']}, {b['format']})\n"
        f"Date       : {b['date']}\n"
        f"Showtime   : {b['time']}\n"
        f"{lap_line}"
        f"{'-' * 50}\n"
        f"Seats:\n{seat_lines}\n"
        f"{'-' * 50}\n"
        f"{bill_text}"
        f"{line}\n"
        f"Booked on  : {b['booked_at']}\n"
        f"Carry a valid age proof for child/senior tickets\n"
        f"and for A-rated films. Arrive 15 minutes early.\n"
    )


def show_confirmation(b):
    """Screen shown right after a successful booking."""
    st.success(f"🎉 Booking confirmed! Your booking ID is **{b['id']}**")
    st.caption(f"A copy would be sent to {b['email']} and {b['mobile']}.")
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
        if st.button("🎟️ Book another ticket"):  # True only on the rerun right after the click
            st.session_state.last_booking = None
            st.rerun()

    st.subheader("🔊 Audio confirmation")
    speech = (
        f"Booking confirmed for {b['name']}. "
        f"{len(b['seats'])} tickets for {b['movie']} on {b['date']} at {b['time']}. "
        f"Your seats are {', '.join(b['seats'])}. "
        f"Total amount is {b['bill']['total']:.0f} rupees. "
        f"Please carry age proof for child or senior tickets. Enjoy your movie!"
    )
    with st.spinner("Generating audio..."):
        audio = text_to_speech(speech)
    if audio:
        st.audio(audio, format="audio/mp3")
    else:
        st.warning("Couldn't generate audio right now.")


# =====================================================================
# PAGES
# =====================================================================

def booking_page(mode):
    """'Book tickets' tab: show -> seats -> ages -> bill -> contact -> confirm."""
    ss = st.session_state

    if ss.last_booking:                    # just booked? show confirmation and stop
        show_confirmation(ss.last_booking)
        return

    # ---------------- Step 1: choose the show ----------------
    col1, col2, col3 = st.columns(3)
    movie = col1.selectbox("🎞️ Movie", list(MOVIES.keys()))
    show_date = col2.date_input(
        "📅 Date",
        value=date.today(),
        min_value=date.today(),                        # no past dates
        max_value=date.today() + timedelta(days=6),    # next 7 days only
    )
    show_time = col3.selectbox("⏰ Showtime", SHOWTIMES)

    info = MOVIES[movie]
    rating = info["rating"]
    st.markdown(f"## {info['emoji']} {movie}")
    st.caption(
        f"{info['genre']} • {info['duration']} • **{info['format']}** • "
        f"Rated **{rating}** ({RATINGS[rating]['desc']})"
    )
    if RATINGS[rating]["strict"]:
        st.warning("🔞 Adults only. Every viewer must be 18+ and carry valid ID.")

    # ---------------- Price legend ----------------
    if mode == MODE_FLAT:
        legend = " &nbsp;|&nbsp; ".join(
            f"**{label}** ({lo}+)" if hi >= MAX_AGE else f"**{label}** ({lo}–{hi})"
            for label, lo, hi, _, _ in AGE_CATEGORIES
        )
        prices = " &nbsp;|&nbsp; ".join(f"{label}: ₹{price}" for label, _, _, price, _ in AGE_CATEGORIES)
        st.markdown(f"Ticket prices (any seat, all taxes included) — {prices}")
        st.caption(f"Categories: {legend}. Ages 13 and 51–60 are not eligible. Under 5: lap child, free.")
    else:
        if show_date.weekday() == 1 and info["format"] in TUESDAY_PROMO_FORMATS:
            st.info("🎉 Tuesday offer: Classic & Prime seats at ₹95 (incl. GST) for this show!")
        elif is_weekend(show_date):
            st.info("📈 Weekend pricing applies (Fri–Sun).")
        if info["format"] == "4DX":
            legend = f"**4DX (all seats)**: ₹{adult_price(movie, 'Classic', show_date, mode):.0f}"
        else:
            rows_text = {"Classic": "A–C", "Prime": "D–F", "Recliner": "G–H"}
            legend = " &nbsp;|&nbsp; ".join(
                f"**{c}** ({rows_text[c]}): ₹{adult_price(movie, c, show_date, mode):.0f}"
                for c in ["Classic", "Prime", "Recliner"]
            )
        st.markdown(f"Adult prices incl. GST — {legend}")
        st.caption("Children (5–12) and seniors (61+) get 20% off the base price. Ages 13 and 51–60 are not eligible.")

    key = show_key(movie, show_date, show_time)
    booked = ss.booked_seats.get(key, set())    # empty set if nothing booked for this show
    v = ss.seat_form_version

    # ---------------- Step 2: seat map ----------------
    st.subheader("💺 Select your seats")
    st.markdown(
        "<div style='text-align:center; padding:6px; margin-bottom:12px; "
        "background:linear-gradient(90deg,#444,#aaa,#444); color:white; "
        "border-radius:6px; font-weight:bold; letter-spacing:6px;'>SCREEN</div>",
        unsafe_allow_html=True,                 # allow raw HTML/CSS
    )
    st.caption("Greyed-out seats are already booked.")

    selected = []
    for row in ROWS:
        cols = st.columns([0.6] + [1] * SEATS_PER_ROW)   # narrow label column + 10 seat columns
        cols[0].markdown(f"**{row}**")
        for n in range(1, SEATS_PER_ROW + 1):
            seat = f"{row}{n}"
            with cols[n]:
                # Unique widget key: includes the show (fresh seats per show) and
                # the version `v` (bumping it after booking clears all checkboxes).
                widget_key = f"{key}|{seat}|{v}"
                if seat in booked:
                    st.checkbox(seat, value=True, disabled=True, key=widget_key)
                elif st.checkbox(seat, key=widget_key):
                    selected.append(seat)

    st.divider()

    if not selected:
        st.info("Select one or more seats to continue.")
        return
    if len(selected) > MAX_SEATS_PER_BOOKING:
        st.error(f"You can book at most {MAX_SEATS_PER_BOOKING} seats at once.")
        return

    selected = sort_seats(selected)

    # ---------------- Step 3: viewer ages ----------------
    st.subheader("👥 Viewer ages")
    st.caption(f"Enter the age of the person in each seat. Valid categories: {category_summary()}.")
    ages = {}
    age_cols = st.columns(5)
    for i, s in enumerate(selected):            # enumerate -> (index, seat)
        with age_cols[i % 5]:                   # % 5 wraps inputs across 5 columns
            # min_value=1 (not 5) on purpose, so under-5 ages reach our validation
            # and get a helpful message instead of being silently blocked.
            ages[s] = st.number_input(
                f"Seat {s}", min_value=1, max_value=MAX_AGE, value=25, step=1,
                key=f"age|{key}|{s}|{v}",
            )
    lap_kids = st.number_input(
        f"👶 Children under {MIN_SEAT_AGE} (on an adult's lap, free, no seat)",
        min_value=0, max_value=5, value=0, step=1, key=f"lap|{key}|{v}",
    )

    # Validation happens in two layers:
    #   1) age brackets (13, 51–60, under 5...) - must pass before we can price anything
    #   2) rating/format rules (A-rated, U/A, 4DX, lap kids)
    bracket_errors = validate_age_brackets(ages)
    rating_errors, warnings = validate_rating_rules(movie, list(ages.values()), lap_kids)
    errors = bracket_errors + rating_errors     # joining two lists

    for w in warnings:
        st.warning(w)
    for e in errors:
        st.error(e)

    if errors:
        # Stop here: we can't price an age that has no category.
        st.caption("Fix the age issues above to see the price and book.")
        return

    # ---------------- Step 4: the bill ----------------
    lines = [price_ticket(movie, s, ages[s], show_date, mode) for s in selected]
    bill = calculate_bill(lines, mode)

    st.subheader("🧾 Booking summary")
    if mode == MODE_FLAT:
        rows = [
            {"Seat": l["seat"], "Age": l["age"], "Category": l["category"], "Price ₹": f"{l['total']:.2f}"}
            for l in lines
        ]
    else:
        rows = [
            {
                "Seat": l["seat"],
                "Class": l["seat_class"],
                "Age": l["age"],
                "Category": l["category"] + (" (Tue offer)" if l["promo"] else ""),
                "Base ₹": f"{l['base']:.2f}",
                "Discount ₹": f"{l['discount']:.2f}",
                "GST": f"{int(l['gst_rate'] * 100)}%",
                "Price ₹": f"{l['total']:.2f}",
            }
            for l in lines
        ]
    st.table(rows)   # list of dicts -> each dict is a row, keys are column headers

    # Count tickets per category, e.g. {"Adult": 2, "Child": 1}
    counts = {}
    for l in lines:
        counts[l["category"]] = counts.get(l["category"], 0) + 1

    left, right = st.columns(2)
    with left:
        st.write(f"**Seats:** {', '.join(selected)}")
        st.write("**Tickets:** " + ", ".join(f"{n} × {c}" for c, n in counts.items())
                 + (f" + {lap_kids} lap child(ren)" if lap_kids else ""))
        if bill["discounts"]:
            st.write(f"🎁 Age discounts saved you **₹{bill['discounts']:.2f}**")
    with right:
        if mode == MODE_PVR:
            st.write(f"Tickets (after discounts): ₹{bill['ticket_subtotal']:.2f}")
            st.write(f"GST on tickets: ₹{bill['ticket_gst']:.2f}")
            st.write(f"Convenience fee: ₹{bill['conv_fee']:.2f}")
            st.write(f"GST on convenience fee: ₹{bill['conv_gst']:.2f}")
        else:
            st.write("All taxes included, no convenience fee.")
        st.markdown(f"### Total: ₹{bill['total']:.2f}")

    # ---------------- Step 5: contact details & confirm ----------------
    st.subheader("👤 Your details")
    name = st.text_input("Full name", key=f"name|{v}")
    c1, c2 = st.columns(2)
    mobile = c1.text_input("Mobile number", placeholder="98765 43210 or +91 98765 43210", key=f"mobile|{v}")
    email = c2.text_input("Email", placeholder="name@example.com", key=f"email|{v}")

    if st.button("✅ Confirm booking", type="primary"):
        contact_errors = validate_contact(name, mobile, email)
        if contact_errors:
            for e in contact_errors:
                st.error(e)
        else:
            clean_mobile = normalize_mobile(mobile)[-10:]   # keep the last 10 digits
            booking = {
                "id": generate_booking_id(),
                "name": name.strip(),
                "mobile": f"+91 {clean_mobile}",
                "email": email.strip().lower(),
                "movie": movie,
                "rating": rating,
                "format": info["format"],
                "mode": mode,
                "date": show_date.strftime("%A, %d %B %Y"),
                "time": show_time,
                "show_key": key,
                "seats": selected,
                "lines": lines,
                "lap_kids": lap_kids,
                "bill": bill,
                "booked_at": datetime.now().strftime("%d-%m-%Y %H:%M"),
            }
            ss.booked_seats.setdefault(key, set()).update(selected)   # mark seats booked
            ss.bookings.append(booking)
            ss.last_booking = booking
            ss.seat_form_version += 1          # new widget keys -> form resets
            logging.info(f"Booking {booking['id']} confirmed: {key} seats={selected} total={bill['total']}")
            st.rerun()


def my_bookings_page():
    """'My bookings' tab: view, download or cancel bookings."""
    ss = st.session_state
    if not ss.bookings:
        st.info("You haven't booked any tickets yet.")
        return

    st.write(f"You have **{len(ss.bookings)}** booking(s).")
    for b in reversed(ss.bookings):            # newest first
        with st.expander(f"{b['id']} — {b['movie']} • {b['date']} • {b['time']} • ₹{b['bill']['total']:.2f}"):
            st.code(build_ticket_text(b), language=None)
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "⬇️ Download",
                    data=build_ticket_text(b),
                    file_name=f"ticket_{b['id']}.txt",
                    mime="text/plain",
                    key=f"dl_{b['id']}",       # widgets in a loop need unique keys
                )
            with c2:
                if st.button("❌ Cancel booking", key=f"cancel_{b['id']}"):
                    ss.booked_seats.get(b["show_key"], set()).difference_update(b["seats"])  # free seats
                    ss.bookings = [x for x in ss.bookings if x["id"] != b["id"]]           # remove booking
                    if ss.last_booking and ss.last_booking["id"] == b["id"]:
                        ss.last_booking = None
                    ss.seat_form_version += 1
                    logging.info(f"Booking {b['id']} cancelled")
                    st.rerun()


# =====================================================================
# MAIN
# =====================================================================
def main():
    # Must be the FIRST Streamlit command
    st.set_page_config(page_title="Movie Ticket Booking", page_icon="🎬", layout="wide")
    init_state()

    # Sidebar: pricing mode switch + quick reference of the age rules
    with st.sidebar:
        st.header("⚙️ Settings")
        mode = st.radio("Pricing mode", PRICING_MODES, index=0)
        st.divider()
        st.markdown("**Age categories**")
        for label, lo, hi, price, _ in AGE_CATEGORIES:
            age_text = f"{lo}+" if hi >= MAX_AGE else f"{lo}–{hi}"
            st.markdown(f"- {label}: {age_text} → ₹{price}")
        st.markdown("- ❌ Not eligible: 13, 51–60")
        st.markdown(f"- 👶 Under {MIN_SEAT_AGE}: lap child, free")

    st.title("🎬 CineMax Movie Ticket Booking")

    tab_book, tab_mine = st.tabs(["🎟️ Book tickets", "📋 My bookings"])
    with tab_book:
        booking_page(mode)
    with tab_mine:
        my_bookings_page()


# True only when this file is run directly (not imported)
if __name__ == "__main__":
    main()
