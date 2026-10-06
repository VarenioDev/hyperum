"""Проверка, что все схемы импортируются."""
from backend.models import *
print("Все схемы импортированы успешно")

# Проверим JSON-схему одной модели
from backend.models import TaskResponse
import json
schema = TaskResponse.model_json_schema()
print(json.dumps(schema, indent=2, ensure_ascii=False)[:500])