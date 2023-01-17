from base64 import b64encode

from geminiportal.handlers.base import TemplateHandler


class AudioHandler(TemplateHandler):
    """
    Render images using an inline <audio> tag.
    """

    def get_body(self) -> str:
        data = b64encode(self.content).decode("ascii")
        data_url = f"data:{self.mimetype};base64,{data}"
        return f'<audio controls="controls"><source src="{data_url}"/></audio>'
