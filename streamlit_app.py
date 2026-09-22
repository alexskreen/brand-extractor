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
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            st.subheader("Logo")
            if result['logo']:
                st.image(result['logo'], width=150)
                st.caption("Downloaded ✓")
            elif result['logo_url']:
                st.info(f"URL: {result['logo_url']}")
            else:
                st.warning("No logo found")

        with col2:
            st.subheader("Colors")
            if result['background_colors']:
                st.write("**Background:**")
                for color in result['background_colors']:
                    col_a, col_b = st.columns([0.3, 0.7])
                    with col_a:
                        st.color_picker("bg", value=color, disabled=True, label_visibility="collapsed")
                    with col_b:
                        st.caption(color)

            if result['primary_font_color']:
                st.write("**Primary Font:**")
                col_a, col_b = st.columns([0.3, 0.7])
                with col_a:
                    st.color_picker("primary", value=result['primary_font_color'], disabled=True, label_visibility="collapsed")
                with col_b:
                    st.caption(result['primary_font_color'])

            if result['secondary_font_color']:
                st.write("**Secondary Font:**")
                col_a, col_b = st.columns([0.3, 0.7])
                with col_a:
                    st.color_picker("secondary", value=result['secondary_font_color'], disabled=True, label_visibility="collapsed")
                with col_b:
                    st.caption(result['secondary_font_color'])

        with col3:
            st.subheader("Button")
            if result['button_color']:
                st.write("**Color:**")
                col_a, col_b = st.columns([0.3, 0.7])
                with col_a:
                    st.color_picker("button", value=result['button_color'], disabled=True, label_visibility="collapsed")
                with col_b:
                    st.caption(result['button_color'])
            else:
                st.write("No button found")

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
