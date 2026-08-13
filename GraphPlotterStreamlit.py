import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
import math
import uuid
import xlsxwriter.utility as xl_util

def evaluate_expression(expr_str, df, base_x_col, base_y_col):
    """Safely evaluates an expression which can be a column name, a constant, or an equation like '0.1 * x'"""
    if not expr_str or not str(expr_str).strip() or str(expr_str).strip().lower() == 'none':
        return None
        
    expr_str = str(expr_str).strip()
    
    # 1. Is it a direct column name?
    if expr_str in df.columns:
        return df[expr_str].values
        
    # 2. Try parsing as a constant
    try:
        val = float(expr_str)
        return np.full(len(df), val)
    except ValueError:
        pass
        
    # 3. Evaluate as mathematical equation
    try:
        x = df[base_x_col].values if base_x_col in df.columns else None
        y = df[base_y_col].values if base_y_col in df.columns else None
        
        # Replace typical string patterns
        s = expr_str.replace('^', '**')
        
        result = eval(s, {"np": np, "math": math, "x": x, "y": y, "__builtins__": None})
        if isinstance(result, (int, float)):
            return np.full(len(df), result)
        return result
    except Exception as e:
        # We don't error out hard here so it doesn't break the app as they type
        return None

def validate_expression(expr_str, df=None):
    if not expr_str or not str(expr_str).strip() or str(expr_str).strip().lower() == 'none':
        return True
    expr_str = str(expr_str).strip()
    if df is not None and expr_str in df.columns:
        return True
    try:
        float(expr_str)
        return True
    except ValueError:
        pass
    try:
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([1.0, 2.0, 3.0])
        s = expr_str.replace('^', '**')
        eval(s, {"np": np, "math": math, "x": x, "y": y, "__builtins__": None})
        return True
    except Exception:
        return False

def validated_text_input(label, value, key, df=None, help_text=None):
    val = st.text_input(label, value=value, key=key, help=help_text)
    if not validate_expression(val, df):
        st.markdown("<div style='color:#d9534f; font-size: 0.85em; margin-top:-10px; margin-bottom:10px; font-weight: 500;'>⚠️ Invalid input or unknown column</div>", unsafe_allow_html=True)
    return val

def render_graph_plotter():
    st.header("Graphs Plotter")
    
    DEFAULT_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # 1. File Uploader
    uploaded_files = st.file_uploader("Upload Excel/CSV files", type=["xlsx", "csv"], accept_multiple_files=True)
    
    if 'datasets' not in st.session_state:
        st.session_state.datasets = {}
    if 'deleted_files' not in st.session_state:
        st.session_state.deleted_files = set()
        
    # Keep track of current files to remove deleted ones (only applies to file-type datasets)
    current_filenames = [f.name for f in uploaded_files] if uploaded_files else []
    
    # Clean up deleted_files so they can be re-uploaded later if user removes them from uploader
    st.session_state.deleted_files = {f for f in st.session_state.deleted_files if f in current_filenames}
    
    keys_to_remove = []
    for k, v in st.session_state.datasets.items():
        if v.get('type', 'file') == 'file' and k not in current_filenames:
            keys_to_remove.append(k)
    for k in keys_to_remove:
        del st.session_state.datasets[k]
        
    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in st.session_state.datasets and uploaded_file.name not in st.session_state.deleted_files:
                try:
                    if uploaded_file.name.endswith('.xlsx'):
                        df = pd.read_excel(uploaded_file)
                    else:
                        df = pd.read_csv(uploaded_file, sep=None, engine='python')
                    
                    color_idx = len(st.session_state.datasets) % len(DEFAULT_COLORS)
                    st.session_state.datasets[uploaded_file.name] = {
                        'type': 'file',
                        'df': df,
                        'x_col': df.columns[0] if len(df.columns) > 0 else None,
                        'y_col': df.columns[1] if len(df.columns) > 1 else None,
                        'err_x': 'None',
                        'err_y': 'None',
                        'color': DEFAULT_COLORS[color_idx],
                        'show': True,
                        'label': uploaded_file.name,
                        'smooth_level': 0
                    }
                except Exception as e:
                    st.error(f"Error reading {uploaded_file.name}: {e}")

    # 2. Controls and Settings
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### Settings")
        graph_title = st.text_input("Graph Title", value="Data Visualization")
        x_label = st.text_input("X Axis Label", value="X Axis")
        y_label = st.text_input("Y Axis Label", value="Y Axis")
        
        log_x = st.checkbox("Logarithmic X-Axis")
        log_y = st.checkbox("Logarithmic Y-Axis")
        
        st.markdown("### Datasets")
        
        # Subtle button for adding function
        if st.button("➕ Add Custom Function", type="secondary"):
            func_id = f"Custom_Func_{str(uuid.uuid4())[:8]}"
            color_idx = len(st.session_state.datasets) % len(DEFAULT_COLORS)
            func_num = sum(1 for v in st.session_state.datasets.values() if v.get('type') == 'function') + 1
            st.session_state.datasets[func_id] = {
                'type': 'function',
                'func_str': 'np.sin(x)',
                'err_x': 'None',
                'err_y': 'None',
                'color': DEFAULT_COLORS[color_idx],
                'show': True,
                'label': f"Function {func_num}",
                'smooth_level': 0
            }
            st.rerun()

        # Render expanders
        for d_key, data in list(st.session_state.datasets.items()):
            is_func = data.get('type', 'file') == 'function'
            
            # Styling differently based on type
            expander_title = f"✨ {data['label']}" if is_func else f"📁 {d_key}"
            
            with st.expander(expander_title):
                data['show'] = st.checkbox("Show on graph", value=data['show'], key=f"show_{d_key}")
                data['label'] = st.text_input("Legend Label", value=data['label'], key=f"label_{d_key}")
                
                if is_func:
                    data['func_str'] = validated_text_input("Function f(x)", value=data.get('func_str', ''), key=f"func_{d_key}")
                    
                else:
                    columns = data['df'].columns.tolist()
                    data['x_col'] = st.selectbox("X Axis", columns, index=columns.index(data['x_col']) if data['x_col'] in columns else 0, key=f"x_{d_key}")
                    data['y_col'] = st.selectbox("Y Axis", columns, index=columns.index(data['y_col']) if data['y_col'] in columns else 0, key=f"y_{d_key}")
                    
                data['smooth_level'] = st.number_input("Smooth level", min_value=0, max_value=100, step=1, value=data.get('smooth_level', 0), key=f"smooth_{d_key}")
                
                col_e1, col_e2 = st.columns(2)
                with col_e1: data['err_y'] = validated_text_input("Y Error", value=data.get('err_y', 'None'), key=f"err_y_{d_key}", df=data.get('df'), help_text="E.g. Column name, 5.2, or 0.1 * y")
                with col_e2: data['err_x'] = validated_text_input("X Error", value=data.get('err_x', 'None'), key=f"err_x_{d_key}", df=data.get('df'), help_text="E.g. Column name, 2.1, or 0.1 * x")
                
                data['color'] = st.color_picker("Color", value=data['color'], key=f"color_{d_key}")
                
                if st.button("🗑️ Remove Dataset", key=f"del_{d_key}"):
                    if not is_func:
                        st.session_state.deleted_files.add(d_key)
                    del st.session_state.datasets[d_key]
                    st.rerun()

    # 3. Data Processing & Plotting
    with col2:
        st.markdown("### Graph")
        fig = go.Figure()
        
        has_plots = False
        master_x_col = None
        combined_df = None
        
        # Phase 1: Build combined DataFrame from File datasets FIRST
        for d_key, data in st.session_state.datasets.items():
            if data['show'] and data.get('type', 'file') == 'file':
                df = data['df']
                x_col, y_col = data['x_col'], data['y_col']
                
                if x_col in df.columns and y_col in df.columns:
                    temp_df = df[[x_col, y_col]].dropna().copy()
                    
                    # Compute Errors
                    err_y_vals = evaluate_expression(data.get('err_y'), df, x_col, y_col)
                    err_x_vals = evaluate_expression(data.get('err_x'), df, x_col, y_col)
                    
                    if err_y_vals is not None: temp_df['__err_y'] = err_y_vals
                    if err_x_vals is not None: temp_df['__err_x'] = err_x_vals
                    
                    # Smooth
                    smooth_level = data.get('smooth_level', 0)
                    if smooth_level > 0:
                        window_size = int(smooth_level * 2 + 1)
                        temp_df[y_col] = temp_df[y_col].rolling(window=window_size, center=True).mean().bfill().ffill()
                        
                    y_name = f"{data['label']} ({d_key})" if data['label'] == 'Y Axis' else data['label']
                    rename_dict = {y_col: y_name}
                    if '__err_y' in temp_df.columns: rename_dict['__err_y'] = f"{y_name} (Error Y)"
                    if '__err_x' in temp_df.columns: rename_dict['__err_x'] = f"{y_name} (Error X)"
                        
                    temp_df = temp_df.rename(columns=rename_dict)
                    
                    if combined_df is None:
                        master_x_col = x_col
                        combined_df = temp_df
                    else:
                        temp_df = temp_df.rename(columns={x_col: master_x_col})
                        combined_df = pd.merge(combined_df, temp_df, on=master_x_col, how='outer')
                    
                    has_plots = True

        # Phase 2: Create a domain for custom functions
        if combined_df is not None:
            combined_df = combined_df.sort_values(by=master_x_col).reset_index(drop=True)
            domain_x = combined_df[master_x_col].values
        else:
            # If no files are uploaded but we have custom functions
            master_x_col = "X Axis"
            domain_x = np.linspace(0, 100, 1000)
            combined_df = pd.DataFrame({master_x_col: domain_x})
            
        # Phase 3: Evaluate Custom Function datasets
        for d_key, data in st.session_state.datasets.items():
            if data['show'] and data.get('type') == 'function':
                func_str = data.get('func_str')
                if func_str and func_str.strip():
                    try:
                        s = func_str.replace('^', '**')
                        y_custom = eval(s, {"np": np, "math": math, "x": domain_x, "__builtins__": None})
                        if isinstance(y_custom, (int, float)):
                            y_custom = np.full(len(domain_x), y_custom)
                            
                        y_name = data['label']
                        combined_df[y_name] = y_custom
                        
                        # Errors for custom function
                        err_y_vals = evaluate_expression(data.get('err_y'), combined_df, master_x_col, y_name)
                        err_x_vals = evaluate_expression(data.get('err_x'), combined_df, master_x_col, y_name)
                        if err_y_vals is not None: combined_df[f"{y_name} (Error Y)"] = err_y_vals
                        if err_x_vals is not None: combined_df[f"{y_name} (Error X)"] = err_x_vals
                        
                        has_plots = True
                    except Exception as e:
                        st.error(f"Failed to evaluate custom function '{func_str}': {e}")
        
        if has_plots:
            # Phase 4: Plotly Rendering
            for d_key, data in st.session_state.datasets.items():
                if data['show']:
                    is_func = data.get('type') == 'function'
                    y_name = data['label'] if is_func else (f"{data['label']} ({d_key})" if data['label'] == 'Y Axis' else data['label'])
                    
                    if y_name in combined_df.columns:
                        plot_df = combined_df[[master_x_col, y_name]].dropna()
                        
                        trace_params = dict(
                            x=plot_df[master_x_col], 
                            y=plot_df[y_name],
                            mode='lines',
                            name=data['label'],
                            line=dict(color=data['color'])
                        )
                        
                        # Add Error bars if present
                        err_x_name = f"{y_name} (Error X)"
                        err_y_name = f"{y_name} (Error Y)"
                        
                        cols_to_drop = [master_x_col, y_name]
                        if err_x_name in combined_df.columns: cols_to_drop.append(err_x_name)
                        if err_y_name in combined_df.columns: cols_to_drop.append(err_y_name)
                        
                        err_df = combined_df[cols_to_drop].dropna()
                        
                        if not err_df.empty:
                            trace_params['x'] = err_df[master_x_col]
                            trace_params['y'] = err_df[y_name]
                            
                            if err_x_name in combined_df.columns:
                                trace_params['error_x'] = dict(type='data', array=err_df[err_x_name], visible=True)
                            if err_y_name in combined_df.columns:
                                trace_params['error_y'] = dict(type='data', array=err_df[err_y_name], visible=True)
                                
                        fig.add_trace(go.Scatter(**trace_params))
                        
            fig.update_layout(
                title=graph_title,
                xaxis_title=x_label,
                yaxis_title=y_label,
                xaxis_type="log" if log_x else "linear",
                yaxis_type="log" if log_y else "linear",
                hovermode="x unified",
                template="plotly_white",
                margin=dict(l=20, r=20, t=50, b=20)
            )
                
            st.plotly_chart(fig, use_container_width=True)
            
            # Phase 5: Combined Data Preview and Export
            st.markdown("### Combined Data Preview")
            st.dataframe(combined_df.head(50), use_container_width=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                combined_df.to_excel(writer, index=False, sheet_name='Combined Data')
                
                workbook  = writer.book
                worksheet = writer.sheets['Combined Data']
                
                chart = workbook.add_chart({'type': 'scatter', 'subtype': 'straight'})
                chart.show_blanks_as('span')
                
                max_row = len(combined_df)
                col_names = combined_df.columns
                
                # Exclude error columns from regular series
                exclude_cols = [c for c in col_names if c.endswith(" (Error X)") or c.endswith(" (Error Y)")]
                
                for i in range(1, len(col_names)):
                    col_name = col_names[i]
                    if col_name in exclude_cols:
                        continue
                        
                    # Find matching color
                    series_color = '#1f77b4'
                    for fn, dt in st.session_state.datasets.items():
                        if dt['show']:
                            y_match = dt['label'] if dt.get('type') == 'function' else (f"{dt['label']} ({fn})" if dt['label'] == 'Y Axis' else dt['label'])
                            if y_match == col_name:
                                series_color = dt['color']
                                break
                                
                    series_dict = {
                        'name':       ['Combined Data', 0, i],
                        'categories': ['Combined Data', 1, 0, max_row, 0],
                        'values':     ['Combined Data', 1, i, max_row, i],
                        'line':       {'color': series_color, 'width': 2.25},
                    }
                    
                    # Add Excel Error Bars
                    err_y_name = f"{col_name} (Error Y)"
                    if err_y_name in col_names:
                        err_idx = col_names.tolist().index(err_y_name)
                        range_str = f"='Combined Data'!{xl_util.xl_range_abs(1, err_idx, max_row, err_idx)}"
                        series_dict['y_error_bars'] = {
                            'type': 'custom',
                            'plus_values': range_str,
                            'minus_values': range_str,
                            'line': {'color': series_color},
                        }
                        
                    err_x_name = f"{col_name} (Error X)"
                    if err_x_name in col_names:
                        err_idx = col_names.tolist().index(err_x_name)
                        range_str = f"='Combined Data'!{xl_util.xl_range_abs(1, err_idx, max_row, err_idx)}"
                        series_dict['x_error_bars'] = {
                            'type': 'custom',
                            'plus_values': range_str,
                            'minus_values': range_str,
                            'line': {'color': series_color},
                        }
                        
                    chart.add_series(series_dict)
                    
                chart.set_title ({'name': graph_title})
                
                x_axis_settings = {'name': x_label}
                if log_x: x_axis_settings['log_base'] = 10
                chart.set_x_axis(x_axis_settings)
                
                y_axis_settings = {'name': y_label}
                if log_y: y_axis_settings['log_base'] = 10
                chart.set_y_axis(y_axis_settings)
                
                chart.set_size({'width': 720, 'height': 480})
                worksheet.insert_chart('E2', chart)
                
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Download Combined Excel",
                data=excel_data,
                file_name='combined_graphs_data.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="primary"
            )
        else:
            if not uploaded_files:
                st.info("Please upload files or add a custom function to start plotting.")
