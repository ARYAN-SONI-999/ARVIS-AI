import threading
from flask_socketio import emit
from agent.brain import ArvisBrain
from agent.task_router import TaskRouter

def register_socket_events(socketio):
    """Binds Socket.IO events for duplex chat streaming."""
    
    @socketio.on('connect')
    def handle_connect():
        print("🔌 Client connected via WebSockets.")
        emit('connection_response', {"status": "connected", "message": "Secure channel established with ARVIS."})

    @socketio.on('user_message')
    def handle_user_message(data):
        prompt = data.get("message", "")
        session_id = data.get("session_id", "web_session")
        if not prompt:
            return

        # Run the ReAct loop in a background task to keep Flask responsive
        def run_thread():
            try:
                router = TaskRouter()
                # Create a brain instance bound to this session
                brain = ArvisBrain(session_id=session_id, task_router=router)
                
                # Iterate over brain updates and emit them in real-time
                for event in brain.execute_react_loop(prompt):
                    event["session_id"] = session_id
                    socketio.emit('react_update', event)
                    if event.get("type") == "final_answer":
                        import voice.tts_engine as tts
                        tts.speak_async(event.get("content", ""))
                    
            except Exception as e:
                socketio.emit('react_update', {"type": "error", "message": f"Server crash: {str(e)}", "session_id": session_id})
                
        socketio.start_background_task(run_thread)
