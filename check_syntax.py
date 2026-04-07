with open('backend/stock/turtle_strategy.py', 'r') as f:
    content = f.read()
try:
    compile(content, 'backend/stock/turtle_strategy.py', 'exec')
    print('Syntax OK')
except SyntaxError as e:
    print(f'Syntax Error: {e}')
    print(f'Line {e.lineno}: {e.text}')