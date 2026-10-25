with open("tests/test_translations.py", "r") as f:
    content = f.read()

content = content.replace("def test_extra_translation_sections", "async def test_extra_translation_sections")
content = content.replace("def test_all_translation_keys_referenced", "async def test_all_translation_keys_referenced")
content = content.replace("def test_translation_schema_compliance", "async def test_translation_schema_compliance")

with open("tests/test_translations.py", "w") as f:
    f.write(content)

