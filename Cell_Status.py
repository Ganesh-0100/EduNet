import streamlit as st
import random
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

def get_cell_data(cell_type):
    voltage = 3.2 if cell_type.lower() == "lfp" else 3.6
    min_voltage = 2.8 if cell_type.lower() == "lfp" else 3.2
    max_voltage = 3.6 if cell_type.lower() == "lfp" else 4.0
    current = 0.0
    temp = round(random.uniform(25, 40), 1)
    capacity = round(voltage * current, 2)
    return {
        "voltage": voltage,
        "current": current,
        "temp": temp,
        "capacity": capacity,
        "min_voltage": min_voltage,
        "max_voltage": max_voltage,
        "type": cell_type.upper()
    }

def process_task_on_cell(task, cell_data):
    if task.upper() == "CC_CV":
        cell_data['current'] = 1.0
        cell_data['voltage'] = min(cell_data['max_voltage'], cell_data['voltage'] + 0.2)
        cell_data['capacity'] = round(cell_data['voltage'] * cell_data['current'], 2)
        cell_data['temp'] = round(cell_data['temp'] + random.uniform(0.2, 0.8), 2)
    elif task.upper() == "CC_CD":
        cell_data['current'] = -1.0
        cell_data['voltage'] = max(cell_data['min_voltage'], cell_data['voltage'] - 0.1)
        cell_data['capacity'] = round(cell_data['voltage'] * abs(cell_data['current']), 2)
        cell_data['temp'] = round(cell_data['temp'] + random.uniform(0.3, 1.0), 2)
    elif task.upper() == "IDLE":
        cell_data['current'] = 0.0
        cell_data['temp'] = max(20.0, round(cell_data['temp'] - random.uniform(0.1, 0.3), 2))
    return cell_data

def multitask(cells_data, tasks):
    for task in tasks:
        for key in cells_data:
            cells_data[key] = process_task_on_cell(task, cells_data[key])
    return cells_data

def plot_pie_chart(cell_types):
    type_counts = pd.Series(cell_types).value_counts()
    fig = px.pie(values=type_counts.values, names=type_counts.index, title="Cell Type Distribution",
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig, use_container_width=True)

def plot_bar_chart(df, column, title, color_col=None):
    fig = px.bar(df, x=df.index, y=column, color=color_col,
                 labels={column: title, 'index': 'Cell'}, title=title,
                 color_continuous_scale='RdYlGn_r' if color_col else px.colors.qualitative.Set3)
    st.plotly_chart(fig, use_container_width=True)

def plot_speedometer(value, title, min_val, max_val):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        delta={'reference': (min_val + max_val)/2, 'increasing': {'color': "red"}},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [min_val, (min_val + max_val) / 2], 'color': "lightgreen"},
                {'range': [(min_val + max_val) / 2, max_val], 'color': "red"}],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': value}}))
    fig.update_layout(height=300, margin={'t': 50, 'b': 0, 'l': 0, 'r': 0}, title=title)
    st.plotly_chart(fig, use_container_width=True)

# Streamlit UI setup
st.set_page_config(page_title="Advanced Battery Cell Dashboard", layout="wide")
st.title("🔋 Advanced Battery Cell Dashboard with Visualizations")

# Sidebar inputs
st.sidebar.header("Configure Cells and Tasks")

num_cells = st.sidebar.number_input("Number of Cells", min_value=1, max_value=10, value=3, step=1)
cell_type_options = ['LFP', 'NMC']

cell_types = []
for i in range(num_cells):
    cell_type = st.sidebar.selectbox(f"Type for Cell #{i+1}", options=cell_type_options, key=f"cell_type_{i}")
    cell_types.append(cell_type)

task_options = ["CC_CV", "CC_CD", "IDLE"]
selected_tasks = st.sidebar.multiselect("Select Tasks in Sequence", options=task_options)

if st.sidebar.button("Initialize / Run Tasks"):

    # Initialize cells dictionary
    cells_data = {}
    for idx, ctype in enumerate(cell_types, 1):
        cell_key = f"Cell_{idx}_{ctype}"
        cells_data[cell_key] = get_cell_data(ctype)

    # Run selected tasks on cells
    if selected_tasks:
        cells_data = multitask(cells_data, selected_tasks)

    # Prepare dataframe for display
    df = pd.DataFrame.from_dict(cells_data, orient='index')
    df_display = df.rename(columns={
        "voltage": "Voltage",
        "current": "Current",
        "temp": "Temperature (°C)",
        "capacity": "Capacity",
        "min_voltage": "Min Voltage",
        "max_voltage": "Max Voltage",
        "type": "Cell Type"
    })[["Cell Type", "Voltage", "Current", "Temperature (°C)", "Capacity", "Min Voltage", "Max Voltage"]]

    st.subheader("Cell Data Overview")
    st.dataframe(df_display.style.highlight_max(axis=0, color="lightgreen"), height=300)

    # Layout columns for charts
    col1, col2 = st.columns(2)

    with col1:
        plot_pie_chart(cell_types)

    with col2:
        plot_bar_chart(df_display, "Voltage", "Voltage Across Cells", color_col="Cell Type")

    st.markdown("---")

    st.subheader("Temperature Comparison")
    plot_bar_chart(df_display, "Temperature (°C)", "Temperature Across Cells", color_col="Cell Type")

    st.markdown("---")

    st.subheader("Individual Cell Gauges")
    gauge_cols = st.columns(min(num_cells, 4))
    for i, (cell_name, data) in enumerate(cells_data.items()):
        with gauge_cols[i % 4]:
            plot_speedometer(data["voltage"], f"{cell_name} Voltage (V)", data["min_voltage"], data["max_voltage"])
            plot_speedometer(data["temp"], f"{cell_name} Temperature (°C)", 20, 45)

else:
    st.info("Configure cells and tasks in the sidebar, then click 'Initialize / Run Tasks'")
