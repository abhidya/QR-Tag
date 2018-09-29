#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request, jsonify, abort
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


@app.route('/debugging')
def debug_page():
    return render_template('debugging.html', async_mode=socketio.async_mode)


@app.route('/new_game', methods=['POST'])
def new_game():
    print("Creating new game...")
    game = Game(socketio, mongo)

    print("Generated game ID: {}".format(game.id))
    game.save()

    return jsonify({'game': game.id}), 201

@app.route('/end_game', methods=['POST'])
def end_game():
    data = request.get_json()

    if data is None:
        abort(400)

    if not Game.exists(mongo, data['game']):
        abort(404)

    game = Game(socketio, mongo, data['game'])

    if game.host is not None:
        host = Player(socketio, mongo, game.host)
        game.remove_player(host)

    game.end_game()
    print("Ended game ID: ", data['game'])

    return '', 204

@app.route('/games/<string:game_id>', methods=['GET'])
def get_game_info(game_id):
    if not Game.exists(mongo, game_id):
        abort(404)

    game = Game(socketio, mongo, game_id)

    return jsonify({
        'id': game_id,
        'players': game.players,
        'state': game.state,
        'host': game.host
    })


@app.route('/players/<string:player_id>', methods=['GET'])
def get_player_info(player_id):
    if not Player.exists(mongo, player_id):
        abort(404)

    player = Player(socketio, mongo, player_id)

    return jsonify({
        'id': player_id,
        'username': player.username,
        'role': player.role,
        'status': player.status,
        'game': player.current_game
    })


@socketio.on('join', namespace='/game')
def join(game_id):
    game = Game(socketio, mongo, game_id)
    player = Player(socketio, mongo, request.sid)

    game.add_player(player)


@socketio.on('leave', namespace='/game')
def leave(game_id):
    game = Game(socketio, mongo, game_id)
    player = Player(socketio, mongo, request.sid)

    game.remove_player(player)


@socketio.on('start', namespace='/game')
def start_game(game_id):
    game = Game(socketio, mongo, game_id)
    player = Player(socketio, mongo, request.sid)

    if game.host != player.id:
        player.emit('error', 'Player is not host!')
        return

    game.start_game()


@socketio.on('tag', namespace='/game')
def on_tag(tagged_player_id):
    player = Player(socketio, mongo, request.sid)
    tagged_player = Player(socketio, mongo, tagged_player_id)
    game = Game(socketio, mongo, player.current_game)

    game.tag(player, tagged_player)


@socketio.on('change_username', namespace='/game')
def change_username(new_username):
    player = Player(socketio, mongo, request.sid)
    player.username = new_username
    player.save()

    if player.current_game is not None:
        game = Game(socketio, mongo, player.current_game)
        game.emit('username_changed', {
            'game': game.id,
            'id': player.id,
            'username': player.username
        })
    else:
        player.emit('username_changed', {
            'game': None,
            'id': player.id,
            'username': player.username
        })


@socketio.on('connect', namespace='/game')
def test_connect():
    player = Player(socketio, mongo, request.sid)
    player.save()

    player.emit('hello', request.sid)


@socketio.on('disconnect', namespace='/game')
def test_disconnect():
    print('Client disconnected', request.sid)

    player = Player(socketio, mongo, request.sid)
    if player.current_game is not None:
        game = Game(socketio, mongo, player.current_game)
        game.remove_player(player)

        if game.host == request.sid:
            game.end_game()

    player.delete()

if __name__ == '__main__':
    socketio.run(app, debug=True)
