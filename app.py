import streamlit as st
import streamlit.components.v1 as components
import yaml
import os
import pandas as pd
from datetime import datetime
import time # For simulation speed control
import graphviz # Import graphviz for drawing simulation flow

# --- Constants for File Paths ---
CONFIGS_DIR = ".configs"
RESULTS_DIR = ".results"

# --- Streamlit Page Configuration ---
st.set_page_config(layout="wide", page_title="SimpactHealth")

# --- Sidebar ---
st.sidebar.title("SimpactHealth")
page = st.sidebar.radio("Menu", ["Draw", "Simulate"])

# --- Session State Initialization ---
for side in ("show_left", "show_right"):
    if side not in st.session_state:
        st.session_state[side] = True

if 'transitions_list' not in st.session_state:
    st.session_state.transitions_list = [
        {"source": "Healthy", "target": "Dead", "probability": 1.0}
    ]
if 'draw_model_name' not in st.session_state:
    st.session_state.draw_model_name = "My Simulation Model"
if 'draw_num_patients' not in st.session_state:
    st.session_state.draw_num_patients = 1000
if 'timestep_unit' not in st.session_state:
    st.session_state.timestep_unit = "Week" # Default timestep unit
if 'selected_config_to_load' not in st.session_state: # For the new loading button logic
    st.session_state.selected_config_to_load = ""
if 'uploaded_parsed_config' not in st.session_state: # To store parsed but not yet applied config
    st.session_state.uploaded_parsed_config = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None


# For simulation page
if 'loaded_config_name' not in st.session_state:
    st.session_state.loaded_config_name = None
if 'loaded_config_data' not in st.session_state: # Store full config data
    st.session_state.loaded_config_data = {}
if 'sim_results_df' not in st.session_state:
    st.session_state.sim_results_df = None
if 'custom_result_name' not in st.session_state:
    st.session_state.custom_result_name = ""

# --- Helper Functions for File Operations ---
def ensure_dir(directory):
    """Ensures a directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_config(config_name, config_data): # Now accepts a dictionary
    """Saves the configuration data as a YAML file."""
    ensure_dir(CONFIGS_DIR)
    file_path = os.path.join(CONFIGS_DIR, f"{config_name}.yaml")
    with open(file_path, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    st.success(f"Configuration '{config_name}' saved successfully!")

def load_config(config_name):
    """Loads a configuration from a YAML file."""
    file_path = os.path.join(CONFIGS_DIR, f"{config_name}.yaml")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return data
    return None

def get_available_configs():
    """Returns a list of available configuration names."""
    ensure_dir(CONFIGS_DIR)
    return [f.replace('.yaml', '') for f in os.listdir(CONFIGS_DIR) if f.endswith('.yaml')]

def save_results(results_df, filename_prefix="simulation_results"):
    """
    Saves simulation results to a CSV file.
    Uses custom_result_name as filename if provided, otherwise uses a timestamped default.
    """
    ensure_dir(RESULTS_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # If custom name is provided and is not empty, use it directly (without timestamp)
    if st.session_state.custom_result_name.strip():
        file_name = f"{st.session_state.custom_result_name}.csv"
    else:
        # If no custom name, use default prefix + timestamp
        file_name = f"{filename_prefix}_{timestamp}.csv"

    file_path = os.path.join(RESULTS_DIR, file_name)
    results_df.to_csv(file_path, index=False)
    st.success(f"Simulation results saved to '{file_name}' in '{RESULTS_DIR}'!")
    return file_name

def load_results(file_name):
    """Loads simulation results from a CSV file."""
    file_path = os.path.join(RESULTS_DIR, file_name)
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None

def get_available_results():
    """Returns a list of available results file names."""
    ensure_dir(RESULTS_DIR)
    return [f for f in os.listdir(RESULTS_DIR) if f.endswith('.csv')]

# --- Graphviz DOT Generation Function ---
def generate_graphviz_dot(transitions, current_populations, initial_num_patients):
    """Generates a Graphviz DOT string for the simulation model with current populations."""
    dot = graphviz.Digraph(
        comment='Simulation Model',
        graph_attr={
            'rankdir': 'LR',  # Changed to Left-Right for horizontal layout
            'forcelabels': 'true'
        },
        node_attr={
            'fontsize': '8',     # Keep a reasonable small font size
            'shape': 'ellipse'   # Ensure consistent node shape
        },
        edge_attr={
            'fontsize': '7'      # Keep a reasonable small font size for edge labels
        }
    )

    # Add 'Start' node (conceptual, no population)
    dot.node('Start', label='Start')

    # Add 'Healthy' node with initial population
    dot.node('Healthy', label=f'Healthy\n({current_populations.get("Healthy", 0)} patients)')

    # Add fixed transition from Start to Healthy
    dot.edge('Start', 'Healthy', label=str(initial_num_patients))

    # Add other nodes and edges based on transitions_list
    all_nodes_in_transitions = set()
    for t in transitions:
        all_nodes_in_transitions.add(t["source"])
        all_nodes_in_transitions.add(t["target"])

    for node_name in all_nodes_in_transitions:
        if node_name not in ['Start', 'Healthy']:
            dot.node(node_name, label=f'{node_name}\n({current_populations.get(node_name, 0)} patients)')

    for t in transitions:
        source_node = t["source"]
        target_node = t["target"]
        probability = t["probability"]

        if source_node not in dot.body and source_node != 'Start' and source_node != 'Healthy':
             dot.node(source_node, label=f'{source_node}\n({current_populations.get(source_node, 0)} patients)')
        if target_node not in dot.body and target_node != 'Start' and target_node != 'Healthy':
             dot.node(target_node, label=f'{current_populations.get(target_node, 0)} patients)')

        dot.edge(source_node, target_node, label=str(probability))

    return dot.source

# --- Toggle Functions ---
def toggle_left():
    st.session_state.show_left = not st.session_state.show_left

def toggle_right():
    st.session_state.show_right = not st.session_state.show_right

def add_transition_row():
    st.session_state.transitions_list.append({"source": "", "target": "", "probability": 0.0})

def remove_last_transition_row():
    if st.session_state.transitions_list:
        st.session_state.transitions_list.pop()

def load_config_into_draw_action(): # This function is now called by a button
    """Loads a selected configuration into the 'Draw' tab's UI elements."""
    config_name = st.session_state.load_config_draw_selector_value # Get value from selectbox
    if config_name:
        loaded_data = load_config(config_name)
        if loaded_data:
            if isinstance(loaded_data, dict):
                st.session_state.draw_model_name = loaded_data.get("model_name", "My Simulation Model")
                st.session_state.draw_num_patients = loaded_data.get("initial_patients", 1000)
                st.session_state.transitions_list = loaded_data.get("transitions", [{"source": "Healthy", "target": "Dead", "probability": 1.0}])
                st.session_state.timestep_unit = loaded_data.get("timestep_unit", "Week")
            elif isinstance(loaded_data, list):
                st.warning("Loaded an old configuration format. Defaulting model name, people, and timestep.")
                st.session_state.draw_model_name = "My Simulation Model"
                st.session_state.draw_num_patients = 1000
                st.session_state.transitions_list = loaded_data
                st.session_state.timestep_unit = "Week"
            
            st.success(f"Configuration '{config_name}' loaded into Draw tab.")
            st.rerun() # Rerun to update the UI with loaded data
        else:
            st.error(f"Failed to load configuration '{config_name}'.")
    else:
        st.warning("Please select a configuration to load.")

def validate_config_data(data):
    """
    Validates the structure and content of the loaded configuration data.
    Returns (True, "Success message") or (False, "Error message").
    """
    if not isinstance(data, dict):
        return False, "Invalid configuration format: Expected a dictionary."

    required_keys = {
        "model_name": str,
        "initial_patients": (int, float),
        "transitions": list,
        "timestep_unit": str
    }

    for key, expected_type in required_keys.items():
        if key not in data:
            return False, f"Missing required key: '{key}' in configuration."
        if not isinstance(data[key], expected_type):
            return False, f"Invalid type for key '{key}': Expected {expected_type}, got {type(data[key])}."

    # Specific validation for transitions
    if not data["transitions"]:
        return True, "Configuration valid (no transitions defined)." # Allow empty transitions for initial setup

    for i, transition in enumerate(data["transitions"]):
        if not isinstance(transition, dict):
            return False, f"Invalid transition format at index {i}: Expected a dictionary, got {type(transition)}."
        
        if "source" not in transition or not isinstance(transition["source"], str):
            return False, f"Invalid 'source' in transition at index {i}: Expected string."
        if "target" not in transition or not isinstance(transition["target"], str):
            return False, f"Invalid 'target' in transition at index {i}: Expected string."
        if "probability" not in transition or not isinstance(transition["probability"], (int, float)):
            return False, f"Invalid 'probability' in transition at index {i}: Expected number."
        if not (0.0 <= transition["probability"] <= 1.0):
            return False, f"Invalid 'probability' in transition at index {i}: Must be between 0.0 and 1.0."
            
    # Check for valid timestep unit
    valid_timestep_units = ["Year", "Month", "Week", "Day"]
    if data["timestep_unit"] not in valid_timestep_units:
        return False, f"Invalid 'timestep_unit': Expected one of {valid_timestep_units}, got '{data['timestep_unit']}'."

    return True, "Configuration is valid."

def handle_uploaded_file():
    """Reads the uploaded file and stores parsed data in session state for later application."""
    uploaded_file = st.session_state.uploaded_config_file
    if uploaded_file is not None:
        try:
            file_content = uploaded_file.getvalue().decode("utf-8")
            loaded_data = yaml.safe_load(file_content)
            
            # Store parsed data and original file name
            st.session_state.uploaded_parsed_config = loaded_data
            st.session_state.uploaded_file_name = uploaded_file.name
            st.info(f"File '{uploaded_file.name}' uploaded and parsed. Click 'Apply Uploaded Config' to load it.")
        except yaml.YAMLError as e:
            st.error(f"Error parsing YAML file: {e}. Please ensure it's a valid YAML format.")
            st.session_state.uploaded_parsed_config = None # Clear on error
            st.session_state.uploaded_file_name = None
        except Exception as e:
            st.error(f"An unexpected error occurred during file processing: {e}")
            st.session_state.uploaded_parsed_config = None
            st.session_state.uploaded_file_name = None
    else:
        st.session_state.uploaded_parsed_config = None # Clear if file is deselected
        st.session_state.uploaded_file_name = None

def apply_uploaded_config_action():
    """Applies the parsed uploaded configuration to the app's state."""
    if st.session_state.uploaded_parsed_config is not None:
        valid, message = validate_config_data(st.session_state.uploaded_parsed_config)
        if valid:
            config_data = st.session_state.uploaded_parsed_config
            if isinstance(config_data, dict):
                st.session_state.draw_model_name = config_data.get("model_name", "My Uploaded Model")
                st.session_state.draw_num_patients = config_data.get("initial_patients", 1000)
                st.session_state.transitions_list = config_data.get("transitions", [{"source": "Healthy", "target": "Dead", "probability": 1.0}])
                st.session_state.timestep_unit = config_data.get("timestep_unit", "Week")
                st.success(f"Configuration from '{st.session_state.uploaded_file_name}' applied successfully!")
            elif isinstance(config_data, list):
                st.warning("Uploaded an old configuration format (list of transitions). Defaulting model name, people, and timestep.")
                st.session_state.draw_model_name = "My Uploaded Model"
                st.session_state.draw_num_patients = 1000
                st.session_state.transitions_list = config_data
                st.session_state.timestep_unit = "Week"
                st.success(f"Configuration from '{st.session_state.uploaded_file_name}' applied successfully!")
            
            # Clear uploaded config data after applying
            st.session_state.uploaded_parsed_config = None
            st.session_state.uploaded_file_name = None
            st.rerun()
        else:
            st.error(f"Uploaded configuration is invalid: {message}")
    else:
        st.warning("No file uploaded or parsed yet to apply.")


# --- Main Application Logic ---
if page == "Draw":
    # --- Mermaid Code Generation (moved to global scope within Draw page) ---
    mermaid_lines = ["graph TD"]
    mermaid_lines.append(f'    Start -- [{st.session_state.draw_num_patients}] --> Healthy;')

    probabilities_by_source = {}
    
    # Initialize with a default if no transitions to avoid errors before user input
    user_mermaid_code = "graph TD\n    No_Transitions_Yet; " 

    if st.session_state.transitions_list:
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
            # Create three tabs: Setup, Mermaid Editor, YAML
            setup_tab, gui_tab, yaml_tab = st.tabs(["Setup", "Mermaid Editor", "YAML"])

            with setup_tab:
                st.subheader("⚙️ Simulation Setup")
                
                # Upload Configuration
                st.markdown("---")
                st.subheader("⬆️ Upload Configuration (YAML)")
                st.file_uploader(
                    "Choose a YAML file",
                    type=["yaml", "yml"],
                    key="uploaded_config_file",
                    on_change=handle_uploaded_file # Trigger handling on file change
                )
                if st.session_state.uploaded_parsed_config is not None:
                    if st.button("Apply Uploaded Config", key="apply_uploaded_config_btn"):
                        apply_uploaded_config_action()
                
                st.markdown("---")
                
                # Load Existing Configuration
                st.subheader("📂 Load Existing Configuration")
                available_configs_for_draw = get_available_configs()
                load_col, button_col = st.columns([0.7, 0.3])
                with load_col:
                    if available_configs_for_draw:
                        st.selectbox(
                            "Select a saved configuration:",
                            options=[""] + available_configs_for_draw,
                            key="load_config_draw_selector_value" # Changed key to avoid direct on_change trigger
                        )
                    else:
                        st.info("No saved configurations found. Create and save one below.")
                with button_col:
                    st.write("") # Spacer for alignment
                    st.write("") # Spacer for alignment
                    st.button("Load Config", on_click=load_config_into_draw_action)
                
                st.markdown("---")

                # Rely on session state for value and remove default 'value' and 'index' parameters
                st.text_input("Model Name", key="draw_model_name")
                st.number_input("Initial Number of People", min_value=1, key="draw_num_patients")
                
                st.selectbox(
                    "Timestep Unit",
                    options=["Year", "Month", "Week", "Day"],
                    key="timestep_unit"
                )

                # --- Save Configuration ---
                st.markdown("---")
                st.subheader("💾 Save Configuration")
                config_save_name = st.text_input("Configuration Name", key="config_save_name")
                save_button_clicked = st.button("Save Configuration", key="save_config_btn")

                if save_button_clicked and config_save_name:
                    config_data_to_save = {
                        "model_name": st.session_state.draw_model_name,
                        "initial_patients": st.session_state.draw_num_patients,
                        "transitions": st.session_state.transitions_list,
                        "timestep_unit": st.session_state.timestep_unit
                    }
                    if config_save_name + ".yaml" in os.listdir(CONFIGS_DIR):
                        st.warning(f"Configuration '{config_save_name}' already exists.")
                        overwrite_confirm = st.checkbox("Overwrite existing configuration?", key="overwrite_config")
                        if overwrite_confirm:
                            save_config(config_save_name, config_data_to_save)
                            st.session_state.overwrite_confirmed = True # Set a flag
                            st.rerun() # Rerun to clear checkbox
                    else:
                        save_config(config_save_name, config_data_to_save)
                        st.session_state.overwrite_confirmed = False # Reset flag
                        st.rerun() # Rerun to clear input
                elif save_button_clicked and not config_save_name:
                    st.error("Please enter a configuration name.")
                
                st.markdown("---")
                st.subheader("⬇️ Download Configuration")
                current_config_data = {
                    "model_name": st.session_state.draw_model_name,
                    "initial_patients": st.session_state.draw_num_patients,
                    "transitions": st.session_state.transitions_list,
                    "timestep_unit": st.session_state.timestep_unit
                }
                st.download_button(
                    label="Download Current Configuration (YAML)",
                    data=yaml.dump(current_config_data, default_flow_style=False),
                    file_name=f"{st.session_state.draw_model_name.replace(' ', '_').lower()}_config.yaml",
                    mime="text/yaml",
                    help="Download the currently defined configuration as a YAML file."
                )


            with gui_tab: # This is the Mermaid Editor tab
                st.subheader("✍️ Define Custom Transitions")
                st.write("Add rows to define custom nodes and arrows. Probabilities for outgoing arrows from a node should sum to 1.0.")

                with st.expander("Expand to define transitions", expanded=True):
                    # Using a Streamlit container with fixed height for internal scrolling
                    scrollable_container = st.container(height=350)

                    with scrollable_container:
                        for i, transition in enumerate(st.session_state.transitions_list):
                            t_col1, t_col2, t_col3 = st.columns([1, 1, 0.8])
                            with t_col1:
                                transition["source"] = st.text_input(
                                    f"Source Node",
                                    value=transition.get("source", ""),
                                    key=f"source_{i}"
                                )
                            with t_col2:
                                transition["target"] = st.text_input(
                                    f"Target Node",
                                    value=transition.get("target", ""),
                                    key=f"target_{i}"
                                )
                            with t_col3:
                                transition["probability"] = st.number_input(
                                    f"Probability",
                                    value=transition.get("probability", 0.0),
                                    min_value=0.0,
                                    max_value=1.0,
                                    format="%.2f",
                                    step=0.01,
                                    key=f"prob_{i}"
                                )
                            if i < len(st.session_state.transitions_list) -1:
                                st.markdown('<hr style="margin: 5px 0;">', unsafe_allow_html=True)

                btn_col1, btn_col2 = st.columns([0.2, 1])
                with btn_col1:
                    st.button("➕ Add Transition", on_click=add_transition_row)
                with btn_col2:
                    st.button("➖ Remove Last", on_click=remove_last_transition_row)


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
                
                # Removed duplicate download button from here


            with yaml_tab:
                st.subheader("📄 Diagram Data in YAML Format")
                # Display the data that would be saved
                display_config_data = {
                    "model_name": st.session_state.draw_model_name,
                    "initial_patients": st.session_state.draw_num_patients,
                    "transitions": st.session_state.transitions_list,
                    "timestep_unit": st.session_state.timestep_unit
                }
                st.code(yaml.dump(display_config_data, default_flow_style=False), language="yaml", height=500)
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
                    html, body {{
                        height: 100%;
                        margin: 0;
                        padding: 0;
                        overflow: hidden;
                    }}
                    .mermaid {{
                        font-family: 'trebuchet ms', verdana, arial;
                        width: 100%;
                        height: 100%;
                        display: block;
                        text-align: center; /* Centers inline-block children (like the SVG output by Mermaid) */
                        overflow: auto;
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
            components.html(html_content, height=600, scrolling=True)

            st.markdown("---")
            st.info("This panel now displays the real-time visualization of your Mermaid.js diagram.")

# --- Simulate Page Logic ---
elif page == "Simulate":
    st.header("🔬 Run Simulation")

    sim_tab1, sim_tab2, sim_tab3 = st.tabs(["Load Configuration", "Run Simulation", "Results"])

    with sim_tab1:
        st.subheader("📂 Load Simulation Configuration")
        available_configs = get_available_configs()
        if available_configs:
            selected_config = st.selectbox(
                "Select a saved configuration:",
                options=[""] + available_configs, # Add empty option
                key="simulate_config_selector"
            )
            if selected_config:
                loaded_data = load_config(selected_config)
                if loaded_data:
                    st.session_state.loaded_config_data = loaded_data # Store full config data
                    st.session_state.loaded_config_name = selected_config
                    st.success(f"Configuration '{selected_config}' loaded successfully!")
                    st.subheader("Loaded Configuration Details (YAML):")
                    st.code(yaml.dump(loaded_data, default_flow_style=False), language="yaml")
                else:
                    st.error(f"Failed to load configuration '{selected_config}'.")
            else:
                st.info("Please select a configuration to load.")
        else:
            st.warning("No saved configurations found. Go to 'Draw' tab to save one.")

    with sim_tab2:
        st.subheader("🚀 Run Simulation")
        if st.session_state.loaded_config_name:
            st.info(f"Using configuration: **{st.session_state.loaded_config_name}**")
            
            # Simulation parameters loaded from config, with ability to override
            st.text_input(
                "Custom Results File Name (optional)",
                value=st.session_state.custom_result_name,
                key="custom_result_name",
                help="Enter a name for your results file. If left empty, a default name with timestamp will be used."
            )

            sim_initial_patients = st.number_input(
                "Initial Number of People for Simulation", # Changed label
                min_value=1,
                value=st.session_state.loaded_config_data.get("initial_patients", 1000),
                key="sim_initial_patients"
            )
            sim_steps = st.number_input("Number of Simulation Steps (Time Units)", min_value=1, value=10, key="sim_steps")
            sim_speed = st.slider("Simulation Speed (seconds per step)", min_value=0.0, max_value=1.0, value=0.1, step=0.05, key="sim_speed")
            
            sim_timestep_unit = st.selectbox(
                "Timestep Unit",
                options=["Year", "Month", "Week", "Day"],
                key="sim_timestep_unit",
                index=["Year", "Month", "Week", "Day"].index(st.session_state.loaded_config_data.get("timestep_unit", "Week"))
            )

            run_simulation_button = st.button("Start Simulation", key="run_simulation_btn")

            if run_simulation_button:
                st.write("---")
                st.subheader("Live Simulation Progress")
                
                # Determine all unique states involved in the transitions
                # Use transitions from loaded_config_data
                sim_transitions = st.session_state.loaded_config_data.get("transitions", [])
                all_sim_nodes = set()
                for t in sim_transitions:
                    all_sim_nodes.add(t["source"])
                    all_sim_nodes.add(t["target"])
                
                # Initialize state populations
                current_populations = {node: 0 for node in all_sim_nodes}
                current_populations['Healthy'] = sim_initial_patients # Assume 'Healthy' is the initial state from 'Start' node
                if 'Start' in current_populations: # 'Start' is conceptual for the diagram, remove from population tracking
                    del current_populations['Start']
                
                # Ensure all nodes are sorted for consistent DataFrame columns
                sorted_sim_nodes = sorted(list(current_populations.keys()))

                # Create a DataFrame to store historical populations
                history_df = pd.DataFrame(columns=['Step'] + sorted_sim_nodes)
                # First step:
                history_df.loc[0] = [f"{sim_timestep_unit} 0"] + [current_populations[s] for s in sorted_sim_nodes]


                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Initialize the Graphviz display area once
                graph_display_area = st.empty() 

                for step in range(1, sim_steps + 1):
                    new_populations = current_populations.copy()
                    
                    # Calculate net changes for each state based on transitions
                    inflows_per_state = {node: 0 for node in sorted_sim_nodes}
                    outflows_per_state = {node: 0 for node in sorted_sim_nodes}

                    for transition in sim_transitions: # Use sim_transitions from loaded config
                        source = transition["source"]
                        target = transition["target"]
                        probability = transition["probability"]

                        if source in current_populations and current_populations[source] > 0:
                            num_moving = round(current_populations[source] * probability)
                            
                            outflows_per_state[source] += num_moving
                            inflows_per_state[target] += num_moving
                    
                    # Apply all calculated changes for the step
                    for node in sorted_sim_nodes:
                        new_populations[node] = current_populations[node] + inflows_per_state.get(node, 0) - outflows_per_state.get(node, 0)
                        new_populations[node] = max(0, new_populations[node])

                    current_populations = new_populations # Update populations for next step

                    # Update history - format step string
                    history_df.loc[step] = [f"{sim_timestep_unit} {step}"] + [current_populations[s] for s in sorted_sim_nodes]
                    
                    # Update UI
                    progress_bar.progress(step / sim_steps)
                    status_text.text(f"Simulating Step {step}/{sim_steps} ({sim_timestep_unit} per step)...")
                    
                    # Generate and update Graphviz diagram in the placeholder
                    dot_source = generate_graphviz_dot(
                        transitions=sim_transitions, # Use sim_transitions
                        current_populations=current_populations,
                        initial_num_patients=sim_initial_patients
                    )
                    # Update the content of the pre-allocated empty container
                    graph_display_area.graphviz_chart(dot_source, use_container_width=True)
                    
                    time.sleep(sim_speed) # Control simulation speed

                status_text.success("Simulation Complete!")
                st.session_state.sim_results_df = history_df # Store final results
                saved_file_name = save_results(history_df) # Pass custom name implicitly
                
                st.markdown(f"**Final State Populations:**")
                st.dataframe(pd.DataFrame([current_populations]))


        else:
            st.info("Please load a configuration in the 'Load Configuration' tab to run a simulation.")

    with sim_tab3:
        st.subheader("📄 Simulation Results")
        available_results = get_available_results()
        if available_results:
            selected_result_file = st.selectbox(
                "Select a results file to inspect:",
                options=[""] + available_results,
                key="inspect_results_selector"
            )
            if selected_result_file:
                df_to_display = load_results(selected_result_file)
                if df_to_display is not None:
                    st.dataframe(df_to_display, use_container_width=True)
                    
                    csv_data = df_to_display.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name=selected_result_file,
                        mime="text/csv",
                        key="download_results_btn"
                    )
                else:
                    st.error(f"Failed to load results from '{selected_result_file}'.")
            else:
                st.info("Select a results file from the dropdown to view its content.")
        elif st.session_state.sim_results_df is not None:
            st.info("No saved results found, but current simulation results are available:")
            st.dataframe(st.session_state.sim_results_df, use_container_width=True)
            csv_data = st.session_state.sim_results_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Current Simulation Results",
                data=csv_data,
                file_name=f"{st.session_state.loaded_config_name}_current_sim_results.csv",
                mime="text/csv",
                key="download_current_results_btn"
            )
        else:
            st.warning("No simulation results available yet. Run a simulation in the 'Run Simulation' tab.")
