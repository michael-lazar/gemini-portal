from base64 import b64encode

from geminiportal.handlers.base import TemplateHandler


class BaseFileHandler(TemplateHandler):
    def get_context(self):
        context = super().get_context()

        mimetype = self.mimetype or "application/octet-stream"
        data = b64encode(self.content).decode("ascii")
        context["mimetype"] = mimetype
        context["data_url"] = f"data:{mimetype};base64,{data}"
        context["filename"] = self.url.get_filename()
        return context


class FileDownloadHandler(BaseFileHandler):
    template = "proxy/handlers/file-download.html"


class FileInlineHandler(BaseFileHandler):
    template = "proxy/handlers/file-inline.html"
