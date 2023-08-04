from base64 import b64encode

from geminiportal.handlers.base import TemplateHandler


class FileHandler(TemplateHandler):
    template = "proxy/handlers/file.html"

    def get_context(self):
        context = super().get_context()

        mimetype = self.mimetype or "application/octet-stream"
        data = b64encode(self.content).decode("ascii")
        context["data_url"] = f"data:{mimetype};base64,{data}"
        return context
