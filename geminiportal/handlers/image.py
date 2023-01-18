from base64 import b64encode

from quart import render_template

from geminiportal.handlers.base import TemplateHandler


class ImageHandler(TemplateHandler):
    """
    Render images using an inline <image> tag.
    """

    async def get_body(self) -> str:
        data = b64encode(self.content).decode("ascii")
        data_url = f"data:{self.mimetype};base64,{data}"
        content = await render_template(
            "fragments/image.html",
            url=self.url.get_proxy_url(raw=True),
            data_url=data_url,
        )
        return content
