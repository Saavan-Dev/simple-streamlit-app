# ==============================================================
# 💰 SIMPLE EXPENSE TRACKER - a Streamlit app
#
# Python concepts you can revise in this file:
#   1. Imports & aliases        7. Conditionals (if / elif / else)
#   2. Variables & data types   8. Classes & objects (OOP)
#   3. Lists                    9. Exception handling (try / except)
#   4. Dictionaries            10. f-strings & number formatting
#   5. Functions & return      11. List comprehensions & lambda
#   6. Loops (for)             12. Tuples & unpacking
# ==============================================================


# ---------- 1. IMPORTS ----------
import streamlit as st          # 'as st' gives the module a short nickname (alias)
import pandas as pd             # pandas works with tables called DataFrames
from datetime import date       # import just ONE thing from a module


# ---------- 2. CONSTANTS ----------
# By convention, UPPERCASE names are "constants": values we don't change.
CURRENCY = "₹"                  # a STRING (str). Change to "$" or "€" if you like.

# A LIST: ordered, changeable, allows duplicates. Written with [ ].
CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Other"]

# A DICTIONARY: stores key -> value pairs. Written with { }.
CATEGORY_EMOJI = {
    "Food": "🍔",
    "Travel": "✈️",
    "Shopping": "🛍️",
    "Bills": "🧾",
    "Other": "📦",
}


# ---------- 3. CLASS (Object-Oriented Programming) ----------
class Expense:
    """A blueprint for one expense.
    (Text in triple quotes right under a class/function is a 'docstring'.)"""

    # __init__ is the CONSTRUCTOR. It runs automatically when you write
    # Expense("Pizza", 250.0, "Food", date.today())
    def __init__(self, title, amount, category, spent_on):
        # 'self' means "this particular object".
        # These are ATTRIBUTES: data stored inside the object.
        self.title = title            # str
        self.amount = amount          # float (decimal number)
        self.category = category      # str
        self.spent_on = spent_on      # date object

    # A METHOD is a function that belongs to a class.
    def to_dict(self):
        """Convert this object into a dictionary (pandas likes dicts)."""
        # dict.get(key, default) returns default if the key is missing,
        # instead of crashing with a KeyError.
        emoji = CATEGORY_EMOJI.get(self.category, "")
        return {
            "Title": self.title,
            "Amount": self.amount,
            "Category": f"{emoji} {self.category}",   # f-string: puts variables inside { }
            "Date": self.spent_on,
        }


# ---------- 4. HELPER FUNCTIONS ----------
def validate_input(title, amount):
    """Check the user's input.
    Returns TWO values (a TUPLE): (is_valid, message)."""
    # .strip() removes spaces from both ends, so "   " becomes ""
    if title.strip() == "":
        return False, "Title cannot be empty."
    elif amount <= 0:                       # elif = "else if"
        return False, "Amount must be greater than 0."
    else:
        return True, "OK"


def total_by_category(expenses):
    """Add up spending per category using a LOOP and a DICTIONARY."""
    totals = {}                             # start with an empty dict

    for exp in expenses:                    # FOR loop: visit each item in the list
        if exp.category in totals:          # 'in' checks whether a key exists
            totals[exp.category] += exp.amount    # += means "add to existing value"
        else:
            totals[exp.category] = exp.amount     # first time: create the key

    return totals                           # e.g. {"Food": 500.0, "Travel": 1200.0}


# ---------- 5. MAIN APP ----------
def main():
    # Page settings must be the first Streamlit command
    st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="centered")
    st.title("💰 Simple Expense Tracker")
    st.caption("Add your expenses and see where your money goes!")

    # --- SESSION STATE ---
    # Streamlit re-runs this WHOLE script every time you click something,
    # so normal variables reset each time. st.session_state works like a
    # dictionary that REMEMBERS values between re-runs.
    if "expenses" not in st.session_state:
        st.session_state.expenses = []      # empty list, filled with Expense objects later

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Settings")
    budget = st.sidebar.number_input(
        f"Monthly budget ({CURRENCY})",
        min_value=0.0,                      # float values -> returns a float
        value=10000.0,
        step=500.0,
    )

    # --- INPUT FORM ---
    st.subheader("➕ Add an expense")

    # 'with' is a CONTEXT MANAGER: everything indented below belongs to the form.
    # clear_on_submit=True empties the boxes after you press the button.
    with st.form("expense_form", clear_on_submit=True):
        title = st.text_input("What did you spend on?")

        # TUPLE UNPACKING: st.columns(2) returns 2 items, stored in 2 variables
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Amount", min_value=0.0, step=10.0)
        with col2:
            category = st.selectbox("Category", CATEGORIES)

        spent_on = st.date_input("Date", value=date.today())
        submitted = st.form_submit_button("Add Expense")   # True only when clicked (bool)

    # --- HANDLE SUBMIT ---
    if submitted:
        is_valid, message = validate_input(title, amount)   # unpack the returned tuple
        if is_valid:
            new_expense = Expense(title.strip(), amount, category, spent_on)  # create an OBJECT
            st.session_state.expenses.append(new_expense)   # .append() adds to end of list
            # :.2f formats a number with exactly 2 decimal places
            st.success(f"Added '{title}' of {CURRENCY}{amount:.2f} ✅")
        else:
            st.error(message)

    expenses = st.session_state.expenses    # shorter name for convenience

    # Nothing to show yet? Exit the function early with 'return'.
    if len(expenses) == 0:                  # len() gives the number of items
        st.info("No expenses yet. Add one above 👆")
        return

    # --- SUMMARY ---
    st.subheader("📊 Summary")

    # LIST COMPREHENSION: build a new list in one line.
    # Same as: amounts = []; for exp in expenses: amounts.append(exp.amount)
    amounts = [exp.amount for exp in expenses]
    total_spent = sum(amounts)              # built-in sum() adds all numbers
    remaining = budget - total_spent

    c1, c2, c3 = st.columns(3)
    # :,.2f adds thousand separators, e.g. 12,345.60
    c1.metric("Total spent", f"{CURRENCY}{total_spent:,.2f}")
    c2.metric("Budget", f"{CURRENCY}{budget:,.2f}")
    c3.metric("Remaining", f"{CURRENCY}{remaining:,.2f}")

    # --- EXCEPTION HANDLING ---
    # Dividing by zero raises ZeroDivisionError. try/except catches it
    # so the app doesn't crash if the budget is 0.
    try:
        used_ratio = total_spent / budget
    except ZeroDivisionError:
        used_ratio = 1.0                    # treat as "budget fully used"

    # min() keeps the value at most 1.0, because st.progress needs 0.0 to 1.0
    st.progress(min(used_ratio, 1.0))

    # Conditionals checked top to bottom; the first True branch runs
    if used_ratio >= 1:
        st.error("🚨 You have exceeded your budget!")
    elif used_ratio >= 0.8:
        st.warning("⚠️ You've used over 80% of your budget.")
    else:
        st.success("👍 You're within budget.")

    # --- TABLE ---
    st.subheader("🧾 All expenses")
    # List comprehension again: turn every object into a dict, then into a DataFrame
    df = pd.DataFrame([exp.to_dict() for exp in expenses])
    st.dataframe(df, hide_index=True)

    # --- CHART ---
    st.subheader("📈 Spending by category")
    totals = total_by_category(expenses)
    # .items() gives (key, value) pairs -> we turn them into table rows
    chart_df = pd.DataFrame(list(totals.items()), columns=["Category", "Amount"])
    st.bar_chart(chart_df.set_index("Category"))

    # --- LAMBDA ---
    # A lambda is a tiny one-line function with no name.
    # max(..., key=...) uses it to decide WHAT to compare (here: the amount).
    biggest = max(expenses, key=lambda exp: exp.amount)
    st.write(f"💸 Biggest expense: **{biggest.title}** ({CURRENCY}{biggest.amount:,.2f})")

    # --- DOWNLOAD & RESET ---
    csv_data = df.to_csv(index=False).encode("utf-8")   # str -> bytes
    st.download_button("⬇️ Download as CSV", data=csv_data,
                       file_name="expenses.csv", mime="text/csv")

    if st.button("🗑️ Clear all expenses"):
        st.session_state.expenses = []      # replace with an empty list
        st.rerun()                          # refresh the page immediately


# ---------- 6. ENTRY POINT ----------
# __name__ equals "__main__" only when this file is run directly
# (not when it's imported by another file). Good habit to include.
if __name__ == "__main__":
    main()
