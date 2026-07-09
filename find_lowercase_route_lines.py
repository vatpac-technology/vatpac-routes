from pathlib import Path
import re

file_path = Path('latest_routes.json')
text = file_path.read_text(encoding='utf-8')
lines = text.splitlines()

pattern = re.compile(r'"route"\s*:\s*"(?P<value>[^"]*)"')

for idx, line in enumerate(lines, start=1):
    match = pattern.search(line)
    if match:
        value = match.group('value')
        if any(ch.islower() for ch in value):
            print(f'{idx}: {line.strip()}')
