import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Login App", page_icon="🔐")

# Connect to Supabase using the secrets file
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Initialize session state for logged-in user
if "user" not in st.session_state:
    st.session_state.user = None

# ---------- LOGGED IN VIEW ----------
if st.session_state.user:
    st.title("🏠 Welcome!")
    st.success(f"Logged in as: **{st.session_state.user.email}**")
    st.write("This is your secure dashboard.")
    
    if st.button("Log out"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
    st.stop()

# ---------- LOGGED OUT VIEW ----------
st.title("🔐 My App")

tab1, tab2 = st.tabs(["Login", "Sign Up"])

# --- LOGIN TAB ---
with tab1:
    st.subheader("Welcome back")
    with st.form("login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Log in", use_container_width=True)
        
    if submitted:
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = response.user
            st.rerun()
        except Exception as e:
            # If the error mentions email confirmation, we show a helpful message
            if "Email not confirmed" in str(e):
                st.error("Please check your email inbox and confirm your account first!")
            else:
                st.error("Login failed. Check your email and password.")

# --- SIGN UP TAB ---
with tab2:
    st.subheader("Create an account")
    with st.form("signup_form"):
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_password")
        submitted_signup = st.form_submit_button("Sign up", use_container_width=True)
        
    if submitted_signup:
        if len(new_password) < 6:
            st.warning("Password must be at least 6 characters.")
        else:
            try:
                response = supabase.auth.sign_up({"email": new_email, "password": new_password})
                st.success("Account created! You can now log in.")
                st.info("💡 Note: If you get a login error later, check your email to confirm your account.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")