import unittest

from tests.test_survey import client, app

def test_cg(client):
    path = "/tasks/cg/"
    with app.test_request_context(path):
        client.get(path)
        res = client.post(
            path,
            data={"donation_a":0, "donation_b":0, "donation_c":0},
            follow_redirects=True
        ).data
        assert b"cg:" in res
        # assert b"60" in res


def test_crt(client):
    path = "/tasks/crt/"
    with app.test_request_context(path):
        client.get(path)
        res = client.post(
            path,
            data={"q1":0, "q2":0, "q3":0},
            follow_redirects=True
        ).data
        assert b"crt:" in res

def test_eff(client):
    path = "/tasks/eff/"
    with app.test_request_context(path):
        client.get(path)
        res = client.post(
            path,
            data={f"img_{img_id}":"xyzt" for img_id in range(1, 21)},
            follow_redirects=True
        ).data
        assert b"eff:" in res

def test_hexaco(client):
    path = "/tasks/hexaco/"
    with app.test_request_context(path):
        client.get(path)
        res = client.post(
            path,
            data={f"q{qid}": "" for qid in range(1, 31)},
            follow_redirects=True
        ).data
        assert b"hexaco:" in res

def test_risk(client):
    path = "/tasks/risk/"
    with app.test_request_context(path):
        client.get(path)
        res = client.post(
            path,
            data={f"cell{img_id}":True for img_id in range(1, 51)},
            follow_redirects=True
        ).data
        assert b"risk:" in res
    pass