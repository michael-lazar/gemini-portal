from base64 import b64encode

from geminiportal.handlers.base import TemplateHandler


class AudioHandler(TemplateHandler):
    """
    Render images using an inline <audio> tag.
    """

    template = "proxy/handlers/audio.html"

    def get_context(self):
        context = super().get_context()
        data = b64encode(self.content).decode("ascii")
        context["data_url"] = f"data:{self.mimetype};base64,{data}"
        return context
