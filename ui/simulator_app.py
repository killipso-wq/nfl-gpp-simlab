"""
NFL GPP Simulator App - Streamlit UI

This module provides the Streamlit interface for the Monte Carlo NFL simulation.
"""

import streamlit as st


def render_header():
    """Render the header section with methodology and reference links."""
    st.markdown("""
    ### NFL GPP Monte Carlo Simulator
    
    **Quick Reference:**
    - 📊 [Methodology PDF](docs/research/monte_carlo_football.pdf) - Monte Carlo simulation approach
    - 📋 [Master Reference](docs/master_reference.md) - Complete specifications and design
    """)
    st.divider()


def main():
    """Main simulator app entry point."""
    st.set_page_config(
        page_title="NFL GPP Simulator",
        page_icon="🏈",
        layout="wide"
    )
    
    # Render header with links
    render_header()
    
    st.write("## Monte Carlo Simulator")
    st.info("Simulator functionality will be implemented according to the Master Reference specifications.")
    
    # Placeholder for future simulator functionality
    st.write("### Upload Players CSV")
    uploaded_file = st.file_uploader(
        "Choose a CSV file", 
        type="csv",
        help="Upload your players.csv with PLAYER, POS, TEAM, OPP, FPTS columns"
    )
    
    if uploaded_file is not None:
        st.success("File uploaded! Simulation functionality to be implemented.")
    
    st.write("### Simulation Parameters")
    col1, col2 = st.columns(2)
    
    with col1:
        sims = st.number_input("Number of Simulations", min_value=1000, max_value=100000, value=10000)
    
    with col2:
        seed = st.number_input("Random Seed", min_value=1, value=42)
    
    if st.button("Run Simulation", disabled=True):
        st.info("Simulation engine to be implemented according to Master Reference.")


if __name__ == "__main__":
    main()