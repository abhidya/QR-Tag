from server import app


def main():
    client = app.test_client()
    health = client.get("/health")
    assert health.status_code == 200
    created = client.post("/new_game")
    assert created.status_code == 201
    game_id = created.get_json()["game"]
    fetched = client.get("/games/{}".format(game_id))
    assert fetched.status_code == 200
    assert fetched.get_json()["id"] == game_id


if __name__ == "__main__":
    main()
