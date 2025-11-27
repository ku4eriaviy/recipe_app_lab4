# recipes/views.py

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.db import models
from .forms import RecipeForm
from .utils import validate_xml, save_recipe_as_xml, load_xml_files, sanitize_filename
from .models import Recipe, Ingredient
import xml.etree.ElementTree as ET
import os
from django.conf import settings

def index(request):
    if request.method == 'POST':
        # Сценарий 1: Сохранение через форму
        if 'save_target' in request.POST:
            form = RecipeForm(request.POST)
            if form.is_valid():
                name = form.cleaned_data['name']
                prep_time = form.cleaned_data['prep_time']
                instructions = form.cleaned_data['instructions']
                ingredients_text = form.cleaned_data['ingredients']
                ingredients = [
                    {"name": part.split(",", 1)[0].strip(), "amount": part.split(",", 1)[1].strip()}
                    for part in ingredients_text.splitlines()
                    if part.strip()
                ]

                save_target = request.POST.get('save_target', 'file')

                if save_target == 'db':
                    if Recipe.objects.filter(name=name).exists():
                        messages.warning(request, f"Рецепт '{name}' уже существует в базе данных.")
                    else:
                        recipe_obj = Recipe.objects.create(
                            name=name,
                            prep_time=prep_time,
                            instructions=instructions
                        )
                        for ing in ingredients:
                            Ingredient.objects.create(
                                recipe=recipe_obj,
                                name=ing['name'],
                                amount=ing['amount']
                            )
                        messages.success(request, f"Рецепт '{name}' сохранён в базу данных")
                else:
                    # Сохранение в XML-файл
                    recipe_data = {
                        "name": name,
                        "prep_time": prep_time,
                        "instructions": instructions,
                        "ingredients": ingredients
                    }
                    filename = sanitize_filename("recipe.xml")
                    save_recipe_as_xml(recipe_data, filename)
                    messages.success(request, f"Рецепт '{name}' сохранён в XML-файл")

                return HttpResponseRedirect(reverse('index'))

        # Сценарий 2: Загрузка XML-файла
        elif request.FILES.get('file'):
            uploaded_file = request.FILES['file']
            if not uploaded_file.name.lower().endswith('.xml'):
                messages.error(request, "Разрешены только XML-файлы.")
                return HttpResponseRedirect(reverse('index'))

            filename = sanitize_filename(uploaded_file.name)
            filepath = os.path.join(settings.MEDIA_ROOT, 'xml', filename)

            with open(filepath, 'wb+') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            try:
                tree = ET.parse(filepath)
                root = tree.getroot()
                is_valid = validate_xml(root)
            except ET.ParseError:
                is_valid = False

            if not is_valid:
                os.remove(filepath)
                messages.error(request, f"Файл {filename} не прошёл валидацию и был удалён.")
            else:
                messages.success(request, f"Файл {filename} успешно загружен и проверен.")

            return HttpResponseRedirect(reverse('index'))

    # GET-запрос: отображение страницы
    form = RecipeForm()
    xml_recipes = load_xml_files()
    return render(request, 'index.html', {
        'form': form,
        'recipes': xml_recipes,
        'source': 'files'
    })