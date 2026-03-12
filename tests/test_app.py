# tests/test_app.py
import json
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_get_expenses(client):
    resp = client.get("/expenses")
    assert resp.status_code == 200
    assert isinstance(resp.json, list)

def test_submit_expense_missing_fields(client):
    resp = client.post("/submit-expense", data={})
    assert resp.status_code == 400
    assert "error" in resp.json

def test_delete_expense_not_found(client):
    resp = client.delete("/expense/non-existent-id")
    assert resp.status_code == 404
    assert "error" in resp.json