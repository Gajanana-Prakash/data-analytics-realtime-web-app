# socket_events.py
# Handles all WebSocket events for the real-time analytics app

from flask_socketio import join_room, leave_room


def register_socket_events(socketio):

    @socketio.on('connect')
    def handle_connect(auth=None):
        # Use request context to get session safely
        try:
            from flask import session
            user_id = session.get("user_id")
        except Exception:
            user_id = None

        if user_id:
            join_room(str(user_id))
            print(f"✅ User {user_id} connected and joined room {user_id}")
            socketio.emit('message', {
                'data': 'Connected to server successfully'
            }, room=str(user_id))
        else:
            print("⚠️ Anonymous connection attempt")

    @socketio.on('disconnect')
    def handle_disconnect():
        try:
            from flask import session
            user_id = session.get("user_id")
        except Exception:
            user_id = None

        if user_id:
            try:
                leave_room(str(user_id))
            except Exception:
                pass
            print(f"❌ User {user_id} disconnected")
        else:
            print("❌ Anonymous client disconnected")

    @socketio.on('ping_server')
    def handle_ping(data=None):
        try:
            from flask import session
            user_id = session.get("user_id")
            if user_id:
                socketio.emit('pong_client', {'status': 'alive'}, room=str(user_id))
        except Exception:
            pass