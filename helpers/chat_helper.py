"""
Chat helper classes to replace LangChain components.
"""
import streamlit as st


class ChatMessage:
    """Base class for chat messages."""
    
    def __init__(self, content: str, role: str):
        self.content = content
        self.role = role
        self.type = role  # For compatibility with existing code


class HumanMessage(ChatMessage):
    """Message from human user."""
    
    def __init__(self, content: str):
        super().__init__(content, 'user')


class AIMessage(ChatMessage):
    """Message from AI assistant."""
    
    def __init__(self, content: str):
        super().__init__(content, 'ai')


class StreamlitChatMessageHistory:
    """Chat message history stored in Streamlit session state."""
    
    def __init__(self, key: str):
        self.key = key
        if key not in st.session_state:
            st.session_state[key] = []
    
    @property
    def messages(self):
        return st.session_state[self.key]
    
    def add_user_message(self, content: str):
        st.session_state[self.key].append(HumanMessage(content))
    
    def add_ai_message(self, content: str):
        st.session_state[self.key].append(AIMessage(content))


class ChatPromptTemplate:
    """Template for chat prompts."""
    
    def __init__(self, template: str):
        self.template = template
    
    @classmethod
    def from_template(cls, template: str):
        return cls(template)
    
    def format(self, **kwargs):
        return self.template.format(**kwargs)
