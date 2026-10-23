import streamlit as st
from supabase import create_client, Client
import uuid

st.set_page_config(page_title="Music App", page_icon="🎵", layout="centered")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

if "user" not in st.session_state:
    st.session_state.user = None

# ---------- LOGGED IN VIEW ----------
if st.session_state.user:
    user_id = st.session_state.user.id
    
    # Get username
    profile = supabase.table("profiles").select("username").eq("id", user_id).execute()
    username = profile.data[0]["username"] if profile.data else "Music Lover"

    st.title("🎵 Your Music Dashboard")
    st.write(f"Logged in as: **{username}**")
    
    if st.button("Log out"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    st.divider()

    # --- UPLOAD SECTION ---
    st.subheader("Upload a new song")
    with st.form("upload_form", clear_on_submit=True):
        title = st.text_input("Song Title")
        audio_file = st.file_uploader("Choose an audio file (MP3, WAV)", type=["mp3", "wav"])
        is_public = st.checkbox("Make this song public (others can see it)")
        submit_song = st.form_submit_button("Upload Song")
        
    if submit_song:
        if not title or not audio_file:
            st.warning("Please provide a title and a file.")
        else:
            try:
                with st.spinner("Uploading..."):
                    # 1. Upload file to Supabase Storage (using a unique ID to avoid name clashes)
                    file_ext = audio_file.name.split(".")[-1]
                    file_path = f"{user_id}/{uuid.uuid4()}.{file_ext}"
                    
                    supabase.storage.from_("music").upload(file_path, audio_file.read())
                    
                    # 2. Save song details to database
                    supabase.table("songs").insert({
                        "user_id": user_id,
                        "title": title,
                        "file_path": file_path,
                        "is_public": is_public
                    }).execute()
                    
                    st.toast("🎉 Song uploaded successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Upload failed: {e}")

    st.divider()

    # --- PLAYLIST SECTION ---
    st.subheader("🎧 Discover & Listen")
    
    # Fetch songs (RLS automatically hides private songs from other users)
    songs = supabase.table("songs").select("*").order("created_at", desc=True).execute()
    
    if not songs.data:
        st.info("No songs uploaded yet. Be the first!")
    else:
        for song in songs.data:
            audio_url = supabase.storage.from_("music").get_public_url(song["file_path"])
            badge = "🌍 Public" if song["is_public"] else "🔒 Private"
            
            with st.container(border=True):
                st.write(f"**{song['title']}** ({badge})")
                st.audio(audio_url)
    
    st.stop()

# ---------- LOGGED OUT VIEW ----------
st.title("🎵 My Music App")
tab1, tab2 = st.tabs(["Login", "Sign Up"])

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
            # Check if username is taken
            existing_user = supabase.table("profiles").select("username").eq("username", new_username).execute()
            
            if len(existing_user.data) > 0:
                st.error("🚫 That username is already taken.")
            else:
                try:
                    # Create Auth user
                    response = supabase.auth.sign_up({"email": new_email, "password": new_password})
                    
                    # Save Username to profiles table
                    if response.user:
                        supabase.table("profiles").insert({
                            "id": response.user.id, 
                            "username": new_username
                        }).execute()
                        
                    st.success("Account created! You can now log in.")
                except Exception as e:
                    st.error(f"Sign up failed: {e}")