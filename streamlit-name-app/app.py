import streamlit as st
from streamlit.components.v1 import html

def main():
    # Check if we are on a user page
    # Using the non-experimental version of get_query_params
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
            
            # Create a FastAPI user page URL
            user_url = f"http://localhost:8000/users/{first_name}"
            
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
    
    user_url = f"http://localhost:8000/users/{user_name}"
    st.markdown(f"[Visit your custom page with editable sections]({user_url})")
    
    if st.button("Return to Main Page"):
        redirect_js = f"""
            <script>
            window.location.href = "{get_base_url()}";
            </script>
        """
        html(redirect_js)

def get_base_url():
    # In a local development environment, this will be the localhost base URL
    return "http://localhost:8501"

if __name__ == "__main__":
    main()