import streamlit as st

st.title("AI Traveller APP")
destination = st.text_input("Enter Destination")
travel_date = st.date_input("Enter Travel Date")
budget = st.number_input("Enter Budget", min_value=0, step=1000)
hotel_required = st.selectbox("Hotel Required", ["Yes", "No"])

if st.button("Submit"):
    st.write(f"""AI Travel Agent Summary
    -----------------------------------------------
    Destination \t: {destination}
    Travel Date \t: {travel_date}
    Budget \t: {budget}
    Hotel Required \t: {hotel_required}""")
    
    st.balloons()
