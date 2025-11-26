with open('documents/phd_seas.txt', 'r', encoding='utf-8') as f:
    content = f.read()

normalized = content.replace('  ', ' ')

with open('documents/phd_seas.txt', 'w', encoding='utf-8') as f:
    f.write(normalized)

print("Successfully normalized double spaces to single spaces")
