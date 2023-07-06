from base64 import b64encode

from geminiportal.handlers.base import TemplateHandler


class ImageHandler(TemplateHandler):
    """
    Render images using an inline <image> tag.
    """

    template = "proxy/protocols/image.html"

    def get_context(self):
        context = super().get_context()
        data = b64encode(self.content).decode("ascii")
        context["data_url"] = f"data:{self.mimetype};base64,{data}"
        context["raw_url"] = self.url.get_proxy_url(raw=True)
        return context
