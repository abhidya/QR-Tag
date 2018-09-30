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

@app.route('/camera')
def camera():
    return render_template('camera.html', async_mode=socketio.async_mode)


@app.route('/gen_code')
def gen_code():
    return render_template('gen_code.html', async_mode=socketio.async_mode)


@app.route('/join_room')
def lobby():
    return render_template('lobby.html', async_mode=socketio.async_mode)


@app.route('/debugging')
def debug_page():
    return render_template('debugging.html', async_mode=socketio.async_mode)


@app.route('/gameplay')
def gameplay_page():
    return render_template('gameplay.html', async_mode=socketio.async_mode)


@app.route('/new_game', methods=['POST'])
def new_game():
    print("Creating new game...")
    game = Game(socketio, mongo)

    print("Generated game ID: {}".format(game.id))
    game.save()

    return jsonify({'game': game.id}), 201


@app.route('/games/<string:game_id>', methods=['GET'])
def get_game_info(game_id):
    if not Game.exists(mongo, game_id):
        abort(404)

    game = Game(socketio, mongo, game_id)
    player_info = []

    for player_id in game.players:
        player = Player(socketio, mongo, player_id)
        player_info.append(player.get_info())

    return jsonify({
        'id': game_id,
        'players': player_info,
        'state': game.state,
        'host': game.host
    })


@app.route('/players/<string:player_id>', methods=['GET'])
def get_player_info(player_id):
    if not Player.exists(mongo, player_id):
        abort(404)

    player = Player(socketio, mongo, player_id)

    return jsonify(player.get_info())


@socketio.on('join', namespace='/game')
def join(game_id):
    player = Player(socketio, mongo, request.sid)
    if not Game.exists(mongo, game_id):
        player.emit('error', 'Game does not exist')
        return

    game = Game(socketio, mongo, game_id)

    game.add_player(player)


@socketio.on('leave', namespace='/game')
def leave(game_id):
    player = Player(socketio, mongo, request.sid)
    if not Game.exists(mongo, game_id):
        player.emit('error', 'Game does not exist')
        return

    game = Game(socketio, mongo, game_id)

    game.remove_player(player)


@socketio.on('start', namespace='/game')
def start_game(game_id):
    player = Player(socketio, mongo, request.sid)
    if not Game.exists(mongo, game_id):
        player.emit('error', 'Game does not exist')
        return

    game = Game(socketio, mongo, game_id)

    if game.host != player.id:
        player.emit('error', 'Player is not host')
        return

    game.start_game()


@socketio.on('end', namespace='/game')
def end_game(game_id):
    player = Player(socketio, mongo, request.sid)
    if not Game.exists(mongo, game_id):
        player.emit('error', 'Game does not exist')
        return

    game = Game(socketio, mongo, game_id)

    if game.host != player.id:
        player.emit('error', 'Player is not host')
        return

    if game.host is not None:
        host = Player(socketio, mongo, game.host)
        game.remove_player(host)

    game.end_game()


@socketio.on('reset', namespace='/game')
def reset_game(game_id):
    player = Player(socketio, mongo, request.sid)
    if not Game.exists(mongo, game_id):
        player.emit('error', 'Game does not exist')
        return

    game = Game(socketio, mongo, game_id)

    if game.host != player.id:
        player.emit('error', 'Player is not host')
        return

    game.reset_game()


def tag_invuln_handler(tagged_player):
    socketio.sleep(15)

    game = Game(socketio, mongo, tagged_player.current_game)

    if game.state != 'running':
        return

    if tagged_player.id not in game.players:
        return

    tagged_player.status = 'alive'
    tagged_player.save()
    game.emit('player_update', tagged_player.get_info())
    tagged_player.emit('revived')


@socketio.on('tag', namespace='/game')
def on_tag(tagged_index):
    tagged_index = int(tagged_index)

    player = Player(socketio, mongo, request.sid)

    game = Game(socketio, mongo, player.current_game)
    tagged_player = game.get_player_by_index(tagged_index)

    if tagged_player is None:
        player.emit('error', 'Player does not exist')
        return

    game.tag(player, tagged_player)
    socketio.start_background_task(tag_invuln_handler, tagged_player)


@socketio.on('change_username', namespace='/game')
def change_username(new_username):
    player = Player(socketio, mongo, request.sid)
    player.username = new_username
    player.save()

    if player.current_game is not None:
        game = Game(socketio, mongo, player.current_game)
        game.emit('player_update', player.get_info())
    else:
        player.emit('player_update', player.get_info())


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
