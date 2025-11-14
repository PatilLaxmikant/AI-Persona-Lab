import streamlit as st
from datetime import datetime
from models.persona import PersonaManager
from chat.interface import ChatInterface
import logging

# Configure the Streamlit page - must be first
st.set_page_config(page_title="AI Persona Lab", layout="wide", page_icon="🤖", initial_sidebar_state="expanded")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def initialize_session_state():
    """Initialize session state with default values."""
    if 'persona_manager' not in st.session_state:
        st.session_state.persona_manager = PersonaManager()
    if 'chat_interface' not in st.session_state:
        st.session_state.chat_interface = ChatInterface()
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = st.session_state.persona_manager.settings["default_model"]
    if 'temperature' not in st.session_state:
        st.session_state.temperature = st.session_state.persona_manager.settings["default_temperature"]
    if 'max_tokens' not in st.session_state:
        st.session_state.max_tokens = st.session_state.persona_manager.settings["default_max_tokens"]

# --- Callbacks (no change) ---
def on_model_change():
    st.session_state.persona_manager.settings["default_model"] = st.session_state.selected_model

def on_temperature_change():
    st.session_state.persona_manager.settings["default_temperature"] = st.session_state.temperature

def on_tokens_change():
    st.session_state.persona_manager.settings["default_max_tokens"] = st.session_state.max_tokens

def generate_persona(occupation):
    """Generate a new persona with the given occupation"""
    with st.spinner(f"Generating {occupation} persona..."):
        try:
            persona = st.session_state.persona_manager.generate_persona(
                occupation=occupation,
                model=st.session_state.selected_model,
                temperature=st.session_state.temperature,
                max_tokens=st.session_state.max_tokens
            )
            if persona:
                st.success(f"Created new persona: {persona.name}")
                st.rerun()
            else:
                st.error("Failed to generate persona. Please try again.")
        except Exception as e:
            st.error(f"Error generating persona: {str(e)}")

def render_model_settings():
    """Render model settings section in sidebar."""
    with st.sidebar:
        with st.expander("⚙️ Default Model Settings", expanded=False):
            available_models = st.session_state.persona_manager.get_available_models()
            if not available_models:
                st.error("No Ollama models available. Run 'ollama pull <model>'")
                return
            
            model_index = available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0
            st.selectbox(
                "Default Model", options=available_models, index=model_index,
                key='selected_model', on_change=on_model_change,
                help="Select the default model for generating new personas"
            )
            st.slider(
                "Default Temperature", min_value=0.0, max_value=1.0, value=st.session_state.temperature,
                step=0.1, key='temperature', on_change=on_temperature_change,
                help="Higher values = more creative, Lower values = more deterministic"
            )
            st.number_input(
                "Default Max Tokens", min_value=50, max_value=2000, value=st.session_state.max_tokens,
                step=50, key='max_tokens', on_change=on_tokens_change,
                help="Maximum number of tokens in model responses"
            )

def render_persona_edit_dialog(persona):
    """
    Renders the consolidated edit form inside a dialog.
    This replaces all the individual forms from the old tab layout.
    """
    with st.form(f"edit_persona_{persona.id}"):
        st.subheader(f"✏️ Editing {persona.name}")
        
        # --- Basic Information ---
        st.header("Basic Information")
        new_name = st.text_input("Name", value=persona.name)
        new_age = st.number_input("Age", min_value=18, max_value=100, value=persona.age)
        new_nationality = st.text_input("Nationality", value=persona.nationality)
        new_occupation = st.text_input("Occupation", value=persona.occupation)
        
        # --- Background & Personality ---
        st.header("Personality & Background")
        new_background = st.text_area("Background", value=persona.background, height=100)
        new_personality = st.text_area("Personality", value=persona.personality, height=100)
        new_routine = st.text_area("Daily Routine", value=persona.routine, height=100)
        
        # --- Skills ---
        st.header("Skills")
        skills_str = ", ".join(persona.skills)
        new_skills = st.text_area("Skills (comma-separated)", value=skills_str, height=100)
        
        # --- Persona-Specific Model Settings ---
        st.header("Persona Model Settings")
        models = st.session_state.persona_manager.get_available_models()
        if not models:
            st.error("No Ollama models available.")
        else:
            new_model = st.selectbox(
                "Model", options=models,
                index=models.index(persona.model) if persona.model in models else 0,
                key=f"model_select_{persona.id}"
            )
            new_temperature = st.slider(
                "Temperature", min_value=0.0, max_value=1.0, value=persona.temperature,
                step=0.1, key=f"temp_slider_{persona.id}"
            )
            new_max_tokens = st.number_input(
                "Max Tokens", min_value=50, max_value=2000, value=persona.max_tokens,
                step=50, key=f"tokens_input_{persona.id}"
            )
        
        # --- Notes & Tags ---
        st.header("Metadata")
        new_notes = st.text_area("Notes", value=persona.notes, height=100)
        new_tags = st.text_input("Tags (comma-separated)", value=", ".join(persona.tags))

        # --- Submit Button ---
        if st.form_submit_button("✅ Save Changes"):
            # Update the persona object with all new values
            persona.name = new_name
            persona.age = new_age
            persona.nationality = new_nationality
            persona.occupation = new_occupation
            persona.background = new_background
            persona.personality = new_personality
            persona.routine = new_routine
            persona.skills = [s.strip() for s in new_skills.split(",") if s.strip()]
            if models:
                persona.model = new_model
                persona.temperature = new_temperature
                persona.max_tokens = new_max_tokens
            persona.notes = new_notes
            persona.tags = [t.strip() for t in new_tags.split(",") if t.strip()]
            persona.modified_at = datetime.now()
            
            # Save all personas (as the original app.py did)
            st.session_state.persona_manager._save_personas()
            
            # Close the dialog
            del st.session_state.edit_persona_id
            st.success(f"Updated {persona.name}!")
            st.rerun()

def main():
    # Initialize session state
    initialize_session_state()
    
    # Load personas
    personas = st.session_state.persona_manager.list_personas()
    if not personas:
        st.session_state.persona_manager.create_default_persona()
        personas = st.session_state.persona_manager.list_personas()
    
    # Sidebar for creating new personas
    with st.sidebar:
        st.title("Persona Generator")
        occupations = [
            "Professor 👨‍🏫", "Engineer 👷", "Artist 🎨",
            "Doctor 👨‍⚕️", "Writer ✍️", "Chef 👨‍🍳", "Other"
        ]
        selected_occupation = st.selectbox("Select Occupation", occupations)
        
        if selected_occupation == "Other":
            custom_occupation = st.text_input("Enter Custom Occupation")
            if st.button("Generate Custom Persona"):
                if custom_occupation:
                    generate_persona(custom_occupation)
                else:
                    st.warning("Please enter an occupation")
        else:
            if st.button("Generate Persona"):
                occupation = selected_occupation.split(" ")[0]
                generate_persona(occupation)
    
    # Render default model settings in sidebar
    render_model_settings()
    
    st.title("🤖 AI Persona Lab")
    
    # --- NEW CARD DASHBOARD (replaces st.tabs) ---
    st.subheader("Persona Dashboard")
    
    if not personas:
        st.info("Add some personas using the sidebar to start!")
        return

    num_cols = 3 # 3 cards per row
    cols = st.columns(num_cols)
    
    for idx, persona in enumerate(personas):
        col = cols[idx % num_cols] # Distribute personas into 3 columns
        with col:
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.image(persona.avatar, width=70)
                with c2:
                    st.subheader(persona.name)
                    st.caption(f"*{persona.occupation}*")
                
                st.markdown(f"**Model:** `{persona.model}`")
                
                if st.button("Edit ✏️", key=f"edit_{persona.id}", use_container_width=True):
                    # Set a session state flag to open the dialog
                    st.session_state.edit_persona_id = persona.id
                
                # Add a delete button
                if st.button("Delete 🗑️", key=f"delete_{persona.id}", use_container_width=True):
                    st.session_state.persona_manager.remove_persona(persona.id)
                    st.success(f"Removed {persona.name}")
                    st.rerun()
                    
# --- DIALOG HANDLING ---
    # Check if the edit flag is set in session state
    if 'edit_persona_id' in st.session_state:
        persona_to_edit = st.session_state.persona_manager.get_persona(st.session_state.edit_persona_id)
        if persona_to_edit:
            # This is the correct pattern:
            # 1. Define a function
            # 2. Decorate it with @st.dialog
            # 3. Call the function
            
            @st.dialog("Edit Persona Details")
            def display_edit_dialog():
                # This function (which you already have) contains the st.form
                render_persona_edit_dialog(persona_to_edit)
            
            # This call opens the dialog
            display_edit_dialog()
            
        else:
            # Safety check: if persona ID is invalid, clear the flag
            del st.session_state.edit_persona_id
    
    # --- Chat interface at the bottom ---
    st.markdown("---")
    st.session_state.chat_interface.render()

if __name__ == "__main__":
    main()
