import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.main import app
from src.rag import initialize_rag_from_docs


@pytest.fixture(scope="session", autouse=True)
def initialize_rag_for_tests():
    initialize_rag_from_docs()


@pytest.fixture
def client():
    return TestClient(app)


def test_search_existing(client):
    response = client.post('/search', json={'query': 'Эндпоинт для создания новой задачи для пользователя'})
    assert response.status_code == 200
    data = response.json()
    assert data['found'] is True
    assert 'POST /api/v1/tasks' in data['content']


def test_search_not_found(client):
    with patch('app.main.search_documentation', return_value=None):
        response = client.post('/search', json={'query': 'любой запрос'})
        assert response.status_code == 200
        data = response.json()
        assert data['found'] is False
        assert 'Документация не найдена' in data['message']


def test_generate_new(client):
    query = 'Поиск по ключевым словам'

    search_resp = client.post('/search', json={'query': query})
    assert search_resp.json()['found'] is False

    with patch('app.main.save_document') as mock_save:
        mock_save.return_value = 'docs/test_search.md'

        # Генерация
        gen_resp = client.post('/generate', json={'query': query})
        assert gen_resp.status_code == 200
        data = gen_resp.json()
        assert data['success'] is True
        assert data['content'].startswith('###')
        assert data['file_path'] == 'docs/test_search.md'
        mock_save.assert_called_once()


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert 'status' in data
    assert 'checks' in data