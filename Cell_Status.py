import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import random
import time
import os

# ========== Persistent global state initialization ===========
if 'run_started' not in st.session_state:
    st.session_state['run_started'] = False
if 'task_timings' not in st.session_state:
    st.session_state['task_timings'] = {}
if 'cells_data' not in st.session_state:
    st.session_state['cells_data'] = {}
if 'overall_start' not in st.session_state:
    st.session_state['overall_start'] = None
if 'progress_count' not in st.session_state:
    st.session_state['progress_count'] = 0
if 'history' not in st.session_state:
    st.session_state['history'] = {}

# ========== Helpers ===========
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
        cell_data['current'] = abs(user_current)  # positive current
        cell_data['voltage'] = min(cell_data['max_voltage'], user_voltage + 0.2)
        cell_data['capacity'] = round(cell_data['voltage'] * cell_data['current'], 2)
        cell_data['temp'] = round(cell_data['temp'] + random.uniform(0.3, 0.9), 2)
    elif task == "DISCHARGE":
        cell_data['current'] = -abs(user_current)  # negative current
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
    duration = time.perf_counter() - start
    return cell_data, duration

def create_progress(total_steps):
    return st.progress(0), total_steps

# ========== Streamlit UI ==========

st.set_page_config(page_title="Battery Test Dashboard Final", layout="wide")
st.title("🔋 Advanced Battery Cell Dashboard with Logging and CSV Export")

st.sidebar.header("Configure Cells & Tasks")

num_cells = st.sidebar.number_input("Number of Cells", min_value=1, max_value=6, value=3)
cell_types = []
for i in range(num_cells):
    ct = st.sidebar.selectbox(f"Cell #{i+1} Type", ['LFP', 'NMC'], key=f"celltype_{i}")
    cell_types.append(ct)

task_list = ["CHARGE", "DISCHARGE", "IDLE", "OPTIMIZING"]
selected_tasks = st.sidebar.multiselect(
    "Select Tasks in Sequence", task_list, default=["CHARGE", "IDLE"]
)

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
    power_figs_placeholders = {key: st.empty() for key in st.session_state['cells_data'].keys()}

    start_overall = st.session_state['overall_start'] or time.perf_counter()

    for t_idx, task in enumerate(selected_tasks):
        for i, key in enumerate(st.session_state['cells_data']):
            user_v = task_inputs[task]["voltage"][key]
            user_c = task_inputs[task]["current"][key]

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
                'power': power,
                'voltage': cell_data['voltage'],
                'current': cell_data['current']
            })

            # Update UI
            st.session_state['progress_count'] += 1
            progbar.progress(st.session_state['progress_count'] / total)
            timer_placeholder.markdown(f"**Elapsed Test Time:** {elapsed:.2f} seconds")

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

            time.sleep(0.1)

    # Summary
    st.header("Cell Data Overview")
    df_display = pd.DataFrame.from_dict(st.session_state['cells_data'], orient='index')
    df_display["Power (W)"] = df_display["voltage"] * df_display["current"]
    df_display2 = df_display.rename(columns={
        "type": "Cell Type",
        "voltage": "Voltage",
        "current": "Current",
        "temp": "Temperature (°C)",
        "capacity": "Capacity",
        "min_voltage": "Min Voltage",
        "max_voltage": "Max Voltage"
    })[["Cell Type", "Voltage", "Current", "Power (W)", "Temperature (°C)", "Capacity", "Min Voltage", "Max Voltage"]]
    st.dataframe(df_display2.style.highlight_max(axis=0, color="lightgreen"), height=250)

    st.header("⏱ Per-Task Per-Cell Duration (seconds)")
    rows = []
    for cell, l in st.session_state['task_timings'].items():
        for rec in l:
            rows.append({"Cell": cell, **rec})
    timing_table = pd.DataFrame(rows)
    st.dataframe(timing_table, height=200)

    col1, col2 = st.columns(2)
    with col1:
        type_counts = pd.Series(df_display2["Cell Type"]).value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="Cell Type Distribution",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(
            df_display2,
            x=df_display2.index,
            y="Voltage",
            color="Cell Type",
            title="Voltage Across Cells",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.header("Temperature Comparison")
    fig3 = px.bar(
        df_display2,
        x=df_display2.index,
        y="Temperature (°C)",
        color="Cell Type",
        title="Temperature Across Cells",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.header("Individual Cell Gauges")
    gauges = st.columns(min(num_cells, 4))
    for i, (cell_key, d) in enumerate(st.session_state['cells_data'].items()):
        with gauges[i % 4]:
            fig_volt = go.Figure(go.Indicator(
                mode="gauge+number",
                value=d["voltage"],
                gauge={'axis': {'range': [d["min_voltage"], d["max_voltage"]]}, 'bar': {'color': "darkblue"}},
                title={'text': f"{cell_key} Voltage (V)"}
            ))
            st.plotly_chart(fig_volt, use_container_width=True)

            fig_temp = go.Figure(go.Indicator(
                mode="gauge+number",
                value=d["temp"],
                gauge={'axis': {'range': [20, 45]}, 'bar': {'color': "darkred"}},
                title={'text': f"{cell_key} Temp (°C)"}
            ))
            st.plotly_chart(fig_temp, use_container_width=True)

    # --- CSV Logging and Download Section ---
    st.markdown("---")
    st.header("📋 Logged Readings Table & CSV Export")

    all_records = []
    for cell_key, histories in st.session_state['history'].items():
        for record in histories:
            all_records.append({
                "Cell": cell_key,
                "Task": record['task'],
                "Elapsed Time (s)": round(record['time'], 2),
                "Voltage (V)": round(record.get('voltage', 0), 3),
                "Current (A)": round(record.get('current', 0), 3),
                "Power (W)": round(record.get('power', 0), 3)
            })

    if all_records:
        df_history = pd.DataFrame(all_records)
        st.dataframe(df_history, height=300)

        csv_file = "cell_readings.csv"
        if os.path.exists(csv_file):
            # Append without header to avoid duplicates
            df_history.to_csv(csv_file, mode='a', index=False, header=False)
        else:
            df_history.to_csv(csv_file, index=False)

        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        st.download_button(
            label="📥 Download Full CSV Log",
            data=csv_data,
            file_name=csv_file,
            mime='text/csv',
        )
    else:
        st.info("No readings recorded yet. Run a test to start logging.")

else:
    st.info("Configure cells/tasks and click ▶️ Start Test to begin. Use ⏹ Stop Test to halt the test.")
