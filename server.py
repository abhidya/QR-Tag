#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request, jsonify
from flask_pymongo import PyMongo
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

from game import Game
from player import Player

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/cql8r'
mongo = PyMongo(app)
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@app.route('/gen_code')
def gen_code():
    return render_template('gen_code.html', async_mode=socketio.async_mode)


@app.route('/join_room')
def lobby():
    return render_template('lobby.html', async_mode=socketio.async_mode)


@app.route('/new_game', methods=['POST'])
def new_game():
    print("Creating new game...")
    game = Game(socketio, mongo)

    print("Generated game ID: {}".format(game.id))
    game.save()

    return jsonify({'game_id': game.id}), 201

@app.route('/end_game', methods=['POST'])
def end_game():
    data = request.get_json()

    if data is None:
        abort(400)

    if not Game.exists(mongo, data['game']):
        abort(404)

    game = Game(socketio, mongo, data['game'])
    game.end_game()

    return '', 204

@app.route('/players', methods=['POST'])
def get_players():
    data = request.get_json()

    if data is None:
        abort(400)

    if not Game.exists(mongo, data['game']):
        abort(404)

    game = Game(socketio, mongo, data['game'])

    return jsonify(game['players'])


@socketio.on('join', namespace='/game')
def join(message):
    game = Game(socketio, mongo, message['game'])
    player = Player(socketio, mongo, request.sid)
    game.add_player(player)


@socketio.on('leave', namespace='/game')
def leave(message):
    game = Game(socketio, mongo, message['game'])
    player = Player(socketio, mongo, request.sid)

    game.remove_player(player)


@socketio.on('tag', namespace='/game')
def on_tag(message):
    player = Player(socketio, mongo, request.sid)
    tagged_player = Player(socketio, mongo, message['tagged_player'])
    game = Game(socketio, mongo, player.current_game)

    tagged_player.emit('tagged', {
        'by': request.sid,
        'game': game.id
    })


@socketio.on('connect', namespace='/game')
def test_connect():
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/game')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, debug=True)
