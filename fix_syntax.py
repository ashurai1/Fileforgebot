import re

for filepath in ['bot/handlers/start_handler.py', 'bot/handlers/conversion_handlers.py']:
    with open(filepath, 'r') as f:
        content = f.read()

    # Fix the unpacking bug: <b>merge_files</b> -> *merge_files
    content = content.replace('<b>merge_files</b>', '*merge_files')
    content = content.replace('<b>pages</b>', '*pages')
    content = content.replace('<b>paths</b>', '*paths')

    # Fix the warnings: \., \-, \!, \(, \) in regular strings (which are now HTML)
    content = content.replace('\\.', '.')
    content = content.replace('\\-', '-')
    content = content.replace('\\!', '!')
    content = content.replace('\\(', '(')
    content = content.replace('\\)', ')')

    with open(filepath, 'w') as f:
        f.write(content)

print("Fixed Syntax Errors.")
