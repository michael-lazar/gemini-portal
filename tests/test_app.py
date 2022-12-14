async def test_robots(client):
    response = await client.get("/robots.txt")
    assert response.status_code == 200
    assert response.mimetype == "text/plain"


async def test_about(client):
    response = await client.get("/about")
    assert response.status_code == 200
    assert response.mimetype == "text/html"


async def test_changes(client):
    response = await client.get("/changes")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
