import streamlit as st
from GraphPlotterStreamlit import render_graph_plotter
from SignalAnalysisStreamlit import render_signal_analysis

# --- Page Config ---
st.set_page_config(
    page_title="Unified Scientific Workbench",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    /* Styling to give a premium feel */
    .stApp {
        background-color: #f8f9fa;
    }
    .main-header {
        color: #2c3e50;
        font-weight: 700;
        text-align: center;
        padding-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #e9ecef;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        font-weight: 600;
    }
    
    /* Hide the vanishing anchor link icons next to text headers */
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
        display: none !important;
    }
    
    /* Reduce large top spacing */
    .block-container {
        padding-top: 1.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">Unified Scientific Workbench</h1>', unsafe_allow_html=True)

# --- Tabs ---
tab1, tab2 = st.tabs(["📊 Graphs Plotter", "🔍 Extrema Finder"])

with tab1:
    render_graph_plotter()

with tab2:
    render_signal_analysis()
