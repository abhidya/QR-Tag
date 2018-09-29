class Player:
    def __init__(self, socketio, mongo, sid):
        self.socketio = socketio
        self.db = mongo.db
        self.id = sid

        self.status = ''
        self.username = ''
        self.current_game = None

        doc = self.db.players.find_one({'player_id': self.id})

        if doc is not None:
            self.status = doc['status']
            self.username = doc['username']
            self.current_game = doc['game']

    def save(self):
        self.db.players.find_one_and_replace(
            {'player_id': self.id},
            {
                'player_id': self.id,
                'status': self.status,
                'username': self.username,
                'game': self.current_game
            },
            upsert=True,
            return_document=pymongo.collection.ReturnDocument.AFTER
        )

    def emit(self, event, data, **kwargs):
        self.socketio.emit(event, data, room=self.id, **kwargs)

    def on_join_game(self, game):
        self.current_game = game.id

        self.save()

    def on_leave_game(self, game):
        self.current_game = None

        self.save()
