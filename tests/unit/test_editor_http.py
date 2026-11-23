import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from engine.editor.server import CWIHandler


@pytest.fixture
def local_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), CWIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_port
    server.shutdown()
    server.server_close()
    thread.join()


def request(port, path, origin=None):
    connection = http.client.HTTPConnection("127.0.0.1", port)
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    connection.request("POST", path, "{}", headers)
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response.status, json.loads(body)


def test_api_rejects_external_web_origin(local_server):
    assert (
        request(local_server, "/api/get_project", "https://outside.invalid")[0] == 403
    )
    assert (
        request(local_server, "/api/render/create", "https://outside.invalid")[0] == 403
    )


def test_api_rejects_internal_attributes_and_accepts_local_reads(local_server):
    assert request(local_server, "/api/editor")[0] == 404
    assert request(local_server, "/api/__init__")[0] == 404
    status, body = request(local_server, "/api/get_project", "http://localhost:5173")
    assert status == 200 and body["success"]


def test_render_video_supports_byte_ranges(local_server, tmp_path, monkeypatch):
    from engine.editor import server

    video = tmp_path / "result.mp4"
    video.write_bytes(b"0123456789")
    monkeypatch.setattr(server.render_jobs, "download", lambda _: video)
    for header, expected in [
        ("bytes=2-5", b"2345"),
        ("bytes=-3", b"789"),
        ("bytes=7-", b"789"),
    ]:
        connection = http.client.HTTPConnection("127.0.0.1", local_server)
        connection.request(
            "GET", "/api/render/test/download", headers={"Range": header}
        )
        response = connection.getresponse()
        assert response.status == 206
        assert response.getheader("Accept-Ranges") == "bytes"
        assert response.read() == expected
        connection.close()
    connection = http.client.HTTPConnection("127.0.0.1", local_server)
    connection.request(
        "GET", "/api/render/test/download", headers={"Range": "bytes=99-"}
    )
    response = connection.getresponse()
    assert response.status == 416
    response.read()
    connection.close()


def test_api_rejects_malformed_body_and_get_mutation(local_server):
    for body in ["[1]", "{", "null"]:
        connection = http.client.HTTPConnection("127.0.0.1", local_server)
        connection.request(
            "POST", "/api/get_project", body, {"Content-Type": "application/json"}
        )
        response = connection.getresponse()
        assert response.status == 400
        response.read()
        connection.close()
    connection = http.client.HTTPConnection("127.0.0.1", local_server)
    connection.request("GET", "/api/undo")
    response = connection.getresponse()
    assert response.status == 405
    response.read()
    connection.close()


def test_render_create_rejects_invalid_request_key(local_server):
    connection = http.client.HTTPConnection("127.0.0.1", local_server)
    connection.request("POST", "/api/render/create", "{}", {
        "Content-Type": "application/json", "X-CWI-Request-Key": "invalid/key",
    })
    response = connection.getresponse()
    assert response.status == 400
    assert "request key" in json.loads(response.read())["error"]
    connection.close()
