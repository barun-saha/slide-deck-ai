"""
Chat helper: message classes and history.
"""


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


class ChatMessageHistory:
    """Chat message history stored in a list."""
    
    def __init__(self):
        self.messages = []
    
    def add_user_message(self, content: str):
        """Append user message to the history."""
        self.messages.append(HumanMessage(content))
    
    def add_ai_message(self, content: str):
        """Append AI-generated response to the history."""
        self.messages.append(AIMessage(content))


class ChatPromptTemplate:
    """Template for chat prompts."""
    
    def __init__(self, template: str):
        self.template = template
    
    @classmethod
    def from_template(cls, template: str):
        return cls(template)
    
    def format(self, **kwargs):
        return self.template.format(**kwargs)
