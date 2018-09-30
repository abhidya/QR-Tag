var socket = null;
var scanner = null;

var players = {};
var username = '';
var game_host = null;
var game_code = null;
var game_start_time = null;

var pregame_form_wrapper = $('.pregame-form-wrapper');
var game_screen_wrapper = $('.game-screen-wrapper');

var username_form = $('.username-form');
var game_form = $('.game-form');
var camera_preview = $('#camera-preview');

var username_prompt = $('#username-prompt');
var gamecode_prompt = $('#code-prompt');
var submit_username = $('#submit-username');
var submit_code = $('#submit-code');
var back_button = $('#game-back-button');

function flashElement(selector) {
    $(selector).removeClass('background-normal').addClass('background-highlight');
    setTimeout(function () {
        $(selector).removeClass('background-highlight').addClass('background-normal');
    }, 100);
}

function flashEventFeed() {
    return flashElement('.event-feed-container');
}

function flashScoreFeed() {
    return flashElement('.score-feed-container');
}

function updateEvent(msg) {
    $('.event-feed').text(msg);
    flashEventFeed();
}

function getPlayerScore(player) {
    if (!player) return 0;
    return player.tagged.length - player.tagged_by.length;
}

function updatePlayer(player) {
    if (player.id === socket.id && getPlayerScore(players[player.id]) != getPlayerScore(player)) {
        $('.score-feed').text("Score: "+getPlayerScore(player));
        flashScoreFeed();
    }

    players[player.id] = player;
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

submit_username.click(function () {
    username = username_prompt.val();
    username_form.hide();
    game_form.show();

    socket.emit('change_username', username);

    return false;
});

back_button.click(function () {
    game_form.hide();
    username_form.show();

    return false;
});

submit_code.click(function () {
    game_code = gamecode_prompt.val().toString().padStart(6, '0');
    console.log(game_code);

    pregame_form_wrapper.hide();
    game_screen_wrapper.show();

    socket.emit('join', game_code);
    activateCamera();

    return false;
});

function activateCamera() {
    let scanner = new Instascan.Scanner({video: document.getElementById('camera-preview'), mirror: false });

    scanner.addListener('scan', function (content) {
        console.log("Scanned player:" + content);
        socket.emit('tag', content);
    });

    Instascan.Camera.getCameras().then(function (cameras) {
        if (cameras.length > 0) {
            if (cameras[1]) {
                scanner.start(cameras[1]);
            } else {
                scanner.start(cameras[0]);
            }
        } else {
            console.error('No cameras found.');
        }
    }).catch(function (e) {
        console.error(e);
    });
}

$(function () {
    socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + '/game');

    socket.on('error', function (err) {
        updateEvent("Error: "+err);
    });

    socket.on('tagged', function (msg) {
        updatePlayer(msg.tagger);
        updatePlayer(msg.tagged);

        if (msg.tagged.id === socket.id) {
            updateEvent("You got tagged by "+msg.tagger.username+"!");
        } else if (msg.tagger.id === socket.id) {
            updateEvent("You tagged "+msg.tagged.username+"!");
        }
    });

    socket.on('player_update', function (msg) {
        updatePlayer(msg);
    });

    socket.on('joined', function (msg) {
        updatePlayer(msg.player);

        if (msg.player.id === socket.id) {
            updateEvent("Successfully entered game!");
            getAllPlayers();
        } else {
            updateEvent(msg.player.username+' joined the game!');
        }
    });

    socket.on('left', function (msg) {
        updateEvent(msg.username+' left the game!');
        delete players[msg.id];
    });

    socket.on('game_start', function (msg) {
        updateEvent("The game has started!");
        game_start_time = new Date();
        for (var i=0;i<msg.players.length;i++) {
            updatePlayer(msg.players[i]);
        }
    });

    socket.on('game_reset', function (msg) {
        updateEvent("The game is restarting!");
        game_start_time = new Date();
        for (var i=0;i<msg.players.length;i++) {
            updatePlayer(msg.players[i]);
        }
    });

    socket.on('game_end', function (id) {
        updateEvent("The game has ended!");

        players = {};
        game_start_time = null;
    });

    setInterval(function () {
        if (!game_start_time) return;

        var elapsed_ms = Date.now() - game_start_time.getTime();

        var elapsed_sec = Math.floor(elapsed_ms / 1000) % 60;
        var elapsed_min = Math.floor(elapsed_ms / (60*1000));

        var time_str = elapsed_min.toString().padStart(2, '0')+':'+elapsed_sec.toString().padStart(2, '0');

        $('.time-feed').text('Time:'+time_str);
    }, 500);
});
