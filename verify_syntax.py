import ast
import traceback

file_path = "c:\\Users\\fseitz\\GitHub\\ha-db_infoscreen\\custom_components\\db_infoscreen\\__init__.py"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    ast.parse(content)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax Error detected: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"Other Error: {e}")
    traceback.print_exc()
