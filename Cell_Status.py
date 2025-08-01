import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import random
import time

# Persistent global state initialization
if 'run_started' not in st.session_state:
    st.session_state['run_started'] = False
if 'task_timings' not in st.session_state:  # Per cell, per task duration
    st.session_state['task_timings'] = {}
if 'cells_data' not in st.session_state:  # Current cell data dict
    st.session_state['cells_data'] = {}
if 'overall_start' not in st.session_state:
    st.session_state['overall_start'] = None
if 'progress_count' not in st.session_state:
    st.session_state['progress_count'] = 0
if 'history' not in st.session_state:  # History to track time, power per cell and task
    st.session_state['history'] = {}

def get_cell_data(cell_type, voltage, current):
    min_voltage, max_voltage = (2.8, 3.6) if cell_type == 'LFP' else (3.2, 4.0)
    temp = round(random.uniform(25, 40), 1)
    capacity = round(voltage * abs(current), 2)
    return {
        "type": cell_type,
        "voltage": voltage,
        "current": current,
        "temp": temp,
        "capacity": capacity,
        "min_voltage": min_voltage,
        "max_voltage": max_voltage
    }

def process_task_on_cell(task, cell_data, user_voltage, user_current):
    start = time.perf_counter()
    if task == "CHARGE":
        # Charging: current positive, voltage tends to rise up to max
        cell_data['current'] = abs(user_current)  # enforce positive for charging
        cell_data['voltage'] = min(cell_data['max_voltage'], user_voltage + 0.2)
        cell_data['capacity'] = round(cell_data['voltage'] * cell_data['current'], 2)
        cell_data['temp'] = round(cell_data['temp'] + random.uniform(0.3, 0.9), 2)
    elif task == "DISCHARGE":
        # Discharging: current negative, voltage tends to drop down to min
        cell_data['current'] = -abs(user_current)  # enforce negative for discharging
        cell_data['voltage'] = max(cell_data['min_voltage'], user_voltage - 0.1)
        cell_data['capacity'] = round(cell_data['voltage'] * abs(cell_data['current']), 2)
        cell_data['temp'] = round(cell_data['temp'] + random.uniform(0.4, 1.1), 2)
    elif task == "IDLE":
        cell_data['current'] = 0.0
        cell_data['temp'] = max(20.0, round(cell_data['temp'] - random.uniform(0.1, 0.3), 2))
    elif task == "OPTIMIZING":
        cell_data['voltage'] = user_voltage
        cell_data['current'] = user_current
        cell_data['capacity'] = round(cell_data['voltage'] * abs(cell_data['current']), 2)
        cell_data['temp'] = round(cell_data['temp'] + random.uniform(-0.5, 0.5), 2)
    else:
        # Fallback: no change
        pass
    duration = time.perf_counter() - start
    return cell_data, duration

def create_progress(total_steps):
    return st.progress(0), total_steps

# --- Streamlit UI Setup ---
st.set_page_config(page_title="Battery Test Dashboard", layout="wide")
st.title("🔋 Advanced Battery Cell Dashboard with Charge/Discharge")

st.sidebar.header("Configure Cells & Tasks")

num_cells = st.sidebar.number_input("Number of Cells", min_value=1, max_value=6, value=3)
cell_types = []
for i in range(num_cells):
    ct = st.sidebar.selectbox(f"Cell #{i+1} Type", ['LFP', 'NMC'], key=f"celltype_{i}")
    cell_types.append(ct)

# Updated task list with CHARGE and DISCHARGE options
task_list = ["CHARGE", "DISCHARGE", "IDLE", "OPTIMIZING"]
selected_tasks = st.sidebar.multiselect(
    "Select Tasks in Sequence", task_list, default=["CHARGE", "IDLE"]
)

# User input for voltage and current per task and per cell
task_inputs = {}
for t in selected_tasks:
    st.sidebar.markdown(f"**{t} Setpoints:**")
    v_dict = {}
    c_dict = {}
    for i in range(num_cells):
        v_key, c_key = f"{t}_v_{i}", f"{t}_c_{i}"
        vold = 3.3 if cell_types[i] == 'LFP' else 3.6
        v = st.sidebar.number_input(
            f"{t} - Cell #{i+1} Voltage", min_value=2.5, max_value=4.4,
            value=float(vold), key=v_key
        )
        # Default currents: positive for charge, negative for discharge, zero for idle, 1.0 for optimizing
        if t == "CHARGE":
            c_default = 1.0
        elif t == "DISCHARGE":
            c_default = -1.0
        elif t == "IDLE":
            c_default = 0.0
        else:  # OPTIMIZING or others
            c_default = 1.0
        c = st.sidebar.number_input(
            f"{t} - Cell #{i+1} Current", min_value=-5.0, max_value=5.0,
            value=float(c_default), key=c_key
        )
        v_dict[f"Cell_{i+1}_{cell_types[i]}"] = v
        c_dict[f"Cell_{i+1}_{cell_types[i]}"] = c
    task_inputs[t] = {"voltage": v_dict, "current": c_dict}

start_btn = st.sidebar.button("▶️ Start Test")
stop_btn = st.sidebar.button("⏹ Stop Test")

if start_btn:
    st.session_state['run_started'] = True
    st.session_state['overall_start'] = time.perf_counter()
    st.session_state['cells_data'] = {}
    st.session_state['task_timings'] = {}
    st.session_state['history'] = {}
    st.session_state['progress_count'] = 0
    for i, ctype in enumerate(cell_types):
        key = f"Cell_{i+1}_{ctype}"
        # Use first selected task inputs for initialization
        first_task = selected_tasks[0]
        v0 = task_inputs[first_task]["voltage"][key]
        c0 = task_inputs[first_task]["current"][key]
        st.session_state['cells_data'][key] = get_cell_data(ctype, v0, c0)
        st.session_state['task_timings'][key] = []

if stop_btn:
    st.session_state['run_started'] = False

if st.session_state['run_started']:
    st.success("Testing running. Click ⏹ Stop when complete.")
    total_steps = len(selected_tasks) * num_cells
    progbar, total = create_progress(total_steps)

    timer_placeholder = st.empty()
    power_figs_placeholders = {cell_key: st.empty() for cell_key in st.session_state['cells_data'].keys()}

    start_overall = st.session_state['overall_start'] or time.perf_counter()

    # Run tasks with live updates
    for t_idx, task in enumerate(selected_tasks):
        for i, key in enumerate(st.session_state['cells_data']):
            user_v = task_inputs[task]["voltage"][key]
            user_c = task_inputs[task]["current"][key]

            # Process task
            cell_data, duration = process_task_on_cell(task, st.session_state['cells_data'][key], user_v, user_c)
            st.session_state['cells_data'][key] = cell_data
            st.session_state['task_timings'][key].append({
                "Task": task,
                "Duration (s)": round(duration, 5)
            })

            power = cell_data['voltage'] * cell_data['current']
            if key not in st.session_state['history']:
                st.session_state['history'][key] = []
            elapsed = time.perf_counter() - start_overall
            st.session_state['history'][key].append({
                'task': task,
                'time': elapsed,
                'power': power
            })

            # Update UI
            st.session_state['progress_count'] += 1
            progbar.progress(st.session_state['progress_count'] / total)
            timer_placeholder.markdown(f"**Elapsed Test Time:** {elapsed:.2f} seconds")

            # Update power graph live for this cell
            df_hist = pd.DataFrame(st.session_state['history'][key])
            fig_power = px.line(
                df_hist,
                x='time',
                y='power',
                color='task',
                markers=True,
                title=f"{key} - Time vs Power (Live)",
                labels={"time": "Elapsed Time (s)", "power": "Power (W)", "task": "Task"},
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            power_figs_placeholders[key].plotly_chart(fig_power, use_container_width=True)

            # Simulate delay for UI responsiveness (adjust or remove as needed)
            time.sleep(0.1)

    # Summary tables and charts after run
    st.header("Cell Data Overview")
    df_display = pd.DataFrame.from_dict(st.session_state['cells_data'], orient='index')
    df_display["Power (W)"] = df_display["voltage"] * df_display["current"]
    df_display2 = df_display.rename(columns={
        "type": "Cell Type", "voltage": "Voltage", "current": "Current",
        "temp": "Temperature (°C)", "capacity": "Capacity",
        "min_voltage": "Min Voltage", "max_voltage": "Max Voltage"
    })[["Cell Type", "Voltage", "Current", "Power (W)", "Temperature (°C)", "Capacity", "Min Voltage", "Max Voltage"]]
    st.dataframe(df_display2.style.highlight_max(axis=0, color="lightgreen"), height=250)

    st.header("⏱ Per-Task Per-Cell Duration (seconds)")
    rows = []
    for cell, l in st.session_state['task_timings'].items():
        for rec in l:
            rows.append({"Cell": cell, **rec})
    timing_table = pd.DataFrame(rows)
    st.dataframe(timing_table, height=200)

    # Pie and voltage bar charts
    col1, col2 = st.columns(2)
    with col1:
        type_counts = pd.Series(df_display2["Cell Type"]).value_counts()
        fig = px.pie(values=type_counts.values, names=type_counts.index, title="Cell Type Distribution", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(df_display2, x=df_display2.index, y="Voltage", color="Cell Type", title="Voltage Across Cells", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.header("Temperature Comparison")
    fig3 = px.bar(df_display2, x=df_display2.index, y="Temperature (°C)", color="Cell Type", title="Temperature Across Cells", color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.header("Individual Cell Gauges")
    gauges = st.columns(min(num_cells, 4))
    for i, (cell_key, d) in enumerate(st.session_state['cells_data'].items()):
        with gauges[i % 4]:
            fig_volt = go.Figure(go.Indicator(
                mode="gauge+number",
                value=d["voltage"],
                gauge={'axis': {'range': [d["min_voltage"], d["max_voltage"]]},
                       'bar': {'color': "darkblue"}},
                title={'text': f"{cell_key} Voltage (V)"}
            ))
            st.plotly_chart(fig_volt, use_container_width=True)

            fig_temp = go.Figure(go.Indicator(
                mode="gauge+number",
                value=d["temp"],
                gauge={'axis': {'range': [20, 45]},
                       'bar': {'color': "darkred"}},
                title={'text': f"{cell_key} Temp (°C)"}
            ))
            st.plotly_chart(fig_temp, use_container_width=True)

else:
    st.info("Configure cells/tasks and click ▶️ Start Test to begin. Use ⏹ Stop Test to halt the test.")
