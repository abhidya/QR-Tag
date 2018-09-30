var socket = null;
var scanner = null;

var players = {};
var username = '';
var game_host = null;
var game_code = null;

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

submit_username.click(function () {
    username = username_prompt.val();
    username_form.hide();
    game_form.show();

    return false;
});

back_button.click(function () {
    game_form.hide();
    username_form.show();

    return false;
});

function activateCamera() {
    let scanner = new Instascan.Scanner({video: document.getElementById('camera-preview'), mirror: false });

    scanner.addListener('scan', function (content) {
        console.log(content);
        socket.emit('tag', content);
        tempAlert("You Tagged Player " + content, 1000);
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

submit_code.click(function () {
    game_code = gamecode_prompt.val().toString().padStart(6, '0');
    console.log(game_code);

    pregame_form_wrapper.hide();
    game_screen_wrapper.show();
    camera_preview.show();

    return false;
})

$(function () {
    //var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + '/game');

    activateCamera();
})
