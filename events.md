# Game Websocket Events and Messages

## Player Info Object

Players are represented as simple objects with the following structure:
```
{
    'id': string (player socket SID),
    'current_game': string (player game ID),
    'status': string ('alive' or 'dead'),
    'username': string,
    'role': role ('player' only for now),
    'tagged':  array of string (list of player IDs this player has tagged),
    'tagged_by': array of string (list of player IDs that have tagged this player)
}
```

## Socket Commands

### join(game_id)
Join a game.

#### Parameters
 - `game_id`: Code / ID for game to join

### leave(game_id)
Leave a game.

#### Parameters
 - `game_id`: Code / ID for game to leave

### start(game_id)
Start a game. Caller must be game host.

#### Parameters
 - `game_id`: Code / ID for game to start.

### end(game_id)
End a game. Caller must be game host.

#### Parameters
 - `game_id`: Code / ID for game to end.

### tag(player_id)
Tag the given player. The game must have been previously started.

#### Parameters
 - `player_id`: The player to tag.

### change_username(new_username)
Change the current player username.

#### Parameters
 - `new_username`: The new username to set.


## Socket Events

### joined(msg)
Sent when a player has joined the current game.

#### Parameters
`msg` has the following properties:
 - `game`: ID of the game the `player` has joined.
 - `player`: Player info object for the newly-joined player.

### left(msg)
Sent when a player has left the current game.

#### Parameters
`msg` has the following properties:
 - `game`: ID of the game the player has left.
 - `id`: ID of the player that has left.

### game_start(msg)
Sent when the current game starts.

#### Parameters
`msg` has the following properties:
 - `id`: ID of the game that has started.
 - `players`: an array of player info objects for every player in the game.

### game_end(game_id)
Sent when the current game ends.

#### Parameters
 - `game_id`: ID of the game that has ended.

### player_update(player)
Sent whenever a player's info has changed for non-tagging reasons (i.e. when a username has changed)

#### Parameters
 - `player`: The new player object to update.

### tagged(msg)
Sent whenever a player is tagged.

#### Parameters
`msg` has the following properties:
 - `game`: ID of the relevant game.
 - `tagger`: Player object for the tagging player.
 - `tagged`: Player object for the tagged player.

### error(error_msg)
Sent whenever an error occurs.

#### Parameters
 - `error_msg`: The message for the error that has occurred.
