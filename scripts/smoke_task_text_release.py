"""Public production smoke test using a synthetic guest (no real student data)."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://hyperum.polyum.ru'


def main():
    session = requests.Session()
    page = session.get(BASE + '/', timeout=(120, 30))
    page.raise_for_status()
    assert hashlib.sha256(page.content).hexdigest() == hashlib.sha256((ROOT / 'pwa/dist/index.html').read_bytes()).hexdigest()
    assets = re.findall(r'(?:src|href)="/([^"?]+\.(?:js|css))"', page.text)
    assert any(asset.startswith('assets/') for asset in assets)
    for file in [*assets, 'sw.js', 'fonts/MontserratAlternates-Regular.woff2']:
        response = session.get(BASE + '/' + file, timeout=(120, 30))
        response.raise_for_status()
        assert len(response.content) > 100
    auth = session.get(BASE + '/api/v1/auth/me', timeout=(120, 30))
    assert auth.status_code == 401
    response = session.post(BASE + '/api/v1/demo/start', json={
        'description': 'Хочу потренировать рекурсию: понимаю базовые условия функций, но путаюсь в рекурсивных вызовах и вычислении F(n).'
    }, timeout=(120, 180))
    response.raise_for_status()
    result = response.json()
    with (ROOT / 'data/task_normalization/vps-bank/verified.csv').open(encoding='utf-8-sig', newline='') as stream:
        expected = {row['code']: row for row in csv.DictReader(stream)}
    assert result['total_tasks'] == len(result['tasks']) and result['tasks']
    for task in result['tasks']:
        assert task['text'] == expected[task['code']]['text']
        assert task['task_id'] == expected[task['code']]['id']
    output = ROOT / 'data/task_normalization/vps-bank/production-smoke.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'index_matches_build': True, 'assets_ok': True,
                      'auth_status': auth.status_code, 'demo_tasks': len(result['tasks']),
                      'topic': result['topic'], 'texts_match_verified_csv': True}, ensure_ascii=False))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
