import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
import scipy.signal

def render_signal_analysis():
    st.header("Signal Extrema Finder")
    
    # 1. File Upload
    uploaded_file = st.file_uploader("Upload Data File (Replaces current data)", type=["xlsx", "csv"], key="extrema_upload", accept_multiple_files=False)
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
                
            columns = df.columns.tolist()
            if len(columns) < 2:
                st.error("Data must have at least two columns.")
                return
                
        except Exception as e:
            st.error(f"Error reading file: {e}")
            return

        # Initialize or clear results table if file changes
        if 'extrema_file' not in st.session_state or st.session_state.extrema_file != uploaded_file.name:
            st.session_state.extrema_results = pd.DataFrame(columns=["Type", "X-Value", "Y-Value"])
            st.session_state.extrema_file = uploaded_file.name
            
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### Settings")
            x_col = st.selectbox("X Axis Column", columns, index=0, key="extrema_x")
            y_col = st.selectbox("Y Axis Column", columns, index=1 if len(columns)>1 else 0, key="extrema_y")
            
            if x_col == y_col:
                st.error("X and Y axes must be different columns.")
                return
            
            x_data = df[x_col].values
            y_data = df[y_col].values
            
            st.markdown("---")
            st.markdown("### Automated Detection")
            smooth_level = st.number_input("Smooth level", min_value=0, max_value=100, step=1, value=0)
            
            if smooth_level > 0:
                # Map 1-100 level to an odd window size (3 to 201)
                window_size = int(smooth_level * 2 + 1)
                # Use pandas rolling mean with center to avoid shifting peaks
                y_data_plot = pd.Series(y_data).rolling(window=window_size, center=True).mean().bfill().ffill().values
            else:
                y_data_plot = y_data
                
            if st.button("🔍 Detect possible points", use_container_width=True):
                # Find peaks and valleys using a 5% prominence threshold to avoid noise
                prom = (np.max(y_data_plot) - np.min(y_data_plot)) * 0.05
                peaks, _ = scipy.signal.find_peaks(y_data_plot, prominence=prom)
                valleys, _ = scipy.signal.find_peaks(-y_data_plot, prominence=prom)
                
                new_rows = []
                for idx in peaks:
                    new_rows.append({"Type": "Max", "X-Value": x_data[idx], "Y-Value": y_data[idx]})
                for idx in valleys:
                    new_rows.append({"Type": "Min", "X-Value": x_data[idx], "Y-Value": y_data[idx]})
                
                if new_rows:
                    st.session_state.extrema_results = pd.concat([st.session_state.extrema_results, pd.DataFrame(new_rows)], ignore_index=True)
                    st.session_state.extrema_results = st.session_state.extrema_results.drop_duplicates(subset=["Type", "X-Value"]).reset_index(drop=True)
                    st.rerun()
            
            st.markdown("---")
            st.markdown("### Selection Actions")
            # Placeholders for buttons on the left
            btn_max_placeholder = st.empty()
            btn_min_placeholder = st.empty()
            
            st.markdown("---")
            if st.button("🗑️ Clear All Results", use_container_width=True):
                st.session_state.extrema_results = pd.DataFrame(columns=["Type", "X-Value", "Y-Value"])
                st.rerun()
                
        # We process the chart first to get the selection
        with col2:
            st.markdown("### Signal Plot")
            fig = go.Figure()
            
            # Plot the main signal
            fig.add_trace(go.Scatter(
                x=x_data,
                y=y_data_plot,
                mode='lines',
                name="Signal",
                line=dict(color='#1f77b4')
            ))
            
            # Invisible scatter trace to force Plotly to enable the Box Select icon in the toolbar from the very beginning
            if len(x_data) > 0:
                fig.add_trace(go.Scatter(
                    x=[x_data[0]], 
                    y=[y_data[0]], 
                    mode='markers', 
                    marker=dict(color='rgba(0,0,0,0)'), 
                    showlegend=False, 
                    hoverinfo='skip'
                ))
            
            # Scatter plot for found extrema (so they persist on the graph)
            results_df = st.session_state.extrema_results
            if not results_df.empty:
                max_pts = results_df[results_df["Type"] == "Max"]
                min_pts = results_df[results_df["Type"] == "Min"]
                
                if not max_pts.empty:
                    fig.add_trace(go.Scatter(
                        x=max_pts["X-Value"],
                        y=max_pts["Y-Value"],
                        mode='markers',
                        name="Max Points",
                        marker=dict(color='red', size=12, symbol='circle')
                    ))
                if not min_pts.empty:
                    fig.add_trace(go.Scatter(
                        x=min_pts["X-Value"],
                        y=min_pts["Y-Value"],
                        mode='markers',
                        name="Min Points",
                        marker=dict(color='green', size=12, symbol='circle')
                    ))
            
            fig.update_layout(
                xaxis_title=x_col,
                yaxis_title=y_col,
                hovermode="x unified",
                template="plotly_white",
                margin=dict(l=20, r=20, t=20, b=20),
                dragmode="select" # Default to box selection mode
            )
            
            # Render chart with selection enabled
            selection_event = st.plotly_chart(
                fig, 
                on_select="rerun", 
                selection_mode="box", 
                use_container_width=True,
                config={'displayModeBar': True}
            )
            
            # Process Selection Bounding Box
            selected_x_range = None
            if selection_event and "selection" in selection_event:
                sel = selection_event["selection"]
                # Look for box coordinates (bypasses Plotly's line-point selection bug)
                if sel.get("box") and len(sel["box"]) > 0:
                    box_x = sel["box"][0].get("x", [])
                    if len(box_x) == 2:
                        selected_x_range = (min(box_x), max(box_x))
                        
            st.markdown("### Extrema Results Table")
            display_df = st.session_state.extrema_results.copy()
            display_df = display_df.rename(columns={"X-Value": x_col, "Y-Value": y_col})
            st.dataframe(display_df, use_container_width=True)
            
            if not display_df.empty:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    display_df.to_excel(writer, index=False, sheet_name='Extrema')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 Download Results as Excel",
                    data=excel_data,
                    file_name='extrema_results.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    type="primary"
                )

        # Now fill the buttons on the left based on selection
        with col1:
            if selected_x_range:
                if st.button("🗑️ Remove Selected Points", use_container_width=True, type="secondary"):
                    current_results = st.session_state.extrema_results
                    if not current_results.empty:
                        # Keep rows where X-Value is OUTSIDE the selected range
                        mask_keep = (current_results["X-Value"] < selected_x_range[0]) | (current_results["X-Value"] > selected_x_range[1])
                        st.session_state.extrema_results = current_results[mask_keep]
                        st.rerun()

                # Highlight the button to show it's active
                if btn_max_placeholder.button("🔴 Find Maximum in Selection", use_container_width=True, type="primary"):
                    mask = (x_data >= selected_x_range[0]) & (x_data <= selected_x_range[1])
                    if np.any(mask):
                        idx_max = np.argmax(y_data_plot[mask])
                        actual_idx = np.where(mask)[0][idx_max]
                        new_row = pd.DataFrame([{"Type": "Max", "X-Value": x_data[actual_idx], "Y-Value": y_data[actual_idx]}])
                        st.session_state.extrema_results = pd.concat([st.session_state.extrema_results, new_row], ignore_index=True)
                        st.rerun()
                        
                if btn_min_placeholder.button("🟢 Find Minimum in Selection", use_container_width=True, type="primary"):
                    mask = (x_data >= selected_x_range[0]) & (x_data <= selected_x_range[1])
                    if np.any(mask):
                        idx_min = np.argmin(y_data_plot[mask])
                        actual_idx = np.where(mask)[0][idx_min]
                        new_row = pd.DataFrame([{"Type": "Min", "X-Value": x_data[actual_idx], "Y-Value": y_data[actual_idx]}])
                        st.session_state.extrema_results = pd.concat([st.session_state.extrema_results, new_row], ignore_index=True)
                        st.rerun()
            else:
                btn_max_placeholder.button("🔴 Find Maximum in Selection", disabled=True, use_container_width=True)
                btn_min_placeholder.button("🟢 Find Minimum in Selection", disabled=True, use_container_width=True)

    else:
        st.info("Please upload a file to start analysis.")
