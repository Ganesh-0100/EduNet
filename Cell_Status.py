df_hist = pd.DataFrame(st.session_state['history'][key])
fig_power = px.line(
            df_hist, x='time', y='power', color='task', markers=True,
            title=f"{key} - Time vs Power (Live)",
            labels={"time": "Elapsed Time (s)", "power": "Power (W)", "task": "Task"},
            color_discrete_sequence=px.colors.qualitative.Pastel
            )
power_figs_placeholders[key].plotly_chart(fig_power, use_container_width=True)

            # Optional delay for UI responsiveness
time.sleep(0.1)

    # --- Summary Section ---
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

    # Pie and bar charts
col1, col2 = st.columns(2)
with col1:
            type_counts = pd.Series(df_display2["Cell Type"]).value_counts()
            fig = px.pie(values=type_counts.values, names=type_counts.index,
            title="Cell Type Distribution", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
with col2:
            fig2 = px.bar(df_display2, x=df_display2.index, y="Voltage", color="Cell Type",
            title="Voltage Across Cells", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown("---")
            st.header("Temperature Comparison")
            fig3 = px.bar(df_display2, x=df_display2.index, y="Temperature (°C)", color="Cell Type",
                          title="Temperature Across Cells", color_discrete_sequence=px.colors.qualitative.Pastel)
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

    # --- CSV Reading Table + Download ---
st.markdown("---")
st.header("📋 Logged Readings Table & CSV Export")

if os.path.exists("cell_readings.csv"):
            df_log = pd.read_csv("cell_readings.csv")
            st.dataframe(df_log.tail(100), height=300)  # Show last 100 readings
            csv = df_log.to_csv(index=False).encode('utf-8')
            st.download_button(
                        label="📥 Download Full CSV Log",
                        data=csv,
                        file_name="cell_readings.csv",
                        mime='text/csv'
            )
else:
            st.info("No readings recorded yet. Run a test to start logging.")
