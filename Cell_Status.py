import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO

# --- Page Config ---
st.set_page_config(page_title="EV Cell Testing Dashboard", layout="wide")

# --- Title ---
st.title("🔋 EV Cell Capacity Testing Dashboard")
st.markdown("Detailed analysis for 4 NMC and 4 LFP cells with individual charts, capacity distributions, and charging/discharging metrics.")

st.markdown("---")

# --- Load Sample Data with 8 cells ---
@st.cache_data
def load_data():
    csv_data = StringIO("""
Time,Cell_ID,Cell_Type,Mode,Voltage,Current,Temperature,Capacity,Status
2025-07-01 10:00:00,CELL001,LFP,Charge,3.20,0.5,35.0,1200,Active
2025-07-01 10:05:00,CELL001,LFP,Charge,3.25,0.6,35.5,1250,Active
2025-07-01 10:00:00,CELL002,NMC,Discharge,3.80,0.7,36.0,1100,Active
2025-07-01 10:05:00,CELL002,NMC,Discharge,3.75,0.65,36.2,1150,Active
2025-07-01 10:00:00,CELL003,NMC,Charge,3.60,0.4,34.5,1300,Active
2025-07-01 10:05:00,CELL003,NMC,Charge,3.65,0.45,34.8,1350,Active
2025-07-01 10:00:00,CELL004,LFP,Discharge,3.10,0.55,33.8,1180,Active
2025-07-01 10:05:00,CELL004,LFP,Discharge,3.12,0.50,33.5,1175,Active
2025-07-01 10:00:00,CELL005,NMC,Charge,3.70,0.48,34.2,1280,Active
2025-07-01 10:05:00,CELL005,NMC,Charge,3.72,0.50,34.3,1290,Active
2025-07-01 10:00:00,CELL006,LFP,Charge,3.22,0.52,35.1,1210,Active
2025-07-01 10:05:00,CELL006,LFP,Charge,3.24,0.54,35.2,1230,Active
2025-07-01 10:00:00,CELL007,NMC,Discharge,3.78,0.68,36.1,1120,Active
2025-07-01 10:05:00,CELL007,NMC,Discharge,3.74,0.66,36.0,1115,Active
2025-07-01 10:00:00,CELL008,LFP,Discharge,3.15,0.53,34.0,1190,Active
2025-07-01 10:05:00,CELL008,LFP,Discharge,3.17,0.55,34.2,1200,Active
    """)
    df = pd.read_csv(csv_data)
    df['Time'] = pd.to_datetime(df['Time'])
    return df

df = load_data()

# --- Helper function to plot individual cell charts ---
def plot_cell_charts(cell_df, cell_id):
    st.markdown(f"### 📊 Cell {cell_id} ({cell_df['Cell_Type'].iloc[0]})")
    cols = st.columns(2)
    
    with cols[0]:
        fig_v = px.line(cell_df, x="Time", y="Voltage", title=f"Voltage over Time for {cell_id}", markers=True)
        st.plotly_chart(fig_v, use_container_width=True)
    
    with cols[1]:
        fig_c = px.line(cell_df, x="Time", y="Current", title=f"Current over Time for {cell_id}", markers=True)
        st.plotly_chart(fig_c, use_container_width=True)
    
    cols2 = st.columns(2)
    with cols2[0]:
        fig_t = px.line(cell_df, x="Time", y="Temperature", title=f"Temperature over Time for {cell_id}", markers=True)
        st.plotly_chart(fig_t, use_container_width=True)
    
    with cols2[1]:
        fig_cap = px.line(cell_df, x="Time", y="Capacity", title=f"Capacity over Time for {cell_id}", markers=True)
        st.plotly_chart(fig_cap, use_container_width=True)

# --- Function to calculate charging and discharging summary per cell ---
def charging_discharging_summary(df):
    summary_list = []
    for cell in df["Cell_ID"].unique():
        cell_data = df[df["Cell_ID"] == cell]
        
        charge_data = cell_data[cell_data["Mode"] == "Charge"]
        discharge_data = cell_data[cell_data["Mode"] == "Discharge"]
        
        charge_capacity = charge_data["Capacity"].max() - charge_data["Capacity"].min() if not charge_data.empty else 0
        discharge_capacity = discharge_data["Capacity"].max() - discharge_data["Capacity"].min() if not discharge_data.empty else 0
        
        avg_charge_current = charge_data["Current"].mean() if not charge_data.empty else 0
        avg_discharge_current = discharge_data["Current"].mean() if not discharge_data.empty else 0
        
        charge_time = (charge_data["Time"].max() - charge_data["Time"].min()).total_seconds()/60 if len(charge_data) > 1 else 0
        discharge_time = (discharge_data["Time"].max() - discharge_data["Time"].min()).total_seconds()/60 if len(discharge_data) > 1 else 0
        
        efficiency = (discharge_capacity / charge_capacity * 100) if charge_capacity > 0 else None
        
        summary_list.append({
            "Cell_ID": cell,
            "Charge Capacity (mAh)": charge_capacity,
            "Discharge Capacity (mAh)": discharge_capacity,
            "Avg Charge Current (A)": avg_charge_current,
            "Avg Discharge Current (A)": avg_discharge_current,
            "Charge Time (min)": charge_time,
            "Discharge Time (min)": discharge_time,
            "Charge/Discharge Efficiency (%)": efficiency
        })
    return pd.DataFrame(summary_list)

# --- Display NMC Cells Section ---
st.header("🔵 NMC Cells")
nmc_cells = sorted(df[df["Cell_Type"] == "NMC"]["Cell_ID"].unique())

# Pie chart for capacity distribution among NMC cells
nmc_latest = df[df["Cell_Type"] == "NMC"].sort_values("Time").groupby("Cell_ID").tail(1)
fig_nmc_pie = px.pie(nmc_latest, names="Cell_ID", values="Capacity", title="NMC Cells Capacity Distribution",
                     color_discrete_sequence=px.colors.qualitative.Bold)
st.plotly_chart(fig_nmc_pie, use_container_width=True)

# Individual charts for each NMC cell
for cell in nmc_cells:
    cell_df = df[(df["Cell_ID"] == cell) & (df["Cell_Type"] == "NMC")]
    plot_cell_charts(cell_df, cell)

# Charging/discharging summary table for NMC
st.subheader("⚡ Charging/Discharging Summary for NMC Cells")
nmc_summary = charging_discharging_summary(df[df["Cell_Type"] == "NMC"])
st.dataframe(nmc_summary)

st.markdown("---")

# --- Display LFP Cells Section ---
st.header("🟠 LFP Cells")
lfp_cells = sorted(df[df["Cell_Type"] == "LFP"]["Cell_ID"].unique())

# Pie chart for capacity distribution among LFP cells
lfp_latest = df[df["Cell_Type"] == "LFP"].sort_values("Time").groupby("Cell_ID").tail(1)
fig_lfp_pie = px.pie(lfp_latest, names="Cell_ID", values="Capacity", title="LFP Cells Capacity Distribution",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
st.plotly_chart(fig_lfp_pie, use_container_width=True)

# Individual charts for each LFP cell
for cell in lfp_cells:
    cell_df = df[(df["Cell_ID"] == cell) & (df["Cell_Type"] == "LFP")]
    plot_cell_charts(cell_df, cell)

# Charging/discharging summary table for LFP
st.subheader("⚡ Charging/Discharging Summary for LFP Cells")
lfp_summary = charging_discharging_summary(df[df["Cell_Type"] == "LFP"])
st.dataframe(lfp_summary)

st.markdown("---")

# --- Optional: Raw Data ---
with st.expander("📄 View Full Raw Data Table"):
    st.dataframe(df, use_container_width=True)
