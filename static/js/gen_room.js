var socket = null;
var players = {};
var game_code = null;
var game_start_time = null;



function getPlayerScore(player) {
    if (!player) return 0;
    return player.tagged.length - player.tagged_by.length;
}

function clearPlayerList() {
    $('.player-list').empty();
}

function updatePlayerList(player) {
    if (!player.username) {
        username = '<unknown username>';
    }

    let label = player.username.toString()+' [Index '+player.index+']';
    if (player.index === 0) {
        label += ' (Host)'
    }

    score = getPlayerScore(player);

    label += ' - Status: '+(player.status.charAt(0).toUpperCase()+player.status.slice(1))+' - Score: '+score

    $('.player-list').append($('<li/>').text(label));
}

function refreshPlayerList() {
    clearPlayerList();

    var p_list = Object.values(players);
    p_list.sort(function (a, b) {
        if (a.index < b.index) {
            return -1;
        } else if (a.index > b.index) {
            return 1;
        } else {
            return 0;
        }
    });

    for (player of p_list) {
        updatePlayerList(player);
    }
}

function updatePlayer(player) {
    players[player.id] = player;
    refreshPlayerList();
}

function getAllPlayers() {
    fetch('/games/'+game_code).then(function (res) {
        return res.json();
    }).then(function (msg) {
        game_host = msg.host;
        for (var i=0;i<msg.players.length;i++) {
            updatePlayer(msg.players[i]);
        }
    });
}

$('#create-game').click(function () {
    $('#create-game').attr('disabled', true);

    fetch('/new_game', {
        method: 'POST',
    }).then(function (res) {
        return res.json();
    }).then(function (body) {
        game_code = body['game'];
        socket.emit('join', body['game']);
        $('.game-code-display').text("Your game code is: "+game_code);

        $('#start-game').removeAttr('disabled');
        $('#end-game').removeAttr('disabled');
    });

    return false;
});

$('#start-game').click(function () {
    $('#start-game').attr('disabled', true);

    socket.emit('start', game_code);

    $('#reset-game').removeAttr('disabled');

    return false;
});

$('#reset-game').click(function () {
    socket.emit('reset', game_code);

    $('#start-game').removeAttr('disabled');
    $('#reset-game').attr('disabled', true);

    return false;
});

$('#end-game').click(function () {
    socket.emit('end', game_code);

    game_code = null;
    game_start_time = null;
    players = {};

    $('.game-code-display').text('Generate Game Code');
    $('.game-time-display').text('');

    clearPlayerList();

    $('#create-game').removeAttr('disabled');
    $('#start-game').attr('disabled', true);
    $('#reset-game').attr('disabled', true);
    $('#end-game').attr('disabled', true);

    return false;
})

$(function () {
    socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + '/game');

    socket.on('connect', function () {
        $('#create-game').removeAttr('disabled');
        socket.emit('change_username', 'Host');
    });

    socket.on('game_start', function (msg) {
        game_start_time = new Date();
        for (var i=0;i<msg.players.length;i++) {
            updatePlayer(msg.players[i]);
        }
    });

    socket.on('game_reset', function (msg) {
        game_start_time = null;
        $('.game-time-display').text('');
        for (var i=0;i<msg.players.length;i++) {
            updatePlayer(msg.players[i]);
        }
    });

    socket.on('game_end', function (msg) {
        players = {}
        game_start_time = null;

        refreshPlayerList();
    })

    socket.on('player_update', function (msg) {
        updatePlayer(msg);
    });

    socket.on('tagged', function (msg) {
        updatePlayer(msg.tagger);
        updatePlayer(msg.tagged);
    });

    socket.on('joined', function (msg) {
        updatePlayer(msg.player);

        if (msg.player.id === socket.id) {
            getAllPlayers();
        }
    });

    socket.on('left', function (msg) {
        updateEvent(msg.username+' left the game!');
        delete players[msg.id];

        refreshPlayerList();
    });

    setInterval(function () {
        if (!game_start_time) return;

        var elapsed_ms = Date.now() - game_start_time.getTime();

        var elapsed_sec = Math.floor(elapsed_ms / 1000) % 60;
        var elapsed_min = Math.floor(elapsed_ms / (60*1000));

        var time_str = elapsed_min.toString().padStart(2, '0')+':'+elapsed_sec.toString().padStart(2, '0');

        $('.game-time-display').text('Elapsed Time: '+time_str);
    }, 500);
});
