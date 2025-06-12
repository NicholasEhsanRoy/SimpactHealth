import streamlit as st
import streamlit.components.v1 as components
import yaml
import os
import pandas as pd
from datetime import datetime
import time
import graphviz
import tempfile

# --- Session-scoped temporary directories for configs & results ---
if "tmpdir_obj" not in st.session_state:
    st.session_state.tmpdir_obj = tempfile.TemporaryDirectory(prefix="simpact-")
    st.session_state.tmpdir     = st.session_state.tmpdir_obj.name
CONFIGS_DIR = os.path.join(st.session_state.tmpdir, "configs")
RESULTS_DIR = os.path.join(st.session_state.tmpdir, "results")
os.makedirs(CONFIGS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# --- Session state defaults ---
def _init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

_init_state('show_left', True)
_init_state('show_right', True)
_init_state('draw_model_name', "My Simulation Model")
_init_state('draw_num_patients', 1000)
# initial_state must come before transitions_list
_init_state('initial_state', "Healthy")
_init_state('prev_initial_state', st.session_state.initial_state)
_init_state('transitions_list', [
    {"source": st.session_state.initial_state, "target": "Dead", "probability": 1.0}
])
_init_state('timestep_unit', "Week")
_init_state('loaded_config_name', "")
_init_state('loaded_config_data', {})
_init_state('sim_results_df', None)
_init_state('custom_result_name', "")
_init_state('uploaded_parsed_config', None)
_init_state('uploaded_file_name', None)

# --- Propagate initial_state changes into transitions_list when you edit it ---
def handle_initial_state_change():
    old = st.session_state.prev_initial_state
    new = st.session_state.initial_state
    for t in st.session_state.transitions_list:
        if t['source'] == old:
            t['source'] = new
    st.session_state.prev_initial_state = new

# --- Helpers for configs & results ---
def save_config_file(name, config):
    path = os.path.join(CONFIGS_DIR, f"{name}.yaml")
    with open(path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    st.success(f"Saved configuration '{name}'.")

def list_configs():
    return [f[:-5] for f in os.listdir(CONFIGS_DIR) if f.endswith('.yaml')]

def load_config_file(name):
    path = os.path.join(CONFIGS_DIR, f"{name}.yaml")
    if os.path.exists(path):
        with open(path) as f:
            return yaml.safe_load(f)
    return None

def save_results_temp(df, prefix="simulation_results"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{prefix}_{ts}.csv"
    df.to_csv(os.path.join(RESULTS_DIR, fname), index=False)
    st.success(f"Saved results '{fname}'.")
    return fname

def list_results():
    return [f for f in os.listdir(RESULTS_DIR) if f.endswith('.csv')]

def load_results_file(name):
    return pd.read_csv(os.path.join(RESULTS_DIR, name))

# --- Other callbacks ---
def toggle_left():  st.session_state.show_left  = not st.session_state.show_left
def toggle_right(): st.session_state.show_right = not st.session_state.show_right
def add_transition_row():    st.session_state.transitions_list.append({"source": "", "target": "", "probability": 0.0})
def remove_last_transition_row():
    if st.session_state.transitions_list:
        st.session_state.transitions_list.pop()

def handle_uploaded_config():
    up = st.session_state.uploaded_config_file
    if not up: return
    try:
        data = yaml.safe_load(up.getvalue().decode('utf-8'))
        st.session_state.uploaded_parsed_config = data
        st.session_state.uploaded_file_name     = up.name
        st.success(f"Parsed '{up.name}'. Click 'Apply Uploaded Config'.")
    except Exception as e:
        st.error(f"YAML parse error: {e}")
        st.session_state.uploaded_parsed_config = None

def apply_uploaded_config():
    cfg = st.session_state.uploaded_parsed_config
    if not isinstance(cfg, dict):
        st.error("Uploaded config invalid."); return
    st.session_state.draw_model_name   = cfg.get('model_name',      st.session_state.draw_model_name)
    st.session_state.draw_num_patients = cfg.get('initial_patients',st.session_state.draw_num_patients)
    st.session_state.initial_state     = cfg.get('initial_state',   st.session_state.initial_state)
    st.session_state.prev_initial_state= st.session_state.initial_state
    st.session_state.transitions_list  = cfg.get('transitions',     st.session_state.transitions_list)
    st.session_state.timestep_unit     = cfg.get('timestep_unit',   st.session_state.timestep_unit)
    st.session_state.uploaded_parsed_config = None
    st.session_state.uploaded_file_name     = None
    st.success("Applied uploaded config.")

def apply_draw_config():
    name = st.session_state.load_config_draw
    cfg  = load_config_file(name)
    if not cfg:
        st.error(f"Config '{name}' not found."); return
    st.session_state.draw_model_name    = cfg.get('model_name',      st.session_state.draw_model_name)
    st.session_state.draw_num_patients  = cfg.get('initial_patients',st.session_state.draw_num_patients)
    st.session_state.initial_state      = cfg.get('initial_state',   st.session_state.initial_state)
    st.session_state.prev_initial_state = st.session_state.initial_state
    st.session_state.transitions_list   = cfg.get('transitions',     st.session_state.transitions_list)
    st.session_state.timestep_unit      = cfg.get('timestep_unit',   st.session_state.timestep_unit)
    st.success(f"Loaded config '{name}' into Draw tab.")

# --- Layout ---
st.set_page_config(layout="wide", page_title="SimpactHealth")
st.sidebar.title("SimpactHealth")
page = st.sidebar.radio("Menu", ["Draw","Simulate"])

if page == "Draw":
    # Build Mermaid
    mer_lines = [
        "graph TD",
        f"    Start -- [{st.session_state.draw_num_patients}] --> {st.session_state.initial_state};"
    ]
    probs = {}
    for t in st.session_state.transitions_list:
        s, tgt, p = t['source'], t['target'], t['probability']
        if not s or not tgt: continue
        lbl = f" -- [{p}] -->" if isinstance(p,(int,float)) else " -->"
        mer_lines.append(f"    {s}{lbl} {tgt};")
        if isinstance(p,(int,float)): probs.setdefault(s,[]).append(p)
    mer_code = "\n".join(mer_lines)

    # Toggles
    c1,c2 = st.columns(2)
    with c1: st.button("👈 Toggle Config Panel", on_click=toggle_left)
    with c2: st.button("👉 Toggle Diagram Panel", on_click=toggle_right)

    if st.session_state.show_left and st.session_state.show_right:
        colL,colR = st.columns([1,2])
    elif st.session_state.show_left:
        colL,colR = st.columns([1,0.01])
    else:
        colL,colR = st.columns([0.01,1])

    # Config panel
    if st.session_state.show_left:
        with colL:
            st.subheader("🛠 Diagram Configuration")
            setup_tab, edit_tab, yaml_tab = st.tabs(["Setup","Mermaid Editor","YAML"])

            with setup_tab:
                st.subheader("⬆️ Upload Configuration (YAML)")
                st.file_uploader("Choose YAML file",
                                 type=["yaml","yml"],
                                 key="uploaded_config_file",
                                 on_change=handle_uploaded_config)
                if st.session_state.uploaded_parsed_config:
                    if st.button("Apply Uploaded Config"):
                        apply_uploaded_config()

                st.markdown("---")
                st.subheader("💾 Save / Load Configuration")
                cn,cb = st.columns([2,1])
                with cn:
                    save_name = st.text_input("Config Name", key="save_config_name")
                with cb:
                    st.markdown("<br>",unsafe_allow_html=True)
                    if st.button("Save Config") and save_name:
                        cfg = {
                            "model_name":      st.session_state.draw_model_name,
                            "initial_patients":st.session_state.draw_num_patients,
                            "initial_state":   st.session_state.initial_state,
                            "transitions":     st.session_state.transitions_list,
                            "timestep_unit":   st.session_state.timestep_unit
                        }
                        save_config_file(save_name, cfg)

                avail = list_configs()
                st.selectbox("Load Config", options=[""]+avail, key="load_config_draw")
                if st.button("Apply Config"):
                    apply_draw_config()

                st.markdown("---")
                st.subheader("⚙️ Simulation Setup")
                st.text_input("Initial State Node",
                              value=st.session_state.initial_state,
                              key="initial_state",
                              on_change=handle_initial_state_change)
                st.text_input("Model Name",
                              value=st.session_state.draw_model_name,
                              key="draw_model_name")
                st.number_input("Initial Number of People",
                                value=st.session_state.draw_num_patients,
                                min_value=1,
                                key="draw_num_patients")
                st.selectbox("Timestep Unit",
                             ["Year","Month","Week","Day"],
                             index=["Year","Month","Week","Day"].index(st.session_state.timestep_unit),
                             key="timestep_unit")

                st.markdown("---")
                cur = {
                    "model_name":      st.session_state.draw_model_name,
                    "initial_patients":st.session_state.draw_num_patients,
                    "initial_state":   st.session_state.initial_state,
                    "transitions":     st.session_state.transitions_list,
                    "timestep_unit":   st.session_state.timestep_unit
                }
                st.download_button("Download Current Configuration (YAML)",
                                   data=yaml.dump(cur),
                                   file_name="config.yaml",
                                   mime="text/yaml")

            with edit_tab:
                st.write("✍️ Define Custom Transitions (outgoing sum to 1.0)")
                for i,t in enumerate(st.session_state.transitions_list):
                    c1,c2,c3 = st.columns([1,1,1])
                    with c1: t['source']      = st.text_input("Source Node", t['source'], key=f"src_{i}")
                    with c2: t['target']      = st.text_input("Target Node", t['target'], key=f"tgt_{i}")
                    with c3:
                        t['probability'] = st.number_input("Probability",
                                                           value=t['probability'],
                                                           min_value=0.0,
                                                           max_value=1.0,
                                                           format="%.2f",
                                                           step=0.01,
                                                           key=f"prob_{i}")
                a,b = st.columns([0.5,0.5])
                with a: st.button("➕ Add Transition", on_click=add_transition_row)
                with b: st.button("➖ Remove Last", on_click=remove_last_transition_row)

                st.markdown("---")
                for s,ps in probs.items():
                    tot = sum(ps)
                    if abs(tot-1.0)>1e-6:
                        st.warning(f"Probabilities from '{s}' sum to {tot:.2f}, not 1.0.")
                else:
                    st.success("All probabilities sum to 1.0.")

            with yaml_tab:
                st.subheader("📄 Diagram Data in YAML Format")
                st.code(yaml.dump(cur), language="yaml", height=300)

    # Diagram panel
    if st.session_state.show_right:
        with colR:
            st.subheader("📊 Live Diagram Preview")
            html = f"""
            <!DOCTYPE html>
            <html><head><script type=module>
            import m from 'https://unpkg.com/mermaid@10/dist/mermaid.esm.min.mjs';
            m.initialize({{startOnLoad:true}});
            </script></head><body>
            <div class="mermaid"
                 style="display:flex;justify-content:center;align-items:center;width:100%;height:100%;">
            {mer_code}
            </div></body></html>
            """
            components.html(html, height=600, scrolling=True)

elif page == "Simulate":
    st.header("🔬 Run Simulation")
    tab1,tab2,tab3 = st.tabs(["Load Configuration","Run Simulation","Results"])

    with tab1:
        avail = list_configs()
        sel   = st.selectbox("Select Config", options=[""]+avail, key="sim_cfg_sel")
        if sel and st.button("Load", key="load_sim_cfg_btn"):
            cfg = load_config_file(sel)
            # pull in initial_state from that config as well:
            st.session_state.initial_state     = cfg.get('initial_state', st.session_state.initial_state)
            st.session_state.loaded_config_data= cfg
            st.session_state.loaded_config_name= sel
            st.success(f"Loaded '{sel}' for simulation.")

    with tab2:
        if st.session_state.loaded_config_name:
            st.info(f"Using config: {st.session_state.loaded_config_name}")
            st.text_input("Custom Results File Name (optional)", key="custom_result_name")

            sim_initial = st.number_input(
                "Initial Number of People",
                value=st.session_state.loaded_config_data.get('initial_patients',1000),
                min_value=1,
                key="sim_initial"
            )
            sim_steps = st.number_input("Number of Simulation Steps", value = 10, min_value=1, key="sim_steps")
            sim_speed = st.slider("Simulation Speed (s/step)", 0.0,1.0,0.1,step=0.05, key="sim_speed")
            sim_unit  = st.selectbox("Timestep Unit",
                                     ["Year","Month","Week","Day"],
                                     index=["Year","Month","Week","Day"].index(
                                         st.session_state.loaded_config_data.get('timestep_unit','Week')
                                     ),
                                     key="sim_unit")

            if st.button("Start Simulation"):
                initial_state = st.session_state.initial_state
                trans = st.session_state.loaded_config_data.get('transitions',[])
                nodes = {t['source'] for t in trans} | {t['target'] for t in trans}
                nodes.add(initial_state)

                current = {n:0 for n in nodes}
                current[initial_state] = sim_initial

                cols = sorted(current.keys())
                history = pd.DataFrame(columns=['Step']+cols)
                history.loc[0] = [f"{sim_unit} 0"] + [current[c] for c in cols]

                prog = st.progress(0); stat = st.empty(); g = st.empty()
                for i in range(1, sim_steps+1):
                    infl = {c:0 for c in cols}; out = {c:0 for c in cols}
                    for tr in trans:
                        m = round(current.get(tr['source'],0)*tr['probability'])
                        out[tr['source']]+=m; infl[tr['target']]+=m
                    for c in cols:
                        current[c] = max(0, current[c] + infl[c] - out[c])

                    history.loc[i] = [f"{sim_unit} {i}"] + [current[c] for c in cols]
                    prog.progress(i/sim_steps); stat.text(f"Step {i}/{sim_steps}")

                    dot = graphviz.Digraph(graph_attr={'rankdir':'LR'},
                                           node_attr={'shape':'ellipse'})
                    dot.node('Start','Start')
                    for c in cols:
                        dot.node(c, f"{c}\n({current[c]} patients)")
                    # now uses your loaded initial_state:
                    dot.edge('Start', initial_state, label=str(sim_initial))
                    for tr in trans:
                        dot.edge(tr['source'], tr['target'], label=str(tr['probability']))
                    g.graphviz_chart(dot, use_container_width=True)

                    time.sleep(sim_speed)

                st.session_state.sim_results_df = history
                if st.session_state.custom_result_name.strip():
                    save_results_temp(history, prefix=st.session_state.custom_result_name.strip())
                else:
                    save_results_temp(history)

    with tab3:
        st.subheader("📄 Simulation Results")
        if st.session_state.sim_results_df is not None:
            st.dataframe(st.session_state.sim_results_df, use_container_width=True)
            csv = st.session_state.sim_results_df.to_csv(index=False).encode()
            st.download_button("Download Current Results",
                               data=csv,
                               file_name=f"{st.session_state.loaded_config_name}_results.csv",
                               mime="text/csv")
        past = list_results()
        if past:
            sel2 = st.selectbox("Load Past Results", options=past, key="res_sel")
            if sel2:
                df = load_results_file(sel2)
                st.dataframe(df, use_container_width=True)
                st.download_button("Download CSV", data=df.to_csv(index=False).encode(),
                                   file_name=sel2, mime="text/csv")
        else:
            st.info("No past results available.")
