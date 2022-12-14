from datetime import datetime

from quart import Quart, Response, render_template

app = Quart(__name__)
app.config.from_prefixed_env()


@app.route("/robots.txt")
async def robots() -> Response:
    return await app.send_static_file("robots.txt")


@app.route("/about")
async def about() -> str:
    return await render_template("about.html", year=datetime.utcnow().year)


@app.route("/changes")
async def changes() -> str:
    return await render_template("changes.html")


if __name__ == "__main__":
    app.run()
