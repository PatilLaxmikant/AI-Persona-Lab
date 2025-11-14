import streamlit as st
import httpx  # <-- New: Async-compatible requests
import asyncio # <-- New: For running async tasks
from models.persona import Persona # Ensure Persona is imported if needed

class ChatInterface:
    def __init__(self):
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'active_personas' not in st.session_state:
            st.session_state.active_personas = set()
        if 'persona_active_states' not in st.session_state:
            st.session_state.persona_active_states = {}

    async def _get_persona_response_async(self, session: httpx.AsyncClient, persona: Persona, prompt: str) -> dict:
        """
        Get a response from a persona using Ollama API (ASYNC).
        Returns a message dictionary.
        """
        system_prompt = f"""You are {persona.name}, a {persona.age}-year-old {persona.nationality} {persona.occupation}.
        Background: {persona.background}
        Daily Routine: {persona.routine}
        Personality: {persona.personality}
        Skills: {', '.join(persona.skills)}
        
        Respond to messages in character, incorporating your background, personality, and expertise.
        Keep responses concise (2-3 sentences) and natural.
        """
        
        try:
            response = await session.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": persona.model,
                    "prompt": f"Previous message: {prompt}\nRespond naturally as {persona.name}:",
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": persona.temperature,
                        "num_predict": persona.max_tokens
                    }
                },
                timeout=30.0 # Add a timeout
            )
            response.raise_for_status()
            result = response.json()
            
            # Return the message dictionary
            return {
                "role": "assistant",
                "content": result["response"].strip(),
                "name": persona.name,
                "avatar": persona.avatar
            }
            
        except Exception as e:
            print(f"Error getting response from {persona.name}: {str(e)}")
            # Return an error message in the bot's "voice"
            return {
                "role": "assistant",
                "content": f"Sorry, I'm having trouble responding right now. (Error: {str(e)})",
                "name": persona.name,
                "avatar": persona.avatar
            }

    def render(self):
        """Render the chat interface."""
        # Sidebar for persona management
        with st.sidebar:
            st.header("Manage Personas")
            
            # Create Persona Form (from original interface.py)
            with st.expander("Create New Persona", expanded=False):
                occupations = [
                    "Business Owner", "Marketing Manager", "Finance Director",
                    "Sales Representative", "Customer Service Manager", "Operations Manager", "Other"
                ]
                with st.form("create_persona_form_sidebar"):
                    selected_occupation = st.selectbox("Select Occupation", options=occupations, key="occupation_select")
                    custom_occupation = None
                    if selected_occupation == "Other":
                        custom_occupation = st.text_input("Enter Custom Occupation")
                    
                    if st.form_submit_button("🎯 Generate Persona"):
                        # ... (Rest of your persona creation logic from interface.py) ...
                        # (This logic is fine to keep here if you like)
                        pass # Placeholder, your original code was here
            
            # Current Personas section (toggles)
            st.subheader("Active Personas (Chat)")
            personas = st.session_state.persona_manager.list_personas()
            for persona in personas:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(persona.avatar, width=50)
                with col2:
                    st.write(f"**{persona.name}**")
                
                is_active = st.session_state.persona_active_states.get(persona.id, True)
                if st.toggle("Active in Chat", value=is_active, key=f"toggle_{persona.id}"):
                    st.session_state.active_personas.add(persona.id)
                    st.session_state.persona_active_states[persona.id] = True
                else:
                    st.session_state.active_personas.discard(persona.id)
                    st.session_state.persona_active_states[persona.id] = False
                st.divider()
        
        # --- Main chat area ---
        st.subheader("🤖 Group Chat")
        
        # --- Display chat messages (NEW UI) ---
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.write(f"**You:** {message['content']}")
            else:
                # Bot-centric UI
                col1, col2 = st.columns([1, 10]) 
                with col1:
                    st.image(message["avatar"], width=50, caption=message.get("name"))
                with col2:
                    # Using st.info() for the bot-theme bubble
                    st.info(message["content"])

        # --- Chat input (NEW ASYNC LOGIC) ---
        if prompt := st.chat_input("Chat with your active personas..."):
            # Add user message
            st.session_state.messages.append({
                "role": "user",
                "content": prompt,
                "name": "You"
            })
            
            # Get active personas
            active_personas = [p for p in personas if p.id in st.session_state.active_personas]
            
            async def get_all_responses():
                """Gathers all persona responses concurrently."""
                async with httpx.AsyncClient() as session:
                    tasks = []
                    for persona in active_personas:
                        tasks.append(self._get_persona_response_async(session, persona, prompt))
                    
                    # Wait for all responses
                    responses = await asyncio.gather(*tasks)
                    # Add valid responses to the message list
                    st.session_state.messages.extend([res for res in responses if res])
            
            # Run the async function
            asyncio.run(get_all_responses())
            
            # Rerun to update the chat display
            st.rerun()
