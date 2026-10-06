import streamlit as st
import requests
import base64
import urllib.parse


# =========================
# Configuration
# =========================

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Simple Social",
    layout="wide"
)


# =========================
# Session State
# =========================

if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None


# =========================streamlit run streamlit_app.py
# Helpers
# =========================

def get_headers():
    """Return authorization headers for authenticated requests."""
    if st.session_state.token:
        return {
            "Authorization": f"Bearer {st.session_state.token}"
        }

    return {}


def get_error(response):
    """Extract a useful error message from FastAPI."""
    try:
        data = response.json()
        return data.get("detail", f"Request failed ({response.status_code})")
    except Exception:
        return f"Request failed ({response.status_code})"


def logout():
    """Clear authentication state."""
    st.session_state.token = None
    st.session_state.user = None
    st.rerun()


# =========================
# Login / Signup
# =========================

def login_page():
    st.title("🚀 Welcome to Simple Social")

    email = st.text_input("Email:")
    password = st.text_input(
        "Password:",
        type="password"
    )

    if not email or not password:
        st.info("Enter your email and password above")
        return

    col1, col2 = st.columns(2)

    # -------------------------
    # Login
    # -------------------------

    with col1:
        if st.button(
            "Login",
            type="primary",
            use_container_width=True
        ):
            login_data = {
                "username": email,
                "password": password
            }

            try:
                response = requests.post(
                    f"{API_URL}/auth/jwt/login",
                    data=login_data,
                    timeout=10
                )

                if response.status_code == 200:
                    token_data = response.json()

                    st.session_state.token = token_data["access_token"]

                    # Get current user
                    user_response = requests.get(
                        f"{API_URL}/users/me",
                        headers=get_headers(),
                        timeout=10
                    )

                    if user_response.status_code == 200:
                        st.session_state.user = user_response.json()
                        st.rerun()

                    else:
                        st.session_state.token = None
                        st.error(
                            f"Failed to get user information: "
                            f"{get_error(user_response)}"
                        )

                else:
                    st.error(
                        f"Login failed: {get_error(response)}"
                    )

            except requests.RequestException as e:
                st.error(f"Cannot connect to backend: {e}")

    # -------------------------
    # Signup
    # -------------------------

    with col2:
        if st.button(
            "Sign Up",
            type="secondary",
            use_container_width=True
        ):

            signup_data = {
                "email": email,
                "password": password
            }

            try:
                response = requests.post(
                    f"{API_URL}/register/register",
                    json=signup_data,
                    timeout=10
                )

                if response.status_code == 201:
                    st.success(
                        "Account created successfully! "
                        "Click Login."
                    )

                else:
                    st.error(
                        f"Registration failed: "
                        f"{get_error(response)}"
                    )

            except requests.RequestException as e:
                st.error(f"Cannot connect to backend: {e}")


# =========================
# Upload
# =========================

def upload_page():
    st.title("📸 Share Something")

    uploaded_file = st.file_uploader(
        "Choose media",
        type=[
            "png",
            "jpg",
            "jpeg",
            "mp4",
            "avi",
            "mov",
            "mkv",
            "webm"
        ]
    )

    caption = st.text_area(
        "Caption:",
        placeholder="What's on your mind?"
    )

    if uploaded_file and st.button(
            "Share",
            type="primary"
    ):
        with st.spinner("Uploading..."):

            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type
                )
            }

            data = {
                "caption": caption
            }

            try:
                response = requests.post(
                    f"{API_URL}/upload",
                    files=files,
                    data=data,
                    headers=get_headers(),
                    timeout=300
                )

                # Successful response
                if response.status_code in (200, 201):

                    st.success("✅ Upload successful!")

                    # Optional: show backend response
                    try:
                        result = response.json()
                        st.write(result)
                    except Exception:
                        pass

                    st.rerun()

                # Authentication problem
                elif response.status_code == 401:

                    st.error(
                        "Your session has expired. Please login again."
                    )
                    logout()

                # Other backend error
                else:

                    st.error(
                        f"Upload failed ({response.status_code}): "
                        f"{get_error(response)}"
                    )

            except requests.Timeout:

                st.error(
                    "⏱️ Upload is taking too long. "
                    "The backend /upload endpoint did not respond."
                )

            except requests.ConnectionError:

                st.error(
                    "❌ Cannot connect to backend. "
                    "Make sure FastAPI is running on port 8000."
                )

            except requests.RequestException as e:

                st.error(
                    f"❌ Upload request failed: {e}"
                )


# =========================
# ImageKit Helpers
# =========================

def encode_text_for_overlay(text):
    """Encode text for ImageKit overlay."""
    if not text:
        return ""

    base64_text = base64.b64encode(
        text.encode("utf-8")
    ).decode("utf-8")

    return urllib.parse.quote(base64_text)


def create_transformed_url(
    original_url,
    transformation_params,
    caption=None
):
    """Create an ImageKit transformation URL."""

    if caption:
        encoded_caption = encode_text_for_overlay(caption)

        text_overlay = (
            f"l-text,"
            f"ie-{encoded_caption},"
            f"ly-N20,"
            f"lx-20,"
            f"fs-100,"
            f"co-white,"
            f"bg-000000A0,"
            f"l-end"
        )

        transformation_params = text_overlay

    if not transformation_params:
        return original_url

    parts = original_url.split("/")

    if len(parts) < 5:
        return original_url

    file_path = "/".join(parts[4:])
    base_url = "/".join(parts[:4])

    return (
        f"{base_url}/tr:{transformation_params}/{file_path}"
    )


# =========================
# Feed
# =========================

def feed_page():
    st.title("🏠 Feed")

    try:
        response = requests.get(
            f"{API_URL}/feed",
            headers=get_headers(),
            timeout=10
        )

        if response.status_code == 401:
            st.error("Your session has expired. Please login again.")
            logout()
            return

        if response.status_code != 200:
            st.error(
                f"Failed to load feed: "
                f"{get_error(response)}"
            )
            return

        posts = response.json().get("posts", [])

        if not posts:
            st.info(
                "No posts yet! "
                "Be the first to share something."
            )
            return

        # Center the feed and keep it separate from the page
        left, center, right = st.columns([1, 2, 1])

        with center:

            for post in posts:

                # =========================
                # Small Feed Card
                # =========================

                with st.container(border=True):

                    # -------------------------
                    # Post Header
                    # -------------------------

                    col1, col2 = st.columns([5, 1])

                    with col1:
                        st.markdown(
                            f"**{post['email']}**  \n"
                            f"_{post['created_at'][:10]}_"
                        )

                    # -------------------------
                    # Delete Post
                    # -------------------------

                    with col2:

                        if post.get("is_owner", False):

                            if st.button(
                                "🗑️",
                                key=f"delete_{post['id']}",
                                help="Delete post"
                            ):

                                try:
                                    delete_response = requests.delete(
                                        f"{API_URL}/posts/{post['id']}",
                                        headers=get_headers(),
                                        timeout=10
                                    )

                                    if delete_response.status_code == 200:
                                        st.success("Post deleted!")
                                        st.rerun()

                                    else:
                                        st.error(
                                            "Failed to delete post: "
                                            f"{get_error(delete_response)}"
                                        )

                                except requests.RequestException as e:
                                    st.error(
                                        f"Delete request failed: {e}"
                                    )

                    # -------------------------
                    # Caption
                    # -------------------------

                    caption = post.get("caption", "")

                    if caption:
                        st.markdown(caption)

                # =========================
                # Media - SEPARATE
                # =========================

                st.markdown("")

                if post["file_type"] == "image":

                    image_url = create_transformed_url(
                        post["url"],
                        ""
                    )

                    st.image(
                        image_url,
                        width=500
                    )

                else:

                    video_url = create_transformed_url(
                        post["url"],
                        "w-600,h-400,cm-pad_resize,bg-blurred"
                    )

                    st.video(
                        video_url,
                        width=500
                    )

                st.markdown("---")

    except requests.RequestException as e:
        st.error(f"Cannot connect to backend: {e}")


if st.session_state.user is None:

    login_page()

else:

    st.sidebar.title(
        f"👋 Hi {st.session_state.user['email']}!"
    )

    if st.sidebar.button("Logout"):
        logout()

    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigate:",
        [
            "🏠 Feed",
            "📸 Upload"
        ]
    )

    if page == "🏠 Feed":
        feed_page()

    elif page == "📸 Upload":
        upload_page()