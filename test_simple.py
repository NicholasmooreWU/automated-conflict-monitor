import streamlit as st

st.set_page_config(page_title="Test", layout="wide")

st.title("✅ Simple Test App")
st.write("If you see this, Streamlit Cloud is working!")
st.success("App loaded successfully")

if st.button("Click me", key="click_me_btn_test"):
    st.balloons()
