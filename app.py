import streamlit as st
import pandas as pd
import json
import os
import re
from io import BytesIO
import base64

from scraper.scraper import scrape_website
from scraper.utils import load_profiles, load_fields, validate_url

# Page config
st.set_page_config(
    page_title="AD.IT.ASAP Web Scraper",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title
st.title("🔍 AD.IT.ASAP Web Scraper")
st.markdown("Extract business information and design elements from websites")

# Load configurations
profiles = load_profiles()
fields = load_fields()

# Sidebar for configuration
with st.sidebar:
    st.header("Scraper Configuration")
    
    # Profile selection
    selected_profile_key = st.selectbox(
        "Select Business Profile",
        options=list(profiles.keys()),
        format_func=lambda x: profiles[x]["profile_name"]
    )
    
    selected_profile = profiles[selected_profile_key]
    
    # If custom profile, allow field selection
    if selected_profile_key == "custom":
        st.subheader("Custom Fields")
        all_field_names = [field["field"] for field in fields]
        selected_fields = st.multiselect(
            "Select Fields to Extract",
            options=all_field_names,
            default=[]
        )
        selected_profile["fields"] = selected_fields
        selected_profile["mandatory_fields"] = []
    
    # Show fields that will be extracted
    st.subheader("Fields to Extract")
    for field in selected_profile["fields"]:
        if field in selected_profile["mandatory_fields"]:
            st.markdown(f"* **{field}** (mandatory)")
        else:
            st.markdown(f"* {field}")
    
    # Advanced options
    st.subheader("Advanced Options")
    extract_colors = st.checkbox("Extract color palette", value=True)
    extract_logo = st.checkbox("Extract logo", value=True)
    extract_fonts = st.checkbox("Identify fonts", value=True)

# Main content
st.header("Website to Scrape")

url = st.text_input("Enter website URL", placeholder="https://example.com")

col1, col2 = st.columns([1, 2])
with col1:
    start_scrape = st.button("Start Scraping", type="primary")

# Display scraping results
if start_scrape and url:
    # Validate URL
    if not validate_url(url):
        st.error("Please enter a valid URL (include http:// or https://)")
    else:
        with st.spinner("Scraping website... This may take a moment."):
            try:
                # Start scraping
                results, design_info = scrape_website(
                    url=url,
                    profile=selected_profile,
                    extract_colors=extract_colors,
                    extract_logo=extract_logo,
                    extract_fonts=extract_fonts
                )
                
                # Show results
                st.header("Scraping Results")
                
                # Basic info
                st.subheader("Business Information")
                
                # Create two columns for displaying info and design elements
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    # Display result table
                    if results:
                        # Convert to DataFrame for display
                        df = pd.DataFrame(list(results.items()), columns=["Field", "Value"])
                        st.dataframe(df, use_container_width=True)
                        
                        # Export options
                        st.subheader("Export Data")
                        export_format = st.radio("Export Format", options=["JSON", "CSV"], horizontal=True)
                        
                        if export_format == "JSON":
                            json_data = json.dumps(results, ensure_ascii=False, indent=2)
                            b64 = base64.b64encode(json_data.encode()).decode()
                            href = f'<a href="data:file/json;base64,{b64}" download="scraped_data.json">Download JSON</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        else: # CSV
                            csv = df.to_csv(index=False)
                            b64 = base64.b64encode(csv.encode()).decode()
                            href = f'<a href="data:file/csv;base64,{b64}" download="scraped_data.csv">Download CSV</a>'
                            st.markdown(href, unsafe_allow_html=True)
                    else:
                        st.warning("No data was extracted. Try another URL or different profile.")
                
                with col2:
                    # Display design elements
                    st.subheader("Design Elements")
                    
                    # Logo
                    if 'logo_url' in design_info and design_info['logo_url']:
                        st.markdown("### Logo")
                        st.markdown(f"![Logo]({design_info['logo_url']})")
                    
                    # Color palette
                    if 'colors' in design_info and design_info['colors']:
                        st.markdown("### Color Palette")
                        color_cols = st.columns(len(design_info['colors']))
                        for i, color in enumerate(design_info['colors']):
                            with color_cols[i]:
                                st.markdown(
                                    f'<div style="background-color: {color}; height: 50px; border-radius: 5px;"></div>',
                                    unsafe_allow_html=True
                                )
                                st.code(color)
                    
                    # Fonts
                    if 'fonts' in design_info and design_info['fonts']:
                        st.markdown("### Fonts")
                        for font in design_info['fonts']:
                            st.markdown(f"* {font}")
                
            except Exception as e:
                st.error(f"An error occurred during scraping: {str(e)}")
                st.error("Please check the URL and try again.")

# Add footer
st.markdown("---")
st.markdown("*AD.IT.ASAP – Automating business intelligence. For questions or feedback, we're here to help!*")
