from base64 import b64encode

from quart import escape

from geminiportal.handlers.base import TemplateHandler


class ImageHandler(TemplateHandler):
    """
    Render images using an inline <image> tag.
    """

    def get_body(self) -> str:
        raw_url = self.url.get_proxy_url(raw=True)

        data = b64encode(self.content).decode("ascii")
        data_url = f"data:{self.mimetype};base64,{data}"
        return f'<a href="{escape(raw_url)}"><img src="{data_url}"></img></a>'
