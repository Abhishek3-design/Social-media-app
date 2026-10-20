import streamlit as st
import requests
import base64
import urllib.parse


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Simple Social",
    page_icon="🚀",
    layout="wide"
)


# ============================================================
# SESSION STATE
# ============================================================

if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None


# ============================================================
# HELPERS
# ============================================================

def get_headers():
    if st.session_state.token:
        return {
            "Authorization": f"Bearer {st.session_state.token}"
        }

    return {}


def get_error(response):
    try:
        data = response.json()
        return data.get(
            "detail",
            f"Request failed ({response.status_code})"
        )
    except Exception:
        return f"Request failed ({response.status_code})"


def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.rerun()


# ============================================================
# LOGIN PAGE
# ============================================================

def login_page():

    st.title("🚀 Welcome to Simple Social")

    st.write(
        "Login to your account or create a new account."
    )

    st.divider()

    email = st.text_input(
        "Email",
        placeholder="Enter your email"
    )

    password = st.text_input(
        "Password",
        type="password",
        placeholder="Enter your password"
    )

    if not email or not password:
        st.info("Enter your email and password above.")
        return

    col1, col2 = st.columns(2)

    # ========================================================
    # LOGIN
    # ========================================================

    with col1:

        if st.button(
            "🔐 Login",
            type="primary",
            use_container_width=True
        ):

            try:

                response = requests.post(
                    f"{API_URL}/auth/jwt/login",
                    data={
                        "username": email,
                        "password": password
                    },
                    timeout=10
                )

                if response.status_code == 200:

                    token_data = response.json()

                    st.session_state.token = (
                        token_data["access_token"]
                    )

                    user_response = requests.get(
                        f"{API_URL}/users/me",
                        headers=get_headers(),
                        timeout=10
                    )

                    if user_response.status_code == 200:

                        st.session_state.user = (
                            user_response.json()
                        )

                        st.rerun()

                    else:

                        st.session_state.token = None

                        st.error(
                            "Failed to get user information: "
                            f"{get_error(user_response)}"
                        )

                else:

                    st.error(
                        f"Login failed: {get_error(response)}"
                    )

            except requests.ConnectionError:

                st.error(
                    "❌ Cannot connect to FastAPI."
                )

            except requests.Timeout:

                st.error(
                    "⏱️ Login request timed out."
                )

            except requests.RequestException as e:

                st.error(
                    f"Login request failed: {e}"
                )

    # ========================================================
    # SIGN UP
    # ========================================================

    with col2:

        if st.button(
            "📝 Sign Up",
            use_container_width=True
        ):

            try:

                response = requests.post(
                    f"{API_URL}/register/register",
                    json={
                        "email": email,
                        "password": password
                    },
                    timeout=10
                )

                if response.status_code in (200, 201):

                    st.success(
                        "✅ Account created successfully!"
                    )

                    st.info(
                        "You can now click Login."
                    )

                else:

                    st.error(
                        f"Registration failed: "
                        f"{get_error(response)}"
                    )

            except requests.RequestException as e:

                st.error(
                    f"Registration request failed: {e}"
                )


# ============================================================
# UPLOAD PAGE
# ============================================================

def upload_page():

    st.title("📸 Share Something")

    st.write(
        "Upload an image or video and add a caption."
    )

    st.divider()

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
        "Caption",
        placeholder="What's on your mind?",
        height=100
    )

    if uploaded_file:

        st.write(
            f"Selected file: **{uploaded_file.name}**"
        )

        if st.button(
            "🚀 Share",
            type="primary",
            use_container_width=True
        ):

            with st.spinner("Uploading your post..."):

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

                    if response.status_code in (200, 201):

                        st.success(
                            "✅ Upload successful!"
                        )

                        st.rerun()

                    elif response.status_code == 401:

                        st.error(
                            "Your session has expired."
                        )

                        logout()

                    else:

                        st.error(
                            f"Upload failed: "
                            f"{get_error(response)}"
                        )

                except requests.Timeout:

                    st.error(
                        "⏱️ Upload took too long."
                    )

                except requests.ConnectionError:

                    st.error(
                        "❌ Cannot connect to backend."
                    )

                except requests.RequestException as e:

                    st.error(
                        f"Upload request failed: {e}"
                    )


# ============================================================
# IMAGEKIT HELPERS
# ============================================================

def encode_text_for_overlay(text):

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

    if caption:

        encoded_caption = (
            encode_text_for_overlay(caption)
        )

        transformation_params = (
            f"l-text,"
            f"ie-{encoded_caption},"
            f"ly-N20,"
            f"lx-20,"
            f"fs-100,"
            f"co-white,"
            f"bg-000000A0,"
            f"l-end"
        )

    if not transformation_params:
        return original_url

    parts = original_url.split("/")

    if len(parts) < 5:
        return original_url

    file_path = "/".join(parts[4:])
    base_url = "/".join(parts[:4])

    return (
        f"{base_url}/tr:"
        f"{transformation_params}/"
        f"{file_path}"
    )


# ============================================================
# DELETE POST
# ============================================================

def delete_post(post_id):

    try:

        response = requests.delete(
            f"{API_URL}/posts/{post_id}",
            headers=get_headers(),
            timeout=10
        )

        if response.status_code in (200, 204):

            st.success(
                "✅ Post deleted successfully!"
            )

            st.rerun()

        elif response.status_code == 401:

            st.error(
                "Your session has expired."
            )

            logout()

        else:

            st.error(
                f"Failed to delete post: "
                f"{get_error(response)}"
            )

    except requests.RequestException as e:

        st.error(
            f"Delete request failed: {e}"
        )


# ============================================================
# LIKE / UNLIKE
# ============================================================

def toggle_like(post_id, liked):

    try:

        if liked:

            response = requests.delete(
                f"{API_URL}/posts/{post_id}/like",
                headers=get_headers(),
                timeout=10
            )

        else:

            response = requests.post(
                f"{API_URL}/posts/{post_id}/like",
                headers=get_headers(),
                timeout=10
            )

        if response.status_code in (200, 201, 204):

            st.rerun()

        elif response.status_code == 401:

            st.error(
                "Your session has expired."
            )

            logout()

        else:

            st.error(
                f"Like failed: {get_error(response)}"
            )

    except requests.RequestException as e:

        st.error(
            f"Like request failed: {e}"
        )


# ============================================================
# DELETE COMMENT
# ============================================================

def delete_comment(comment_id):

    try:

        response = requests.delete(
            f"{API_URL}/comments/{comment_id}",
            headers=get_headers(),
            timeout=10
        )

        if response.status_code in (200, 204):

            st.success(
                "✅ Comment deleted!"
            )

            st.rerun()

        elif response.status_code == 401:

            st.error(
                "Your session has expired."
            )

            logout()

        elif response.status_code == 403:

            st.error(
                "You can only delete your own comment."
            )

        elif response.status_code == 404:

            st.error(
                "Comment not found."
            )

        else:

            st.error(
                f"Failed to delete comment: "
                f"{get_error(response)}"
            )

    except requests.RequestException as e:

        st.error(
            f"Delete comment request failed: {e}"
        )


# ============================================================
# ADD COMMENT
# ============================================================

def add_comment(post_id, comment_text):

    if not comment_text.strip():

        st.warning(
            "Comment cannot be empty."
        )

        return

    try:

        response = requests.post(
            f"{API_URL}/posts/{post_id}/comments",
            json={
                "content": comment_text.strip()
            },
            headers=get_headers(),
            timeout=10
        )

        if response.status_code in (200, 201):

            st.success(
                "✅ Comment posted!"
            )

            st.rerun()

        elif response.status_code == 401:

            st.error(
                "Your session has expired."
            )

            logout()

        else:

            st.error(
                f"Failed to post comment: "
                f"{get_error(response)}"
            )

    except requests.RequestException as e:

        st.error(
            f"Comment request failed: {e}"
        )


# ============================================================
# COMMENTS SECTION
# ============================================================

def comments_section(post_id):

    st.markdown("### 💬 Comments")

    try:

        response = requests.get(
            f"{API_URL}/posts/{post_id}/comments",
            headers=get_headers(),
            timeout=10
        )

        # ----------------------------------------------------
        # Authentication
        # ----------------------------------------------------

        if response.status_code == 401:

            st.warning(
                "Your session has expired. "
                "Please login again."
            )

            logout()
            return

        # ----------------------------------------------------
        # Other errors
        # ----------------------------------------------------

        if response.status_code != 200:

            st.error(
                "Could not load comments: "
                f"{get_error(response)}"
            )

            return

        # ----------------------------------------------------
        # Read comments
        # ----------------------------------------------------

        data = response.json()

        comments = data.get(
            "comments",
            []
        )

        # ----------------------------------------------------
        # No comments
        # ----------------------------------------------------

        if not comments:

            st.caption(
                "No comments yet. "
                "Be the first to comment!"
            )

            return

        # ----------------------------------------------------
        # Current user
        # ----------------------------------------------------

        current_user_id = str(
            st.session_state.user.get(
                "id",
                ""
            )
        )

        # ----------------------------------------------------
        # Display comments
        # ----------------------------------------------------

        for comment in comments:

            comment_id = comment.get("id")

            comment_user_id = str(
                comment.get(
                    "user_id",
                    ""
                )
            )

            comment_email = comment.get(
                "email",
                "User"
            )

            comment_content = comment.get(
                "content",
                ""
            )

            comment_col1, comment_col2 = st.columns(
                [8, 1]
            )

            # ------------------------------------------------
            # Comment text
            # ------------------------------------------------

            with comment_col1:

                st.markdown(
                    f"**{comment_email}**  \n"
                    f"{comment_content}"
                )

            # ------------------------------------------------
            # DELETE ICON
            # ------------------------------------------------

            with comment_col2:

                # Only comment owner sees delete icon
                if comment_user_id == current_user_id:

                    if st.button(
                        "🗑️",
                        key=f"delete_comment_{comment_id}",
                        help="Delete comment"
                    ):

                        delete_comment(
                            comment_id
                        )

    except requests.ConnectionError:

        st.error(
            "❌ Cannot connect to backend."
        )

    except requests.Timeout:

        st.error(
            "⏱️ Loading comments timed out."
        )

    except requests.RequestException as e:

        st.error(
            f"Comments request failed: {e}"
        )


# ============================================================
# FEED PAGE
# ============================================================

def feed_page():

    st.title("🏠 Feed")

    try:

        response = requests.get(
            f"{API_URL}/feed",
            headers=get_headers(),
            timeout=10
        )

        # ====================================================
        # AUTHENTICATION
        # ====================================================

        if response.status_code == 401:

            st.error(
                "Your session has expired. "
                "Please login again."
            )

            logout()
            return

        # ====================================================
        # API ERROR
        # ====================================================

        if response.status_code != 200:

            st.error(
                f"Failed to load feed: "
                f"{get_error(response)}"
            )

            return

        # ====================================================
        # POSTS
        # ====================================================

        data = response.json()

        posts = data.get(
            "posts",
            []
        )

        if not posts:

            st.info(
                "No posts yet! "
                "Be the first to share something."
            )

            return

        # ====================================================
        # CENTER FEED
        # ====================================================

        left, center, right = st.columns(
            [1, 2, 1]
        )

        with center:

            for post in posts:

                post_id = post.get("id")

                # =================================================
                # POST
                # =================================================

                with st.container(border=True):

                    # ---------------------------------------------
                    # HEADER
                    # ---------------------------------------------

                    col1, col2 = st.columns(
                        [5, 1]
                    )

                    with col1:

                        email = post.get(
                            "email",
                            "User"
                        )

                        created_at = post.get(
                            "created_at",
                            ""
                        )

                        date = (
                            created_at[:10]
                            if created_at
                            else ""
                        )

                        st.markdown(
                            f"**{email}**  \n"
                            f"_{date}_"
                        )

                    # ---------------------------------------------
                    # DELETE POST
                    # ---------------------------------------------

                    with col2:

                        if post.get(
                            "is_owner",
                            False
                        ):

                            if st.button(
                                "🗑️",
                                key=f"delete_post_{post_id}",
                                help="Delete post"
                            ):

                                delete_post(
                                    post_id
                                )

                    # ---------------------------------------------
                    # CAPTION
                    # ---------------------------------------------

                    caption = post.get(
                        "caption",
                        ""
                    )

                    if caption:

                        st.markdown(
                            caption
                        )

                # =================================================
                # MEDIA
                # =================================================

                file_type = post.get(
                    "file_type",
                    ""
                )

                media_url = post.get(
                    "url",
                    ""
                )

                if media_url:

                    if file_type == "image":

                        image_url = create_transformed_url(
                            media_url,
                            ""
                        )

                        st.image(
                            image_url,
                            width=500
                        )

                    else:

                        video_url = create_transformed_url(
                            media_url,
                            "w-600,h-400,"
                            "cm-pad_resize,"
                            "bg-blurred"
                        )

                        st.video(
                            video_url,
                            width=500
                        )

                # =================================================
                # LIKE
                # =================================================

                st.markdown("")

                like_col1, like_col2 = st.columns(
                    [1, 5]
                )

                liked = post.get(
                    "liked_by_me",
                    False
                )

                with like_col1:

                    like_button_text = (
                        "❤️"
                        if liked
                        else "🤍"
                    )

                    if st.button(
                        like_button_text,
                        key=f"like_{post_id}",
                        help=(
                            "Unlike post"
                            if liked
                            else "Like post"
                        )
                    ):

                        toggle_like(
                            post_id,
                            liked
                        )

                with like_col2:

                    likes_count = post.get(
                        "likes_count",
                        0
                    )

                    if liked:

                        st.markdown(
                            f"""
                            <span style="
                                color:#e0245e;
                                font-weight:bold;
                                font-size:16px;
                            ">
                                ❤️ {likes_count} likes
                            </span>
                            """,
                            unsafe_allow_html=True
                        )

                    else:

                        st.markdown(
                            f"**🤍 {likes_count} likes**"
                        )

                # =================================================
                # COMMENTS
                # =================================================

                comments_section(
                    post_id
                )

                # =================================================
                # ADD COMMENT
                # =================================================

                comment_col1, comment_col2 = st.columns(
                    [5, 1]
                )

                with comment_col1:

                    comment_text = st.text_input(
                        "Write a comment...",
                        key=f"comment_input_{post_id}",
                        placeholder="Write a comment...",
                        label_visibility="collapsed"
                    )

                with comment_col2:

                    if st.button(
                        "Post",
                        key=f"comment_button_{post_id}"
                    ):

                        add_comment(
                            post_id,
                            comment_text
                        )

                st.markdown("---")

    except requests.ConnectionError:

        st.error(
            "❌ Cannot connect to FastAPI.\n\n"
            "Make sure FastAPI is running on "
            "http://localhost:8000"
        )

    except requests.Timeout:

        st.error(
            "⏱️ Feed request timed out."
        )

    except requests.RequestException as e:

        st.error(
            f"Feed request failed: {e}"
        )


# ============================================================
# MAIN APPLICATION
# ============================================================

if st.session_state.user is None:

    login_page()

else:

    # ========================================================
    # SIDEBAR
    # ========================================================

    with st.sidebar:

        st.title(
            "🚀 Simple Social"
        )

        user_email = st.session_state.user.get(
            "email",
            "User"
        )

        st.write(
            "Logged in as:"
        )

        st.markdown(
            f"**{user_email}**"
        )

        st.divider()

        page = st.radio(
            "Navigation",
            [
                "🏠 Feed",
                "📸 Upload"
            ]
        )

        st.divider()

        if st.button(
            "🚪 Logout",
            use_container_width=True
        ):

            logout()

    # ========================================================
    # PAGE ROUTING
    # ========================================================

    if page == "🏠 Feed":

        feed_page()

    elif page == "📸 Upload":

        upload_page()
