from urllib import parse


class MyApplication:
    def __init__(self, stream):
        self.stream = stream

    def do_app(self):
        req_path = self.stream.fields[":path"]
        if self.stream.fields[":method"] == "GET":
            pos = req_path.find("?")
            if pos == -1:
                qstr = ""
            else:
                qstr = req_path[pos + 1 :]
        # for POST method
        else:
            qstr = self.stream.post_data.decode()
        params = parse.parse_qs(qstr)

        fields = {"content-type": "text/html; charset=utf-8"}
        self.stream.send_headers(200, fields)

        cont = "<html><body>\n"
        cont += "<h1>Headers</h1><table border='1'>\n"
        for nm, val in self.stream.fields.items():
            cont += f"<tr><td>{nm}</td><td>{val}</td></tr>\n"
        cont += "</table>\n"

        cont += "<h1>Parameters</h1><table border='1'>"
        for nm, val in params.items():
            cont += f"<tr><td>{nm}</td><td>{val}</td></tr>\n"
        cont += "</table></body></html>\n"

        self.stream.send_data(cont.encode())
