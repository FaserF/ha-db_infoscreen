with open("tests/test_translations.py", "r") as f:
    content = f.read()

content = content.replace("async def test_extra_translation_sections", "def test_extra_translation_sections")
content = content.replace("async def test_all_translation_keys_referenced", "def test_all_translation_keys_referenced")
content = content.replace("async def test_translation_schema_compliance", "def test_translation_schema_compliance")


with open("tests/test_translations.py", "w") as f:
    f.write(content)
