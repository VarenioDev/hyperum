"""Check that normalized formulas occur in one of the original representations.

This is a conservative textual audit, not a mathematical equivalence proof.
"""
import json
from pathlib import Path
import re
import sys


def canonical(value):
    replacements = [(r'\leqslant', '<='), (r'\geqslant', '>='), (r'\leq', '<='),
                    (r'\geq', '>='), (r'\neq', '!='), (r'\le', '<='), (r'\ge', '>='),
                    (r'\lt', '<'), (r'\gt', '>'), (r'\times', '*'), (r'\cdot', '*'),
                    (r'\%', '%'), ('≤', '<='), ('≥', '>='), ('⩽', '<='), ('⩾', '>='),
                    ('≠', '!='), ('−', '-'), ('–', '-'), ('×', '*'), ('⋅', '*'),
                    ('·', '*'), ('∗', '*'), (r'\,', ''), (r'\ ', '')]
    for source, target in replacements:
        value = value.replace(source, target)
    value = re.sub(r'\\(?:left|right|displaystyle)\b', '', value)
    return re.sub(r'[\s{}$\u200b]', '', value)


def unmatched_formulas(original, candidate):
    unmatched = []
    for match in re.finditer(r'\$\$([\s\S]*?)\$\$|(?<!\$)\$([^$\n]+)\$(?!\$)', candidate):
        formula = match.group(1) or match.group(2)
        if canonical(formula) not in canonical(original):
            unmatched.append(formula)
    return unmatched


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    report = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    for task in report['tasks']:
        if task.get('error'):
            continue
        unmatched = unmatched_formulas(task['original_text'], task['normalized_text'])
        for formula in unmatched:
            print(task['code'], repr(formula))
