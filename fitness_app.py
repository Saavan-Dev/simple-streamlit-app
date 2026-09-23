import streamlit as st

# 1. Page Configuration & Header
st.set_page_config(page_title="AI Fitness Coach", page_icon="🏋️")
st.title("🏋️ Smart AI Fitness & Habit Planner")

# 2. Input Collection Widgets
client_name = st.text_input("Enter your name")
age = st.number_input("Enter your age", min_value=12, max_value=100, value=25)
daily_active_time = st.number_input("Target workout time (minutes per day)", min_value=10, max_value=180, value=45)
gym_access = st.selectbox("Do you have access to a gym or equipment?", ("Yes", "No"))

fitness_goal = st.selectbox(
    "Primary Fitness Goal",
    ["Fat Loss", "Muscle Building", "Endurance", "Flexibility & Mobility"]
)

activities = st.multiselect(
    "Preferred Activities",
    ["Running", "Weightlifting", "Yoga", "Swimming", "Cycling", "Calisthenics"]
)

# 3. Execution Trigger
if st.button("Generate Plan"):
    st.write("---")
    st.write("### 📊 Assessment & Plan")

    # 4. Rule Engine / Business Logic
    if daily_active_time < 30:
        intensity_level = "Light Routine"
        commitment_tier = "Beginner (Focus on habit formation)"
    elif daily_active_time < 60:
        intensity_level = "Moderate Routine"
        commitment_tier = "Intermediate (Balanced progress)"
    elif daily_active_time < 90:
        intensity_level = "High-Intensity Routine"
        commitment_tier = "Advanced (Performance gains)"
    else:
        intensity_level = "Athlete Routine"
        commitment_tier = "Elite (Requires structured recovery)"

    # 5. UI Presentation with Columns and Callouts
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Target Time", value=f"{daily_active_time} min/day")
        st.write(f"**Intensity Tier:** {intensity_level}")
    with col2:
        st.metric(label="Equipment Access", value=gym_access)
        st.write(f"**Profile:** {commitment_tier}")

    st.write(f"""
    **Plan Summary for {client_name if client_name else 'Athlete'}:**
    - **Goal:** {fitness_goal}
    - **Selected Activities:** {', '.join(activities) if activities else 'General bodyweight conditioning'}
    """)

    st.write("#### 🎯 Coaching Directives")
    if fitness_goal == "Fat Loss":
        st.info("Combine progressive resistance training with a daily 500-calorie deficit and steady walking.")
    elif fitness_goal == "Muscle Building":
        st.info("Prioritize progressive overload, 1.6–2.2g of protein per kg of body weight, and 8 hours of sleep.")
    elif fitness_goal == "Endurance":
        st.info("Dedicate 80% of weekly training volume to Zone-2 aerobic work and 20% to interval sessions.")
    elif fitness_goal == "Flexibility & Mobility":
        st.info("Incorporate 20 minutes of dynamic mobility upon waking and static stretching post-workout.")

    st.balloons()
