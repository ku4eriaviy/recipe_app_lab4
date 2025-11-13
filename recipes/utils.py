import xml.etree.ElementTree as ET
import os
import uuid
from django.conf import settings

def validate_xml(root):
    """
    Проверяет, соответствует ли XML-документ структуре рецепта.
    Возвращает True, если валиден, иначе False.
    """
    try:
        assert root.tag == 'recipe'
        assert root.find('name') is not None
        assert root.find('ingredients') is not None
        assert root.find('instructions') is not None
        assert root.find('prep_time') is not None
        prep_time = int(root.find('prep_time').text)
        return True
    except (AssertionError, ValueError, AttributeError):
        return False

def save_recipe_as_xml(recipe_data, filename):
    """
    Сохраняет рецепт в формате XML по заданному пути.
    """
    import xml.etree.ElementTree as ET
    root = ET.Element("recipe")
    ET.SubElement(root, "name").text = recipe_data['name']
    ET.SubElement(root, "prep_time").text = str(recipe_data['prep_time'])
    ET.SubElement(root, "instructions").text = recipe_data['instructions']
    ingredients_el = ET.SubElement(root, "ingredients")
    for ing in recipe_data['ingredients']:
        el = ET.SubElement(ingredients_el, "ingredient", name=ing['name'], amount=ing['amount'])
    tree = ET.ElementTree(root)
    filepath = os.path.join(settings.MEDIA_ROOT, 'xml', filename)
    tree.write(filepath, encoding='utf-8', xml_declaration=True)

def load_xml_files():
    """
    Загружает и парсит все XML-файлы из папки uploads/xml.
    Возвращает список словарей с данными рецептов.
    """
    folder = os.path.join(settings.MEDIA_ROOT, 'xml')
    files = []
    for f in os.listdir(folder):
        if f.endswith('.xml'):
            filepath = os.path.join(folder, f)
            try:
                tree = ET.parse(filepath)
                root = tree.getroot()
                recipe = {
                    'name': root.find('name').text,
                    'prep_time': int(root.find('prep_time').text),
                    'instructions': root.find('instructions').text,
                    'ingredients': [
                        {'name': el.attrib['name'], 'amount': el.attrib['amount']}
                        for el in root.find('ingredients')
                    ]
                }
                files.append(recipe)
            except ET.ParseError:
                # Игнорировать битые XML-файлы
                pass
    return files

def sanitize_filename(filename):
    """
    Безопасно генерирует уникальное имя файла.
    """
    ext = os.path.splitext(filename)[1]
    unique_name = f"{uuid.uuid4()}{ext}"
    return unique_name