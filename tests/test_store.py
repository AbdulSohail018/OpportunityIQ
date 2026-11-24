import pytest
from backend import store

@pytest.fixture(autouse=True)
def isolated_database(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',str(tmp_path/'test.db'))

def job(id='1',title='Python Engineer'):
    return store.normalize(title,'Test fixture','Remote','Python SQL','https://example.org/jobs/'+id,'greenhouse',id,board='fixture')

def test_empty():
    assert store.search()['total']==0

def test_search():
    store.upsert([job()])
    assert store.search('Python')['total']==1
    assert store.search('unrelated')['total']==0

def test_deduplication():
    store.upsert([job(),job()])
    assert store.search()['total']==1

def test_refresh_removes_expired():
    store.refresh_board('greenhouse','fixture','Test fixture',[job(),job('2')])
    store.refresh_board('greenhouse','fixture','Test fixture',[job()])
    assert store.search()['total']==1

def test_failed_refresh_preserves_records():
    store.refresh_board('greenhouse','fixture','Test fixture',[job()])
    store.source_failure('greenhouse','fixture','Test fixture',RuntimeError('network failure'))
    assert store.search()['total']==1
    assert store.sources()[0]['status']=='error'

def test_matching():
    store.upsert([job()])
    j=store.search(profile='Python')['jobs'][0]
    assert j['match_score']==50
    assert j['matched_skills']==['python']

def test_remote():
    store.upsert([job()])
    assert store.search(remote=True)['total']==1

def test_invalid_url():
    with pytest.raises(ValueError):
        store.normalize('Title','Company','','','javascript:alert(1)','lever','1')

def test_pagination():
    store.upsert([job('1'),job('2')])
    assert len(store.search(page=2,limit=1)['jobs'])==1
