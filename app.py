import streamlit as st
from supabase import create_client, Client
import uuid

st.set_page_config(page_title="Music App", page_icon="🎵", layout="centered")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

# Initialize session states
if "user" not in st.session_state:
    st.session_state.user = None
if "viewing_user" not in st.session_state:
    st.session_state.viewing_user = None

# ---------- LOGGED IN VIEW ----------
if st.session_state.user:
    user_id = st.session_state.user.id
    
    # Get logged-in user's username
    profile = supabase.table("profiles").select("username").eq("id", user_id).execute()
    username = profile.data[0]["username"] if profile.data else "Music Lover"

    # ==========================================
    # PROFILE VIEW
    # ==========================================
    if st.session_state.viewing_user:
        target_user = st.session_state.viewing_user
        
        if st.button("⬅ Back to Dashboard"):
            st.session_state.viewing_user = None
            st.rerun()
            
        st.title(f"👤 {target_user}'s Profile")
        
        target_search = supabase.table("profiles").select("id").eq("username", target_user).execute()
        if target_search.data:
            target_id = target_search.data[0]["id"]
            songs = supabase.table("songs").select("*").eq("user_id", target_id).eq("is_public", True).order("created_at", desc=True).execute()
            
            if not songs.data:
                st.info("This user has no public songs.")
            else:
                for song in songs.data:
                    audio_url = supabase.storage.from_("music").get_public_url(song["file_path"])
                    with st.container(border=True):
                        st.write(f"**{song['title']}**")
                        st.audio(audio_url)
        else:
            st.error("User not found.")
            
        st.stop()

    # ==========================================
    # MAIN DASHBOARD
    # ==========================================
    st.title("🎵 Your Music Dashboard")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"Logged in as: **{username}**")
    with col2:
        if st.button("Log out", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.viewing_user = None
            st.rerun()

    # --- ACCOUNT SETTINGS ---
    with st.expander("⚙️ Account Settings"):
        st.warning("Deleting your account is permanent. All your uploaded songs and profile data will be lost forever.")
        confirm_delete = st.checkbox("Yes, I want to permanently delete my account")
        
        if st.button("Delete My Account", type="primary"):
            if confirm_delete:
                try:
                    with st.spinner("Deleting account and data..."):
                        supabase.rpc("delete_my_account").execute()
                        supabase.auth.sign_out()
                        st.session_state.user = None
                        st.session_state.viewing_user = None
                        st.success("Account successfully deleted.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete account: {e}")
            else:
                st.error("⚠️ Please check the confirmation box first.")

    st.divider()

    # --- UPLOAD SECTION ---
    st.subheader("Upload a new song")
    with st.form("upload_form", clear_on_submit=True):
        title = st.text_input("Song Title")
        audio_file = st.file_uploader("Choose an audio file", type=["mp3", "wav", "m4a", "ogg"])
        is_public = st.checkbox("Make this song public (others can see it)")
        submit_song = st.form_submit_button("Upload Song")
        
    if submit_song:
        if not title or not audio_file:
            st.warning("Please provide a title and a file.")
        else:
            try:
                with st.spinner("Uploading..."):
                    file_ext = audio_file.name.split(".")[-1]
                    file_path = f"{user_id}/{uuid.uuid4()}.{file_ext}"
                    supabase.storage.from_("music").upload(file_path, audio_file.read())
                    supabase.table("songs").insert({
                        "user_id": user_id,
                        "title": title,
                        "file_path": file_path,
                        "is_public": is_public
                    }).execute()
                st.success("🎉 Song uploaded successfully! Please refresh the page.")
            except Exception as e:
                st.error(f"❌ Upload failed: {e}")

    st.divider()

    # --- PLAYLIST & SEARCH SECTION ---
    st.subheader("🎧 Discover & Listen")
    
    all_profiles = supabase.table("profiles").select("id, username").execute()
    user_map = {p["id"]: p["username"] for p in all_profiles.data}
    search_query = st.text_input("🔍 Search for a user to see their public playlist")
    
    if search_query:
        user_search = supabase.table("profiles").select("id").eq("username", search_query).execute()
        if not user_search.data:
            st.warning("User not found.")
        else:
            searched_id = user_search.data[0]["id"]
            songs = supabase.table("songs").select("*").eq("user_id", searched_id).eq("is_public", True).order("created_at", desc=True).execute()
            if not songs.data:
                st.info(f"No public songs found for {search_query}.")
            else:
                st.write(f"Showing public playlist for **{search_query}**:")
                for song in songs.data:
                    audio_url = supabase.storage.from_("music").get_public_url(song["file_path"])
                    with st.container(border=True):
                        st.write(f"**{song['title']}**")
                        st.audio(audio_url)
    else:
        songs = supabase.table("songs").select("*").order("created_at", desc=True).execute()
        if not songs.data:
            st.info("No songs uploaded yet. Be the first!")
        else:
            for song in songs.data:
                audio_url = supabase.storage.from_("music").get_public_url(song["file_path"])
                badge = "🌍 Public" if song["is_public"] else "🔒 Private"
                uploader_name = user_map.get(song["user_id"], "Unknown User")
                
                with st.container(border=True):
                    st.write(f"**{song['title']}** ({badge})")
                    
                    if uploader_name != "Unknown User":
                        if st.button(f"👤 View {uploader_name}'s Profile", key=f"profile_{song['id']}"):
                            st.session_state.viewing_user = uploader_name
                            st.rerun()
                    else:
                        st.caption(f"👤 Uploaded by: {uploader_name}")
                        
                    st.audio(audio_url)
    
    st.stop()

# ---------- LOGGED OUT VIEW ----------
st.title("🎵 My Music App")
tab1, tab2, tab3 = st.tabs(["Login", "Sign Up", "Reset Password"])

# --- LOGIN TAB ---
with tab1:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", use_container_width=True)
        
    if submitted:
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = response.user
            st.rerun()
        except Exception:
            st.error("Login failed. Check your email and password.")

# --- SIGN UP TAB ---
with tab2:
    with st.form("signup_form"):
        new_username = st.text_input("Choose a Username")
        new_email = st.text_input("Email")
        new_password = st.text_input("Password", type="password")
        submitted_signup = st.form_submit_button("Sign up", use_container_width=True)
        
    if submitted_signup:
        if len(new_password) < 6:
            st.warning("Password must be at least 6 characters.")
        elif len(new_username) < 3:
            st.warning("Username must be at least 3 characters.")
        else:
            existing_user = supabase.table("profiles").select("username").eq("username", new_username).execute()
            if len(existing_user.data) > 0:
                st.error("🚫 That username is already taken.")
            else:
                try:
                    response = supabase.auth.sign_up({"email": new_email, "password": new_password})
                    if response.user:
                        supabase.table("profiles").insert({
                            "id": response.user.id, 
                            "username": new_username
                        }).execute()
                    st.success("Account created! You can now log in.")
                except Exception as e:
                    st.error(f"Sign up failed: {e}")

# --- RESET PASSWORD TAB ---
with tab3:
    st.subheader("Forgot your password?")
    st.write("Enter your email to receive a 6-digit reset code.")
    
    reset_email = st.text_input("Email", key="reset_email")
    if st.button("Send Reset Code"):
        if reset_email:
            try:
                supabase.auth.reset_password_for_email(reset_email)
                st.success("Code sent! Check your email.")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter your email.")

    st.divider()
    
    st.write("Already have a code?")
    with st.form("update_password_form"):
        otp_code = st.text_input("6-Digit Code")
        new_pw = st.text_input("New Password", type="password")
        update_btn = st.form_submit_button("Update Password")
        
    if update_btn:
        if len(new_pw) < 6:
            st.warning("Password must be at least 6 characters.")
        else:
            try:
                # Verify the OTP code
                supabase.auth.verify_otp({
                    "email": reset_email,
                    "token": otp_code,
                    "type": "recovery"
                })
                # Update the password
                supabase.auth.update_user({"password": new_pw})
                st.success("🎉 Password updated! You can now log in.")
            except Exception as e:
                st.error(f"Failed to update password. Check the code and try again. Error: {e}")