from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from random import randint
from enum import Enum
import pymongo

from player import Player


class Game:
    def __init__(self, socketio, mongo, game_id=None):
        self.socketio = socketio
        self.mongo = mongo
        self.db = mongo.db

        if game_id is None:
            self.id = ''.join([str(randint(0, 9)) for i in range(6)])
        else:
            self.id = game_id

        self.players = []
        self.host = None
        self.state = 'prestart'

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
        self.socketio.emit(event, data, room=self.id, namespace='/game', **kwargs)

    def start_game(self):
        self.state = 'running'
        self.save()

        print("Game "+self.id+" started!")

        player_info = []

        for player_id in self.players:
            player = Player(self.socketio, self.mongo, player_id)
            player_info.append({
                'id': player.id,
                'username': player.username,
                'role': player.role
            })

        self.emit('game_start', {
            'id': self.id,
            'players': player_info
        })

    def end_game(self):
        print("Game "+self.id+" ending!")

        players = list(self.players)
        for player_id in players:
            player = Player(self.socketio, self.mongo, player_id)
            player.on_leave_game(game)

        self.db.games.remove({'game_id': self.id})
        self.emit('game_end', self.id)
        self.socketio.close_room(self.id, namespace='/game')

    def add_player(self, player):
        if player.id in self.players:
            player.emit('error', 'Already in game')
            return

        self.players.append(player.id)

        if len(self.players) == 1:
            self.host = player.id

        self.save()

        join_room(self.id, sid=player.id, namespace='/game')

        player.on_join_game(self)

        print("Player "+player.id+' joined game '+self.id)

        self.emit('joined', {'game': self.id, 'id': player.id, 'username': player.username})

    def remove_player(self, player):
        print("Player "+player.id+' left game '+self.id)

        if player.id not in self.players:
            player.emit('error', 'Not in game')
            return

        self.players.remove(player.id)
        self.save()

        leave_room(self.id, sid=player.id, namespace='/game')

        player.on_leave_game(self)

        self.emit('left', {'game': self.id, 'id': player.id, 'username': player.username})

    def tag(self, tagging_player, tagged_player):
        if self.state != 'running':
            tagging_player.emit('error', 'Game is not running')
            return

        if tagging_player.id not in self.players:
            tagging_player.emit('error', 'Tagging player not in this game')
            return

        if tagged_player.id not in self.players:
            tagging_player.emit('error', 'Tagged player not in this game')
            return

        if tagging_player.status == 'dead':
            tagging_player.emit('error', 'Tagging player is dead')
            return

        if tagged_player.status == 'dead':
            tagging_player.emit('error', 'Tagged player is dead')
            return

        print("Player "+tagging_player.id+' tagged player '+tagged_player.id)

        self.emit('tagged', {
            'id': tagged_player.id,
            'by': tagging_player.id,
            'game': self.id
        })

        tagging_player.on_tag(self, tagged_player)
        tagged_player.on_tagged(self, tagging_player)
