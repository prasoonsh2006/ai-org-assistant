"""
Real "Login with Google" for the public/general-use mode, using the
`streamlit-google-auth` package.

SETUP (see README.md for full walkthrough):
1. Create a Google Cloud project + OAuth 2.0 Client ID (type: Web application).
2. Add http://localhost:8501 as an authorized redirect URI.
3. Download the client secret JSON and save it as `google_credentials.json`
   in this project folder.

If `google_credentials.json` is missing, Google login is simply not offered
and the app falls back to "Continue as Guest" - so the project still runs
and can be demoed/graded without anyone setting up Google Cloud.
"""

import os

CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "google_credentials.json")


def google_login_available() -> bool:
    return os.path.exists(CREDENTIALS_PATH)


def get_authenticator():
    """Returns a streamlit_google_auth Authenticate instance, or None if not configured."""
    if not google_login_available():
        return None
    from streamlit_google_auth import Authenticate

    return Authenticate(
        secret_credentials_path=CREDENTIALS_PATH,
        cookie_name="org_ai_assistant_google",
        cookie_key="a_random_local_secret_key_change_me",
        redirect_uri="http://localhost:8501",
    )
