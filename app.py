import streamlit as st

st.set_page_config(layout="wide", page_title="SimpactHealth")

# -- Sidebar Navigation --
st.sidebar.title("SimpactHealth")
selected_page = st.sidebar.radio("Menu", ["Simulate"])

# -- Setup toggle buttons --
if "show_left" not in st.session_state:
    st.session_state.show_left = True
if "show_right" not in st.session_state:
    st.session_state.show_right = True

def toggle_left():
    st.session_state.show_left = not st.session_state.show_left

def toggle_right():
    st.session_state.show_right = not st.session_state.show_right

# -- Only show Simulate page --
if selected_page == "Simulate":
    col_toggle_left, col_toggle_right = st.columns([1, 1])
    
    with col_toggle_left:
        st.button("👈 Toggle Config Panel", on_click=toggle_left)
    with col_toggle_right:
        st.button("👉 Toggle Output Panel", on_click=toggle_right)

    # -- Determine column layout based on toggle state --
    if st.session_state.show_left and st.session_state.show_right:
        col_left, col_right = st.columns([1, 2])
    elif st.session_state.show_left:
        col_left, col_right = st.columns([1, 0.01])  # Right nearly hidden
    elif st.session_state.show_right:
        col_left, col_right = st.columns([0.01, 1])  # Left nearly hidden
    else:
        st.warning("Both panels are collapsed. Nothing to display.")
        st.stop()

    # -- Left Panel --
    if st.session_state.show_left:
        with col_left:
            st.subheader("🛠 Configuration")
            gui_tab, yaml_tab = st.tabs(["Setup GUI", "Setup YAML Markup"])

            with gui_tab:
                st.text_input("Model Name")
                st.number_input("Number of Patients", min_value=1, value=1000)

            with yaml_tab:
                st.text_area("YAML Markup")

    # -- Right Panel --
    if st.session_state.show_right:
        with col_right:
            st.subheader("📊 Simulation Output")
            st.info("Simulation results will appear here.")
