class ContextManager:
    def __init__(self, max_history=10):
        self.max_history = max_history

    def format_history_for_gemini(self, db_history):
        """Converts database conversation logs to the structure Gemini API expects.
        
        Gemini expects roles to be either 'user' or 'model', and content in a 'parts' list.
        """
        formatted_messages = []
        # Get only the last max_history messages
        recent_history = db_history[-self.max_history:] if len(db_history) > self.max_history else db_history
        
        for msg in recent_history:
            role = msg["role"]
            if role == "assistant":
                role = "model"
            elif role == "user":
                role = "user"
            
            # Formats into parts structure
            formatted_messages.append({
                "role": role,
                "parts": [msg["content"]]
            })
            
        return formatted_messages
