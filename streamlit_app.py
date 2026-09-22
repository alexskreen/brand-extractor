import streamlit as st
import json
from brand_extractor import extract_brand
from PIL import Image
import os

st.set_page_config(page_title="Brand Extractor", layout="wide")

st.title("Brand Extractor")
st.write("Paste a business URL to extract their logo, colors, and typography.")

col1, col2 = st.columns([3, 1])

with col1:
    url = st.text_input("Enter Website URL:", placeholder="https://example.com")

with col2:
    extract_button = st.button("Extract", use_container_width=True)

if extract_button:
    if not url:
        st.error("Please enter a URL")
    else:
        with st.spinner("Extracting brand information..."):
            result = extract_brand(url, output_dir="./brand_assets")

        # Display results
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Logo")
            if result['logo']:
                st.image(result['logo'], width=200)
                st.caption(f"Downloaded: {result['logo']}")
            elif result['logo_url']:
                st.info(f"Logo URL (couldn't download): {result['logo_url']}")
            else:
                st.warning("No logo found")

        with col2:
            st.subheader("Colors")
            if result['background_colors']:
                st.write("**Background Colors:**")
                for color in result['background_colors']:
                    st.color_picker("", value=color, disabled=True)

            if result['primary_font_color']:
                st.write("**Primary Font Color:**")
                st.color_picker("", value=result['primary_font_color'], disabled=True)

            if result['secondary_font_color']:
                st.write("**Secondary Font Color:**")
                st.color_picker("", value=result['secondary_font_color'], disabled=True)

            if result['button_color']:
                st.write("**Button Color:**")
                st.color_picker("", value=result['button_color'], disabled=True)

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            if result['background_image']:
                st.subheader("Background Image")
                st.image(result['background_image'])

        with col2:
            st.subheader("Raw Data")
            raw_data = {k: v for k, v in result.items() if k != 'errors'}
            st.json(raw_data)

        if result['errors']:
            with st.expander("⚠️ Warnings/Errors"):
                for error in result['errors']:
                    st.warning(error)

        st.success("✅ Extraction complete!")
