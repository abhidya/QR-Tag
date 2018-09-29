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

    def get_player_by_index(self, index):
        doc = self.db.players.find_one({'game': self.id, 'index': index})

        if doc is None:
            return None
        else:
            return Player(self.socketio, self.mongo, doc['player_id'])

    def start_game(self):
        self.state = 'running'
        self.save()

        print("Game "+self.id+" started!")

        player_info = []

        for player_id in self.players:
            player = Player(self.socketio, self.mongo, player_id)
            player_info.append(player.get_info())

        self.emit('game_start', {
            'id': self.id,
            'players': player_info
        })

    def reset_game(self):
        print("Resetting game "+self.id+"!")

        players = list(self.players)
        player_info = []
        for player_id in players:
            player = Player(self.socketio, self.mongo, player_id)
            player.reset_game_state()
            player_info.append(player.get_info())

        self.state = 'prestart'
        self.save()

        self.emit('game_reset', {
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

        current_index = 0
        for player_id in self.players:
            p = Player(self.socketio, self.mongo, player_id)
            if p.index >= current_index:
                current_index = p.index+1

        if current_index == 0:
            self.host = player.id

        self.players.append(player.id)
        self.save()

        join_room(self.id, sid=player.id, namespace='/game')

        player.index = current_index
        player.on_join_game(self)

        print("Player "+player.id+' joined game '+self.id+' (index '+str(current_index)+')')

        self.emit('joined', {'game': self.id, 'player': player.get_info()})

    def remove_player(self, player):
        print("Player "+player.id+' left game '+self.id)

        if player.id not in self.players:
            player.emit('error', 'Not in game')
            return

        self.players.remove(player.id)
        self.save()

        leave_room(self.id, sid=player.id, namespace='/game')

        player.on_leave_game(self)

        self.emit('left', {'game': self.id, 'id': player.id})

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

        tagging_player.on_tag(self, tagged_player)
        tagged_player.on_tagged(self, tagging_player)

        self.emit('tagged', {
            'tagged': tagged_player.get_info(),
            'tagger': tagging_player.get_info(),
            'game': self.id
        })
