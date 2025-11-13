from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from .forms import RecipeForm
from .utils import (
    validate_xml, save_recipe_as_xml,
    load_xml_files, sanitize_filename
)
import xml.etree.ElementTree as ET
import os
from django.conf import settings

def index(request):
    # Обработка формы "Добавить рецепт"
    if request.method == 'POST' and 'format' in request.POST:
        form = RecipeForm(request.POST)
        if form.is_valid():
            # Получаем данные из формы
            name = form.cleaned_data['name']
            prep_time = form.cleaned_data['prep_time']
            instructions = form.cleaned_data['instructions']
            ingredients_text = form.cleaned_data['ingredients']
            # Парсим ингредиенты
            ingredients = [
                {"name": part.split(",", 1)[0].strip(), "amount": part.split(",", 1)[1].strip()}
                for part in ingredients_text.splitlines()
                if part.strip()
            ]

            # Подготовим данные для сохранения
            recipe_data = {
                "name": name,
                "prep_time": prep_time,
                "instructions": instructions,
                "ingredients": ingredients
            }

            # Генерируем безопасное имя файла и сохраняем как XML
            filename = sanitize_filename("recipe.xml")
            save_recipe_as_xml(recipe_data, filename)

            # Уведомление об успехе
            messages.success(request, f"Рецепт '{name}' сохранен в XML")
            return HttpResponseRedirect(reverse('index'))
    # Обработка загрузки XML-файла
    elif request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        # Проверяем расширение файла
        if not uploaded_file.name.lower().endswith('.xml'):
            messages.error(request, "Разрешены только XML файлы.")
            return HttpResponseRedirect(reverse('index'))

        # Генерируем безопасное имя файла
        filename = sanitize_filename(uploaded_file.name)
        filepath = os.path.join(settings.MEDIA_ROOT, 'xml', filename)

        # Сохраняем файл
        with open(filepath, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Проверяем валидность XML
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            is_valid = validate_xml(root)
        except ET.ParseError:
            is_valid = False

        if not is_valid:
            os.remove(filepath)  # Удаляем невалидный файл
            messages.error(request, f"Файл {filename} не прошёл валидацию и был удалён.")
        else:
            messages.success(request, f"Файл {filename} успешно загружен и проверен.")

        return HttpResponseRedirect(reverse('index'))
    else:
        # GET-запрос — отображаем форму
        form = RecipeForm()

    # Загружаем все XML-рецепты
    xml_recipes = load_xml_files()

    # Отображаем шаблон с формой и рецептами
    return render(request, 'index.html', {
        'form': form,
        'recipes': xml_recipes
    })