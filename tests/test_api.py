from fastapi.testclient import TestClient
from backend import store
from backend.main import app

def test_api(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',str(tmp_path/'api.db'))
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with TestClient(app) as c:
        assert c.get('/health').status_code==200
        assert c.get('/jobs').json()['total']==0
        assert c.get('/jobs?limit=0').status_code==422
        assert c.post('/recommend',json={'profile':'Python'}).status_code==400
        assert c.post('/recommend',json={'profile':'Python','consent':True}).status_code==503
