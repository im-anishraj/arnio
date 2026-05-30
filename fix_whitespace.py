import re
for f in ['tests/test_register_validator.py', 'arnio/schema.py']:
    with open(f, 'r') as file:
        content = file.read()
    cleaned = re.sub(r'[ \t]+\n', '\n', content)
    with open(f, 'w') as file:
        file.write(cleaned)
print('Done!')
