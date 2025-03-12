import streamlit as st
from streamlit.components.v1 import html
import os

# Get the API base URL from environment or use default
def get_api_url():
    # Check if we're in Streamlit Cloud
    if os.getenv("STREAMLIT_CLOUD", "") == "true":
        # In cloud, use the deployed URL base
        return "https://challenge-sise-production.up.railway.app"
    else:
        # Local development
        return "https://challenge-sise-production.up.railway.app:8000"

# Get the Streamlit URL from environment or use deployed URL
def get_streamlit_url():
    return os.getenv("STREAMLIT_URL", "https://challenge-sise-production.up.railway.app/")

def main():
    # Check if we are on a user page
    query_params = st.query_params
    if "name" in query_params:
        user_name = query_params["name"]
        show_user_page(user_name)
    else:
        show_main_page()

def show_main_page():
    st.title("Personalized Page Creator")
    
    first_name = st.text_input("Enter your first name:")
    
    if st.button("Create Your Page"):
        if first_name:
            # Store the name in session state
            st.session_state.user_name = first_name
            
            # Create a user page URL using the base URL
            user_url = f"{get_api_url()}/users/{first_name}"
            
            st.success(f"Your personal page has been created!")
            st.markdown(f"[Visit your page]({user_url})")
            
            # Alternatively, use JS to redirect
            if st.button("Go to page now"):
                redirect_js = f"""
                    <script>
                    window.location.href = "{user_url}";
                    </script>
                """
                html(redirect_js)
        else:
            st.error("Please enter a name.")

def show_user_page(user_name):
    st.title(f"Welcome to your page, {user_name}!")
    st.write(f"This is your personalized page.")
    st.balloons()
    
    user_url = f"{get_api_url()}/users/{user_name}"
    st.markdown(f"[Visit your custom page with editable sections]({user_url})")
    
    if st.button("Return to Main Page"):
        redirect_js = f"""
            <script>
            window.location.href = "{get_streamlit_url()}";
            </script>
        """
        html(redirect_js)

if __name__ == "__main__":
    main()