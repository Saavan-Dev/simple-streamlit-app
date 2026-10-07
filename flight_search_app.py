import streamlit as st
import requests
import json
from datetime import datetime


from sqlalchemy import create_engine, URL
import pymysql

db_url = URL.create(
    drivername = DRIVERNAME,
    username = USERNAME,
    password = PASSWORD,
    host = HOSTNAME,
    database = DATABASE
)

engine = create_engine(
    db_url
)

def save_search(origin, destination, travel_date):

    conn = engine.raw_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "INSERT IGNORE INTO airports(iata_code) VALUES(%s)",
            (origin.upper(),)
        )

        cursor.execute(
            "INSERT IGNORE INTO airports(iata_code) VALUES(%s)",
            (destination.upper(),)
        )

        conn.commit()

        cursor.execute(
            "SELECT airport_id FROM airports WHERE iata_code=%s",
            (origin.upper(),)
        )
        source_id = cursor.fetchone()[0]

        cursor.execute(
            "SELECT airport_id FROM airports WHERE iata_code=%s",
            (destination.upper(),)
        )
        dest_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO searches(
                source_airport_id,
                destination_airport_id,
                travel_date
            )
            VALUES(%s,%s,%s)
        """, (
            source_id,
            dest_id,
            str(travel_date)
        ))

        conn.commit()

        return cursor.lastrowid

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        cursor.close()
        conn.close()

def save_flight(
search_id,
airline,
dep_airport,
arr_airport,
dep_time,
arr_time,
duration,
price
):

    conn = engine.raw_connection()
    cursor = conn.cursor()

    try:

        dep_time = datetime.strptime(
            dep_time,
            "%Y-%m-%d %H:%M"
        )

        arr_time = datetime.strptime(
            arr_time,
            "%Y-%m-%d %H:%M"
        )

        duration = int(duration)

        price = float(price)

        cursor.execute("""
            INSERT INTO flights(
                search_id,
                airline,
                departure_airport,
                arrival_airport,
                departure_time,
                arrival_time,
                duration_minutes,
                price
            )
            VALUES(
                %s,%s,%s,%s,
                %s,%s,%s,%s
            )
        """, (
            search_id,
            airline,
            dep_airport,
            arr_airport,
            dep_time,
            arr_time,
            duration,
            price
        ))

        conn.commit()

    except Exception as e:

        conn.rollback()
        print("DB ERROR:", e)

    finally:

        cursor.close()
        conn.close()
def fetch_flights(origin, destination, date):
    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google_flights",
        "api_key": API_KEY,
        "departure_id": origin.upper(),
        "arrival_id": destination.upper(),
        "outbound_date": date,
        "type": 2,
        "currency": "USD"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if "error" in data:
            return f"API Error:\n{data['error']}"

        flights = data.get("best_flights", [])

        if not flights:
            flights = data.get("other_flights", [])

        search_id = save_search(
        origin,
        destination,
        date
        )


        if not flights:
            return (
                "No flights found.\n\n"
                "Debug Response:\n"
                + json.dumps(data, indent=2)[:3000]
            )

        result = "✈️ Available Flights\n\n"

        for i, flight in enumerate(flights[:5], start=1):

            total_duration = flight.get("total_duration", "N/A")
            price = flight.get("price", "N/A")

            segments = flight.get("flights", [])

            if not segments:
                continue

            first = segments[0]
            last = segments[-1]

            airline = first.get("airline", "Unknown")

            dep_airport = first.get(
                "departure_airport", {}
            ).get("id", origin.upper())

            dep_time = first.get(
                "departure_airport", {}
            ).get("time", "N/A")

            arr_airport = last.get(
                "arrival_airport", {}
            ).get("id", destination.upper())

            arr_time = last.get(
                "arrival_airport", {}
            ).get("time", "N/A")

            save_flight(
            search_id,
            airline,
            dep_airport,
            arr_airport,
            dep_time,
            arr_time,
            total_duration,
            price
            )
            result += (
                f"{i}. {airline}\n"
                f"   From: {dep_airport} ({dep_time})\n"
                f"   To:   {arr_airport} ({arr_time})\n"
                f"   Duration: {total_duration} mins\n"
                f"   Price: {price}\n\n"
            )

        return result

    except Exception as e:
        return f"Error: {str(e)}"
        return f"Error: {str(e)}"

st.set_page_config(
page_title="Flight Search",
page_icon="✈️",
layout="centered"
)

st.title("🌍 Real-Time Flight Information")

st.write(
"Enter source airport, destination airport, and travel date "
"to retrieve flight details."
)

origin = st.text_input(
"Origin IATA Code",
placeholder="MAA"
)

destination = st.text_input(
"Destination IATA Code",
placeholder="DEL"
)

date = st.date_input(
"Date (YYYY-MM-DD)",value=None
)

if st.button("Search Flights"):


    if not origin or not destination or not date:
        st.warning("Please fill all fields.")
    else:
        with st.spinner("Fetching flights..."):
            result = fetch_flights(origin, destination, date)

        st.text_area(
            "Flight Results",
            value=result,
            height=400
        )
