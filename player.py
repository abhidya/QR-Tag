import pymongo
from enum import Enum

class Player:
    def __init__(self, socketio, mongo, sid):
        self.socketio = socketio
        self.db = mongo.db
        self.id = sid

        self.username = ''
        self.current_game = None

        self.role = 'player'
        self.status = 'alive'
        self.index = -1

        self.players_tagged = []
        self.players_tagged_by = []

        doc = self.db.players.find_one({'player_id': self.id})

        if doc is not None:
            self.status = doc['status']
            self.username = doc['username']
            self.current_game = doc['game']
            self.role = doc['role']
            self.players_tagged = doc['players_tagged']
            self.players_tagged_by = doc['players_tagged_by']
            self.index = doc['index']

    @staticmethod
    def exists(mongo, player_id):
        doc = mongo.db.players.find_one({'player_id': player_id})

        return doc is not None

    def save(self):
        self.db.players.find_one_and_replace(
            {'player_id': self.id},
            {
                'player_id': self.id,
                'status': self.status,
                'username': self.username,
                'game': self.current_game,
                'role': self.role,
                'players_tagged': self.players_tagged,
                'players_tagged_by': self.players_tagged_by,
                'index': self.index
            },
            upsert=True,
            return_document=pymongo.collection.ReturnDocument.AFTER
        )

    def delete(self):
        self.db.players.remove({'player_id': self.id})

    def get_info(self):
        return {
            'id': self.id,
            'current_game': self.current_game,
            'status': self.status,
            'username': self.username,
            'role': self.role,
            'tagged': self.players_tagged,
            'tagged_by': self.players_tagged_by,
            'index': self.index
        }

    def emit(self, event, data, **kwargs):
        self.socketio.emit(event, data, room=self.id, namespace='/game', **kwargs)

    def on_join_game(self, game):
        self.current_game = game.id

        self.save()

    def on_leave_game(self, game):
        self.current_game = None

        self.save()

    def on_tag(self, game, tagged_player):
        self.players_tagged.append(tagged_player.id)
        self.save()

    def on_tagged(self, game, tagging_player):
        self.status = 'dead'
        self.players_tagged_by.append(tagging_player.id)
        self.save()
