import streamlit as st
import streamlit.components.v1 as components
import yaml

# --- Streamlit Page Configuration ---
st.set_page_config(layout="wide", page_title="SimpactHealth")

# --- Sidebar ---
st.sidebar.title("SimpactHealth")
page = st.sidebar.radio("Menu", ["Draw", "Simulate"])

# --- Session State Initialization ---
for side in ("show_left", "show_right"):
    if side not in st.session_state:
        st.session_state[side] = True

# Initialize default structured data for transitions as a list of dictionaries
if 'transitions_list' not in st.session_state:
    st.session_state.transitions_list = [
        {"source": "Alive", "target": "Dead", "probability": 1.0}
    ]

# --- Toggle Functions ---
def toggle_left():
    st.session_state.show_left = not st.session_state.show_left

def toggle_right():
    st.session_state.show_right = not st.session_state.show_right

def add_transition_row():
    """Adds an empty row to the transitions_list."""
    st.session_state.transitions_list.append({"source": "", "target": "", "probability": 0.0})

def remove_last_transition_row():
    """Removes the last row from the transitions_list, if any."""
    if st.session_state.transitions_list:
        st.session_state.transitions_list.pop()

# --- Main Application Logic ---
if page == "Draw":
    # --- Panel Toggle Buttons ---
    l, r = st.columns(2)
    with l:
        st.button("👈 Toggle Config Panel", on_click=toggle_left)
    with r:
        st.button("👉 Toggle Diagram Panel", on_click=toggle_right)

    # --- Layout Panels ---
    if st.session_state.show_left and st.session_state.show_right:
        col_left, col_right = st.columns([1, 2])
    elif st.session_state.show_left:
        col_left, col_right = st.columns([1, 0.01])
    elif st.session_state.show_right:
        col_left, col_right = st.columns([0.01, 1])
    else:
        st.warning("Both panels collapsed. Please enable at least one.")
        st.stop()

    # --- Left Panel: Configuration and Mermaid Editor ---
    if st.session_state.show_left:
        with col_left:
            st.subheader("🛠 Diagram Configuration")
            gui, yaml_tab = st.tabs(["Mermaid Editor", "Setup YAML"])

            with gui:
                st.text_input("Model Name", value="My Simulation Model")
                num_patients = st.number_input("Initial Number of Patients", min_value=1, value=1000)

                st.markdown("---")

                st.subheader("✍️ Define Custom Transitions")
                st.write("Add rows to define custom nodes and arrows. Probabilities for outgoing arrows from a node should sum to 1.0.")

                # Use st.expander to contain the transition inputs and manage vertical space
                with st.expander("Expand to define transitions", expanded=True):
                    # Use a Streamlit container with custom CSS for scrolling
                    # This ensures the widgets are correctly nested within the scrollable element.
                    scrollable_container = st.container(height=350) # Set fixed height for the container

                    with scrollable_container:
                        for i, transition in enumerate(st.session_state.transitions_list):
                            # Use columns for a compact layout for each transition row
                            t_col1, t_col2, t_col3 = st.columns([1, 1, 0.8])
                            with t_col1:
                                transition["source"] = st.text_input(
                                    f"Source Node", # Simplified label
                                    value=transition.get("source", ""),
                                    key=f"source_{i}"
                                )
                            with t_col2:
                                transition["target"] = st.text_input(
                                    f"Target Node", # Simplified label
                                    value=transition.get("target", ""),
                                    key=f"target_{i}"
                                )
                            with t_col3:
                                transition["probability"] = st.number_input(
                                    f"Probability", # Simplified label
                                    value=transition.get("probability", 0.0),
                                    min_value=0.0,
                                    max_value=1.0,
                                    format="%.2f",
                                    step=0.01,
                                    key=f"prob_{i}"
                                )
                            # Add a very subtle separator unless it's the very last one
                            if i < len(st.session_state.transitions_list) -1:
                                st.markdown('<hr style="margin: 5px 0;">', unsafe_allow_html=True) # Smaller margin for separator


                # Buttons to add/remove rows outside the expander/scrollable container
                btn_col1, btn_col2 = st.columns([0.2, 1])
                with btn_col1:
                    st.button("➕ Add Transition", on_click=add_transition_row)
                with btn_col2:
                    st.button("➖ Remove Last", on_click=remove_last_transition_row)


                # --- Generate Mermaid Code from Structured Data ---
                mermaid_lines = ["graph TD"]
                mermaid_lines.append(f'    Start -- [{num_patients}] --> Alive;')

                probabilities_by_source = {}
                user_mermaid_code = ""

                for transition in st.session_state.transitions_list:
                    source = transition.get("source")
                    target = transition.get("target")
                    probability = transition.get("probability")

                    if not source or not target:
                        continue

                    arrow_label = ""
                    if isinstance(probability, (int, float)):
                        arrow_label = f' -- [{probability}] -->'
                    else:
                        arrow_label = " -->"

                    mermaid_lines.append(f'    {source} {arrow_label} {target};')

                    if isinstance(probability, (int, float)):
                        if source not in probabilities_by_source:
                            probabilities_by_source[source] = []
                        probabilities_by_source[source].append(probability)

                user_mermaid_code = "\n".join(mermaid_lines)

                # --- Validation Check for Probabilities ---
                st.markdown("---")
                st.subheader("⚠️ Validation Warnings")
                has_warnings = False
                for node, probs in probabilities_by_source.items():
                    current_sum = sum(probs)
                    if abs(current_sum - 1.0) > 1e-9:
                        st.warning(f"Probabilities from **'{node}'** do not sum to 1.0 (Current sum: **{current_sum:.2f}**). Please adjust.")
                        has_warnings = True
                if not has_warnings:
                    st.success("All probabilities sum to 1.0 (or no probabilities found).")

                st.download_button(
                    label="Download Generated Mermaid Code",
                    data=user_mermaid_code,
                    file_name="my_generated_diagram.mmd",
                    mime="text/plain",
                    help="Download the Mermaid diagram code generated from the table."
                )

            with yaml_tab:
                st.subheader("📄 Diagram Data in YAML Format")
                st.code(yaml.dump(st.session_state.transitions_list, default_flow_style=False), language="yaml", height=500)
                st.info("This YAML dynamically reflects the data from the custom transitions input.")

    # --- Right Panel: Live Diagram Preview ---
    if st.session_state.show_right:
        with col_right:
            st.subheader("📊 Live Diagram Preview")

            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Mermaid Diagram</title>
                <script type="module">
                    import * as mermaid from 'https://unpkg.com/mermaid@10/dist/mermaid.min.js';
                    mermaid.initialize({{ startOnLoad: true }});
                </script>
                <style>
                    /* Ensure html and body take full height of the iframe */
                    html, body {{
                        height: 100%;
                        margin: 0;
                        padding: 0;
                        /* Use hidden for body to ensure iframe itself handles scroll */
                        overflow: hidden; 
                    }}
                    .mermaid {{
                        font-family: 'trebuchet ms', verdana, arial;
                        width: 100%;
                        height: 100%; /* Make mermaid div fill its parent (body/html) */
                        /* Changed to 'block' and `text-align: center` to center horizontally
                           without interfering with vertical scrolling. */
                        display: block;
                        text-align: center; /* Centers inline-block children (like the SVG output by Mermaid) */
                        overflow: auto; /* Make content scrollable if it overflows its fixed height */
                    }}
                </style>
            </head>
            <body>
                <div class="mermaid">
                    {user_mermaid_code}
                </div>
            </body>
            </html>
            """
            # The iframe itself is made scrollable if its content (the HTML above) overflows
            components.html(html_content, height=600, scrolling=True)

            st.markdown("---")
            st.info("This panel now displays the real-time visualization of your Mermaid.js diagram.")

elif page == "Simulate":
    st.subheader("📊 Simulation Output")
    st.info("Results will appear here based on the configured model.")
