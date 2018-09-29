from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from random import randint
from enum import Enum
import pymongo


class Game:
    class State(Enum):
        PRESTART = 1
        RUNNING = 2

    def __init__(self, socketio, mongo, game_id=None):
        self.socketio = socketio
        self.db = mongo.db

        if game_id is None:
            self.id = ''.join([str(randint(0, 9)) for i in range(6)])
        else:
            self.id = game_id

        self.players = []
        self.host = None
        self.state = State.PRESTART

        # attempt to load from database:
        doc = self.db.games.find_one({'game_id': self.id})

        if doc is not None:
            self.players = doc['players']
            self.host = doc['host']
            self.state = doc['state']

    @staticmethod
    def exists(mongo, game_id):
        doc = mongo.db.games.find_one({'game_id': game_id})

        return (doc is not None)

    def save(self):
        return self.db.games.find_one_and_replace(
            {'game_id': self.id},
            {
                'game_id': self.id,
                'players': self.players,
                'host': self.host,
                'state': self.state
            },
            upsert=True,
            return_document=pymongo.collection.ReturnDocument.AFTER
        )

    def emit(self, event, data, **kwargs):
        self.socketio.emit(event, data, room=self.id, **kwargs)

    def start_game(self):
        self.state = State.RUNNING
        self.save()

        self.emit('game_start', self.id)

    def end_game(self):
        self.db.games.remove({'game_id': self.id})
        self.emit('game_end', self.id)
        self.socketio.close_room(self.id)

    def add_player(self, player):
        if player.id in self.players:
            return

        self.players.append(player.id)

        if len(self.players) == 1:
            self.host = player.id

        self.save()

        join_room(self.id, sid=player.id)

        player.on_join_game(self)

        self.emit('joined', {'game': self.id, 'id': player.id, 'username': player.username})

    def remove_player(self, player):
        self.players.remove(player.id)
        self.save()

        leave_room(self.id, sid=player.id)

        player.on_leave_game(self)

        self.emit('left', {'game': game.id, 'id': player.id, 'username': player.username})

    def tag(self, tagging_player, tagged_player):
        if self.state != State.RUNNING:
            return

        tagged_player.emit('tagged', {
            'by': tagging_player.id,
            'game': game.id
        })

        tagging_player.on_tag(self, tagged_player)
        tagged_player.on_tagged(self, tagging_player)
