import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Replace parse_mode="MarkdownV2" with parse_mode="HTML"
    content = content.replace('parse_mode="MarkdownV2"', 'parse_mode="HTML"')
    
    # We need to replace *bold* with <b>bold</b>. 
    # A simple regex for *text* where text doesn't contain *
    content = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', content)
    
    # Remove all the escaped characters like \\., \\!, \\-, \\( \\)
    content = content.replace('\\.', '.')
    content = content.replace('\\!', '!')
    content = content.replace('\\-', '-')
    content = content.replace('\\(', '(')
    content = content.replace('\\)', ')')

    with open(filepath, 'w') as f:
        f.write(content)

fix_file('bot/handlers/start_handler.py')
fix_file('bot/handlers/conversion_handlers.py')
print("Fixed Markdown to HTML.")
