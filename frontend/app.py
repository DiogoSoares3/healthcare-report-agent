import streamlit as st
import requests
import re
import os


API_INTERNAL_URL = os.getenv("API_INTERNAL_URL", "http://api:8220/api/v1/agent/report")
API_PUBLIC_BASE_URL = os.getenv("API_PUBLIC_BASE_URL", "http://localhost:8220")

st.set_page_config(layout="wide", page_title="SRAG Agent", page_icon="🏥")

st.markdown(
    """
<style>
    .report-box { border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px; background-color: #ffffff; }
    img { max-width: 100%; border-radius: 4px; border: 1px solid #ddd; margin-top: 10px; margin-bottom: 10px; }
</style>
""",
    unsafe_allow_html=True,
)


def fix_image_paths(markdown_text: str) -> str:
    return re.sub(
        r"\(/api/v1/plots/", f"({API_PUBLIC_BASE_URL}/api/v1/plots/", markdown_text
    )


st.title("🏥 SRAG Executive Reporting Agent")

with st.sidebar:
    st.header("Parameters")
    focus_area = st.text_input("Focus Area", placeholder="Ex: H1N1 Variant")
    st.info("Generating report via LLM Agent pipeline...")

if st.button("Generate Report", type="primary"):
    with st.spinner("Agent is working..."):
        try:
            payload = {"focus_area": focus_area if focus_area else None}
            response = requests.post(API_INTERNAL_URL, json=payload, timeout=120)

            if response.status_code == 200:
                data = response.json()
                raw_markdown = data.get("response", "")

                final_markdown = fix_image_paths(raw_markdown)

                st.success(f"Done in {data.get('execution_time'):.2f}s")
                st.markdown(final_markdown, unsafe_allow_html=True)

                with st.expander("Governance Artifacts (Plots)"):
                    st.json(data.get("plots"))
            else:
                st.error(f"API Error: {response.text}")

        except Exception as e:
            st.error(f"Connection Error: {e}")
            st.warning(f"Attempted to connect to internal URL: {API_INTERNAL_URL}")
