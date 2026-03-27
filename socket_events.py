# socket_events.py

from flask import request, session

def register_socket_events(socketio):

    @socketio.on('connect')
    def handle_connect(auth=None):

        user_id = session.get("user_id")

        if user_id:
            from flask_socketio import join_room

            join_room(str(user_id))
            print(f"✅ User {user_id} connected")

            socketio.emit('message', {
                'data': 'Connected successfully'
            }, room=str(user_id))

    @socketio.on('disconnect')
    def handle_disconnect():
        print("❌ Client disconnected")