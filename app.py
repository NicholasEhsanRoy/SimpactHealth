import streamlit as st
import streamlit.components.v1 as components
import yaml
import os
import pandas as pd
from datetime import datetime
import time
import graphviz
import tempfile

# ─── Temporary directories for configs & results ─────────────────────────────
if "tmpdir_obj" not in st.session_state:
    st.session_state.tmpdir_obj = tempfile.TemporaryDirectory(prefix="simpact-")
    st.session_state.tmpdir     = st.session_state.tmpdir_obj.name

CONFIGS_DIR = os.path.join(st.session_state.tmpdir, "configs")
RESULTS_DIR = os.path.join(st.session_state.tmpdir, "results")
os.makedirs(CONFIGS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ─── Session-state defaults ──────────────────────────────────────────────────
def _init(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

# Draw-tab state
_init('show_left',         True)
_init('show_right',        True)
_init('draw_model_name',   "My Simulation Model")
_init('draw_num_patients', 1000)
_init('initial_state',     "Healthy")                        # your custom start node
_init('prev_initial',      st.session_state.initial_state)
_init('transitions_list',  [{"source": st.session_state.initial_state,
                             "target": "Dead", "probability": 1.0}])
_init('timestep_unit',     "Week")

# Simulation-tab state
_init('loaded_name',       "")
_init('sim_initial_state', st.session_state.initial_state)
_init('sim_transitions',   list(st.session_state.transitions_list))
_init('sim_initial_patients', st.session_state.draw_num_patients)
_init('sim_timestep_unit', st.session_state.timestep_unit)
_init('sim_results_df',    None)
_init('custom_result_name',"")
_init('uploaded_parsed_config', None)

# ─── Helpers ────────────────────────────────────────────────────────────────

def save_config_file(name, cfg):
    path = os.path.join(CONFIGS_DIR, f"{name}.yaml")
    with open(path, 'w') as f:
        yaml.dump(cfg, f, default_flow_style=False)
    st.success(f"Saved configuration '{name}'.")

def list_configs():
    return [fn[:-5] for fn in os.listdir(CONFIGS_DIR) if fn.endswith('.yaml')]

def load_config_file(name):
    path = os.path.join(CONFIGS_DIR, f"{name}.yaml")
    return yaml.safe_load(open(path)) if os.path.exists(path) else None

def save_results(df, prefix="simulation_results"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{prefix}_{ts}.csv"
    df.to_csv(os.path.join(RESULTS_DIR, fname), index=False)
    st.success(f"Saved results '{fname}'.")
    return fname

def list_results():
    return [fn for fn in os.listdir(RESULTS_DIR) if fn.endswith('.csv')]

def load_results_file(name):
    return pd.read_csv(os.path.join(RESULTS_DIR, name))

# ─── Callbacks ──────────────────────────────────────────────────────────────

def toggle_left():
    st.session_state.show_left = not st.session_state.show_left

def toggle_right():
    st.session_state.show_right = not st.session_state.show_right

def add_transition():
    st.session_state.transitions_list.append({"source":"", "target":"", "probability":0.0})

def remove_transition():
    if st.session_state.transitions_list:
        st.session_state.transitions_list.pop()

def on_initial_change():
    old = st.session_state.prev_initial
    new = st.session_state.initial_state
    for t in st.session_state.transitions_list:
        if t['source'] == old:
            t['source'] = new
    st.session_state.prev_initial = new

def handle_upload():
    up = st.session_state.uploaded_config_file
    if not up:
        return
    try:
        cfg = yaml.safe_load(up.getvalue().decode('utf-8'))
        st.session_state.uploaded_parsed_config = cfg
        st.success(f"Parsed '{up.name}'.")
    except Exception as e:
        st.error(f"YAML parse error: {e}")

def apply_uploaded_config():
    cfg = st.session_state.uploaded_parsed_config or {}
    # Draw state
    st.session_state.draw_model_name    = cfg.get('model_name',   st.session_state.draw_model_name)
    st.session_state.draw_num_patients  = cfg.get('initial_patients', st.session_state.draw_num_patients)
    st.session_state.initial_state      = cfg.get('initial_state',   st.session_state.initial_state)
    st.session_state.prev_initial       = st.session_state.initial_state
    st.session_state.transitions_list   = cfg.get('transitions',      st.session_state.transitions_list)
    st.session_state.timestep_unit      = cfg.get('timestep_unit',    st.session_state.timestep_unit)
    st.success("Applied uploaded config.")

def apply_draw_config():
    name = st.session_state.load_config_draw
    if not name:
        return
    cfg = load_config_file(name) or {}
    st.session_state.draw_model_name    = cfg.get('model_name',   st.session_state.draw_model_name)
    st.session_state.draw_num_patients  = cfg.get('initial_patients', st.session_state.draw_num_patients)
    st.session_state.initial_state      = cfg.get('initial_state',   st.session_state.initial_state)
    st.session_state.prev_initial       = st.session_state.initial_state
    st.session_state.transitions_list   = cfg.get('transitions',      st.session_state.transitions_list)
    st.session_state.timestep_unit      = cfg.get('timestep_unit',    st.session_state.timestep_unit)
    st.success(f"Loaded '{name}' into Draw tab.")

def load_simulation_config():
    sel = st.session_state.sim_cfg_sel
    if not sel:
        return
    cfg = load_config_file(sel) or {}
    # copy into simulation-only vars
    st.session_state.sim_initial_state    = cfg.get('initial_state',     st.session_state.initial_state)
    st.session_state.sim_transitions      = cfg.get('transitions',       st.session_state.transitions_list)
    st.session_state.sim_initial_patients = cfg.get('initial_patients',  st.session_state.draw_num_patients)
    st.session_state.sim_timestep_unit    = cfg.get('timestep_unit',     st.session_state.timestep_unit)
    st.session_state.loaded_name          = sel
    st.success(f"Loaded '{sel}' for simulation.")

# ─── Layout ─────────────────────────────────────────────────────────────────

st.set_page_config(layout="wide", page_title="SimpactHealth")
st.sidebar.title("SimpactHealth")
page = st.sidebar.radio("Menu", ["Draw", "Simulate"])

if page == "Draw":
    # — Build mermaid source
    mer_lines = [
        "graph TD",
        f"    Start -- [{st.session_state.draw_num_patients}] --> {st.session_state.initial_state};"
    ]
    probs = {}
    for t in st.session_state.transitions_list:
        s,tgt,p = t['source'], t['target'], t['probability']
        if not s or not tgt:
            continue
        lbl = f" -- [{p}] -->" if isinstance(p,(int,float)) else " -->"
        mer_lines.append(f"    {s}{lbl} {tgt};")
        if isinstance(p,(int,float)):
            probs.setdefault(s, []).append(p)
    mer_code = "\n".join(mer_lines)

    # — Toggle buttons
    c1, c2 = st.columns(2)
    with c1:
        st.button("👈 Toggle Config Panel", on_click=toggle_left)
    with c2:
        st.button("👉 Toggle Diagram Panel", on_click=toggle_right)

    # — Panel layout
    if   st.session_state.show_left and st.session_state.show_right:
        colL, colR = st.columns([1, 2])
    elif st.session_state.show_left:
        colL, colR = st.columns([1, 0.01])
    else:
        colL, colR = st.columns([0.01, 1])

    # — Config panel
    if st.session_state.show_left:
        with colL:
            st.subheader("🛠 Diagram Configuration")
            tabA, tabB, tabC = st.tabs(["Setup", "Mermaid Editor", "YAML"])

            # Setup
            with tabA:
                st.file_uploader("Upload Configuration (YAML)",
                                 type=["yaml","yml"],
                                 key="uploaded_config_file",
                                 on_change=handle_upload)
                if st.session_state.uploaded_parsed_config:
                    st.button("Apply Uploaded Config", on_click=apply_uploaded_config)

                st.markdown("---")
                st.text_input("Config Name", key="save_config_name")
                csave, cload = st.columns([2,1])
                with cload:
                    if st.button("Save Config") and st.session_state.save_config_name:
                        cfg = {
                          "model_name":      st.session_state.draw_model_name,
                          "initial_patients":st.session_state.draw_num_patients,
                          "initial_state":   st.session_state.initial_state,
                          "transitions":     st.session_state.transitions_list,
                          "timestep_unit":   st.session_state.timestep_unit
                        }
                        save_config_file(st.session_state.save_config_name, cfg)

                st.selectbox("Load Config", options=[""]+list_configs(), key="load_config_draw")
                st.button("Apply Config", on_click=apply_draw_config)

                st.markdown("---")
                st.subheader("⚙️ Simulation Setup")
                st.text_input("Initial State Node",
                              value=st.session_state.initial_state,
                              key="initial_state",
                              on_change=on_initial_change)
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

            # Mermaid Editor
            with tabB:
                st.write("✍️ Define Custom Transitions")
                for i, t in enumerate(st.session_state.transitions_list):
                    c1, c2, c3 = st.columns([1,1,1])
                    with c1:
                        st.text_input("Source", value=t['source'], key=f"s{i}",
                                      on_change=lambda i=i: st.session_state.transitions_list.__setitem__(i, {**t, 'source': st.session_state[f"s{i}"]}))
                    with c2:
                        st.text_input("Target", value=t['target'], key=f"t{i}",
                                      on_change=lambda i=i: st.session_state.transitions_list.__setitem__(i, {**t, 'target': st.session_state[f"t{i}"]}))
                    with c3:
                        st.number_input("Probability",
                                        value=t['probability'],
                                        min_value=0.0,
                                        max_value=1.0,
                                        step=0.01,
                                        format="%.2f",
                                        key=f"p{i}",
                                        on_change=lambda i=i: st.session_state.transitions_list.__setitem__(i, {**t, 'probability': st.session_state[f"p{i}"]}))
                cadd, crem = st.columns([0.5,0.5])
                with cadd: st.button("➕ Add Transition", on_click=add_transition)
                with crem: st.button("➖ Remove Last",   on_click=remove_transition)

                st.markdown("---")
                bad = False
                for s, ps in probs.items():
                    if abs(sum(ps)-1.0) > 1e-6:
                        st.warning(f"Outgoing from '{s}' sum to {sum(ps):.2f}, not 1.0.")
                        bad = True
                if not bad:
                    st.success("All probabilities sum to 1.0.")

            # YAML
            with tabC:
                st.subheader("📄 Diagram Data in YAML Format")
                cur = {
                  "model_name":      st.session_state.draw_model_name,
                  "initial_patients":st.session_state.draw_num_patients,
                  "initial_state":   st.session_state.initial_state,
                  "transitions":     st.session_state.transitions_list,
                  "timestep_unit":   st.session_state.timestep_unit
                }
                st.code(yaml.dump(cur), language="yaml", height=300)

    # — Mermaid live preview (centered) ────────────────────────────────────────
    if st.session_state.show_right:
        with colR:
            st.subheader("📊 Live Diagram Preview")
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <script type="module">
                import m from 'https://unpkg.com/mermaid@10/dist/mermaid.esm.min.mjs';
                m.initialize({{startOnLoad:true}});
              </script>
              <style>
                body {{
                  margin:0;
                  height:100%;
                  display:flex;
                  justify-content:center;
                  align-items:center;
                }}
              </style>
            </head>
            <body>
              <div class="mermaid">
              {mer_code}
              </div>
            </body>
            </html>
            """
            components.html(html, height=600, scrolling=True)

# ─── SIMULATE TAB ─────────────────────────────────────────────────────────────
elif page == "Simulate":

    st.header("🔬 Run Simulation")
    tab1, tab2, tab3 = st.tabs(["Load Config","Run Simulation","Results"])

    # — Tab 1: Load a saved config into simulation-only state
    with tab1:
        st.selectbox("Select Config", options=[""]+list_configs(), key="sim_cfg_sel")
        if st.button("Load", key="load_sim_cfg_btn"):
            load_simulation_config()

    # — Tab 2: run using only sim_* variables
    with tab2:
        if st.session_state.loaded_name:
            st.info(f"Using config: {st.session_state.loaded_name}")
            st.text_input("Custom Results File Name (optional)",
                          key="custom_result_name")
            sim_initial = st.number_input(
                "Initial # People",
                value=st.session_state.sim_initial_patients,
                min_value=1,
                key="run_sim_initial"
            )
            sim_steps  = st.number_input(
                "Number of Simulation Steps", value=10, min_value=1, key="run_sim_steps"
            )
            sim_speed  = st.slider(
                "Simulation Speed (s/step)", 0.0, 1.0, 0.1, step=0.05, key="run_sim_speed"
            )
            sim_unit   = st.selectbox(
                "Timestep Unit",
                ["Year","Month","Week","Day"],
                index=["Year","Month","Week","Day"].index(st.session_state.sim_timestep_unit),
                key="run_sim_unit"
            )

            if st.button("Start Simulation"):
                # ALWAYS read from sim_*:
                initial_state = st.session_state.sim_initial_state
                transitions   = st.session_state.sim_transitions

                # build node set
                nodes = {t['source'] for t in transitions} | {t['target'] for t in transitions}
                nodes.add(initial_state)

                # initialize counts
                current = {n:0 for n in nodes}
                current[initial_state] = sim_initial

                # history DataFrame
                cols = sorted(current)
                history = pd.DataFrame(columns=['Step'] + cols)
                history.loc[0] = [f"{sim_unit} 0"] + [current[c] for c in cols]

                prog = st.progress(0)
                stat = st.empty()
                graph = st.empty()

                for i in range(1, sim_steps+1):
                    infl = {c:0 for c in cols}
                    out = {c:0 for c in cols}
                    for tr in transitions:
                        m = round(current[tr['source']] * tr['probability'])
                        out[tr['source']] += m
                        infl[tr['target']] += m
                    for c in cols:
                        current[c] = max(0, current[c] + infl[c] - out[c])

                    history.loc[i] = [f"{sim_unit} {i}"] + [current[c] for c in cols]
                    prog.progress(i/sim_steps)
                    stat.text(f"Step {i}/{sim_steps}")

                    dot = graphviz.Digraph(graph_attr={'rankdir':'LR'},
                                            node_attr={'shape':'ellipse'})
                    dot.node('Start','Start')
                    for c in cols:
                        dot.node(c, f"{c}\n({current[c]} patients)")
                    dot.edge('Start', initial_state, label=str(sim_initial))
                    for tr in transitions:
                        dot.edge(tr['source'], tr['target'], label=str(tr['probability']))
                    graph.graphviz_chart(dot, use_container_width=True)

                    time.sleep(sim_speed)

                st.session_state.sim_results_df = history
                prefix = (st.session_state.custom_result_name.strip() or "simulation_results")
                save_results(history, prefix=prefix)

    # — Tab 3: view or load past results
    with tab3:
        st.subheader("📄 Simulation Results")
        if st.session_state.sim_results_df is not None:
            st.dataframe(st.session_state.sim_results_df, use_container_width=True)
            csv = st.session_state.sim_results_df.to_csv(index=False).encode()
            st.download_button("Download Current Results",
                               data=csv,
                               file_name=f"{st.session_state.loaded_name}_results.csv",
                               mime="text/csv")
        past = list_results()
        if past:
            sel2 = st.selectbox("Load Past Results", options=past, key="res_sel")
            if sel2:
                df = load_results_file(sel2)
                st.dataframe(df, use_container_width=True)
                st.download_button("Download CSV",
                                   data=df.to_csv(index=False).encode(),
                                   file_name=sel2,
                                   mime="text/csv")
        else:
            st.info("No past results available.")
