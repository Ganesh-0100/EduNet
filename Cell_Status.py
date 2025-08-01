import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import random
import time
import numpy as np

# Persistent state initialization
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

# Cell data initiation
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

# Task processing logic with charge/discharge semantics
def process_task_on_cell(task, cell_data, user_voltage, user_current):
    start = time.perf_counter()
    if task == "CHARGE":
        cell_data['current'] = abs(user_current)
        cell_data['voltage'] = min(cell_data['max_voltage'], user_voltage + 0.2)
        cell_data['capacity'] = round(cell_data['voltage'] * cell_data['current'], 2)
        cell_data['temp'] = round(cell_data['temp'] + random.uniform(0.3, 0.9), 2)
    elif task == "DISCHARGE":
        cell_data['current'] = -abs(user_current)
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

# -------- Streamlit UI Setup ---------
st.set_page_config(page_title="Battery Testing Dashboard 3D Visualization", layout="wide")
st.title("🔋 Battery Test Dashboard with 3D Visualizations and Live Timing")

# Sidebar configuration
st.sidebar.header("Configure Cells and Tasks")

num_cells = st.sidebar.number_input("Number of Cells", min_value=1, max_value=6, value=3)
cell_types = []
for i in range(num_cells):
    ct = st.sidebar.selectbox(f"Cell #{i+1} Type", ['LFP', 'NMC'], key=f"celltype_{i}")
    cell_types.append(ct)

task_list = ["CHARGE", "DISCHARGE", "IDLE", "OPTIMIZING"]
selected_tasks = st.sidebar.multiselect(
    "Select Tasks in Sequence", task_list, default=["CHARGE", "IDLE"]
)

# User input for each task and cell
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
        c_default = 1.0 if t == "CHARGE" else (-1.0 if t=="DISCHARGE" else (0.0 if t=="IDLE" else 1.0))
        c = st.sidebar.number_input(
            f"{t} - Cell #{i+1} Current", min_value=-5.0, max_value=5.0,
            value=float(c_default), key=c_key
        )
        v_dict[f"Cell_{i+1}_{cell_types[i]}"] = v
        c_dict[f"Cell_{i+1}_{cell_types[i]}"] = c
    task_inputs[t] = {"voltage": v_dict, "current": c_dict}

start_btn = st.sidebar.button("▶️ Start Test")
stop_btn = st.sidebar.button("⏹ Stop Test")

# Start logic
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
    st.success("Test running. Click ⏹ Stop when complete.")
    total_steps = len(selected_tasks) * num_cells
    progbar, total = create_progress(total_steps)

    timer_placeholder = st.empty()
    # placeholders for power graphs per cell
    power_figs_placeholders = {cell_key: st.empty() for cell_key in st.session_state['cells_data'].keys()}

    start_overall = st.session_state['overall_start'] or time.perf_counter()

    # Run the tasks with live updates
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

            # Update UI components
            st.session_state['progress_count'] += 1
            progbar.progress(st.session_state['progress_count'] / total)
            timer_placeholder.markdown(f"**Elapsed Test Time:** {elapsed:.2f} seconds")

            # Update live power vs time chart by cell
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

            time.sleep(0.1)  # for UI smoothness

    # Prepare dataframe for display, adding Power column
    st.header("Cell Data Overview")
    df_display = pd.DataFrame.from_dict(st.session_state['cells_data'], orient='index')
    df_display["Power (W)"] = df_display["voltage"] * df_display["current"]
    df_display2 = df_display.rename(columns={
        "type": "Cell Type", "voltage": "Voltage", "current": "Current",
        "temp": "Temperature (°C)", "capacity": "Capacity",
        "min_voltage": "Min Voltage", "max_voltage": "Max Voltage"
    })[["Cell Type", "Voltage", "Current", "Power (W)", "Temperature (°C)", "Capacity", "Min Voltage", "Max Voltage"]]

    # 3D TABLE simulation using heatmap (voltage, current, power)
    # Create a grid for 3D table: cells as y axis, parameters as x axis
    parameters = ["Voltage", "Current", "Power (W)", "Temperature (°C)"]
    z_data = df_display2[parameters].values

    fig_table_3d = go.Figure(data=[go.Surface(
        z=z_data,
        x=np.arange(len(parameters)),
        y=np.arange(len(df_display2)),
        colorscale='Viridis',
        showscale=True,
        colorbar=dict(title='Value')
    )])
    fig_table_3d.update_layout(
        title="3D Table of Cell Parameters",
        scene=dict(
            xaxis=dict(tickvals=list(range(len(parameters))), ticktext=parameters, title="Parameter"),
            yaxis=dict(tickvals=list(range(len(df_display2))), ticktext=df_display2.index.tolist(), title="Cell"),
            zaxis=dict(title="Value")
        ),
        height=500,
        margin=dict(l=0, r=0, b=0, t=50)
    )
    st.plotly_chart(fig_table_3d, use_container_width=True)

    # 3D BAR chart: Power across Cells and Tasks
    power_matrix = np.zeros((num_cells, len(selected_tasks)))
    for i, cell_key in enumerate(st.session_state['cells_data']):
        for j, task in enumerate(selected_tasks):
            # Find the last recorded power for that cell & task, fallback to 0
            history = st.session_state['history'].get(cell_key, [])
            power_val = 0
            for h in reversed(history):
                if h['task'] == task:
                    power_val = h['power']
                    break
            power_matrix[i][j] = power_val

    x_vals = list(range(len(selected_tasks)))
    y_vals = list(range(num_cells))
    dx = dy = 0.6

    # Use pastel color sequence cycling per cell
    pastel_colors = px.colors.qualitative.Pastel

    fig_bar3d = go.Figure()
    for i in range(num_cells):
        for j in range(len(selected_tasks)):
            fig_bar3d.add_trace(go.Bar3d(
                x=[j], y=[i], z=[0],
                dx=dx, dy=dy,
                dz=[power_matrix[i][j]],
                opacity=0.8,
                marker=dict(color=pastel_colors[i % len(pastel_colors)]),
                name=f"Cell {i+1} - {selected_tasks[j]}",
                showlegend=(j==0)
            ))

    fig_bar3d.update_layout(
        scene=dict(
            xaxis=dict(tickvals=x_vals, ticktext=selected_tasks, title='Task'),
            yaxis=dict(tickvals=y_vals, ticktext=[f'Cell_{i+1}' for i in range(num_cells)], title='Cell'),
            zaxis=dict(title='Power (W)'),
            bgcolor="rgb(245,245,245)"
        ),
        title="3D Power Distribution Bar Chart",
        height=600,
        margin=dict(l=0, r=0, b=0, t=50),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    st.plotly_chart(fig_bar3d, use_container_width=True)

    # 3D PIE chart simulation (radial scatter with elevation)
    type_counts = pd.Series(df_display2["Cell Type"]).value_counts()
    labels = type_counts.index.tolist()
    values = type_counts.values

    # Compute angles for slices
    angles = np.cumsum(values / values.sum() * 2 * np.pi)
    angles = np.insert(angles, 0, 0)

    xs, ys, zs = [], [], []
    colors = pastel_colors
    for i in range(len(labels)):
        # Create sector arc
        theta = np.linspace(angles[i], angles[i+1], 100)
        r = 1
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        z = np.linspace(0, 0.4, len(theta))  # height for 3d effect
        xs.extend(x)
        ys.extend(y)
        zs.extend(z)

    fig_pie3d = go.Figure()

    # Create offset slices to simulate depth layers by type
    offset = 0
    for i, label in enumerate(labels):
        # Create a wedge in 3D
        theta_i = np.linspace(angles[i], angles[i+1], 50)
        r = 1
        x_i = r * np.cos(theta_i)
        y_i = r * np.sin(theta_i)
        z_i = np.linspace(0, 0.3, 50)

        fig_pie3d.add_trace(go.Scatter3d(
            x=x_i,
            y=y_i,
            z=z_i + offset,
            mode='lines',
            line=dict(color=colors[i], width=8),
            name=f"{label} ({values[i]})",
            showlegend=True
        ))
        offset += 0.35

    fig_pie3d.update_layout(
        title="3D Pie Chart Approximation of Cell Types",
        legend=dict(y=0.9, x=0.8),
        margin=dict(l=0, r=0, b=0, t=40),
        height=500
    )
    st.plotly_chart(fig_pie3d, use_container_width=True)

    # 3D Scatter plot: Voltage vs Power vs Current with color by cell type
    all_data = []
    for cell_key, entries in st.session_state['history'].items():
        for entry in entries:
            all_data.append({
                "cell": cell_key,
                "voltage": entry['voltage'],
                "power": entry['power'],
                "current": entry['current'],
                "task": entry['task'],
                "time": entry['time'],
                "cell_type": st.session_state['cells_data'][cell_key]['type']
            })
    df_all = pd.DataFrame(all_data)

    if not df_all.empty:
        fig_3d_scatter = px.scatter_3d(
            df_all,
            x="voltage",
            y="power",
            z="current",
            color="cell_type",
            symbol="task",
            title="Voltage vs Power vs Current by Cell Type and Task",
            labels={"voltage": "Voltage (V)", "power": "Power (W)", "current": "Current (A)"},
            color_discrete_sequence=px.colors.qualitative.Pastel,
            size_max=18,
            opacity=0.8,
            hover_data=["cell", "time", "task"]
        )
        st.plotly_chart(fig_3d_scatter, use_container_width=True)

    # Traditional charts preserved: Voltage bar chart & Temperature bar chart
    col1, col2 = st.columns(2)
    with col1:
        # 2D pie chart for backup
        fig_pie = px.pie(values=type_counts.values, names=type_counts.index,
                         title="Cell Type Distribution (2D Pie)", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        fig_voltage_bar = px.bar(df_display2, x=df_display2.index, y="Voltage", color="Cell Type",
                                title="Voltage Across Cells (2D Bar)", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_voltage_bar, use_container_width=True)

    st.markdown("---")
    st.header("Temperature Comparison")
    fig_temp_bar = px.bar(df_display2, x=df_display2.index, y="Temperature (°C)", color="Cell Type",
                          title="Temperature Across Cells (2D Bar)", color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig_temp_bar, use_container_width=True)

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
