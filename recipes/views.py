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
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
import json

@require_http_methods(["POST"])
def edit_recipe(request, recipe_id):
    try:
        recipe = Recipe.objects.get(id=recipe_id)
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        prep_time = data.get('prep_time')
        instructions = data.get('instructions', '').strip()

        if not name or not instructions or not prep_time:
            return JsonResponse({'error': 'Все поля обязательны'}, status=400)

        if Recipe.objects.filter(name=name).exclude(id=recipe_id).exists():
            return JsonResponse({'error': 'Рецепт с таким названием уже существует'}, status=400)

        recipe.name = name
        recipe.prep_time = int(prep_time)
        recipe.instructions = instructions
        recipe.save()

        # Обновляем ингредиенты (просто заменяем)
        recipe.ingredients.all().delete()
        ingredients = data.get('ingredients', [])
        for ing in ingredients:
            if ing.get('name') and ing.get('amount'):
                Ingredient.objects.create(
                    recipe=recipe,
                    name=ing['name'],
                    amount=ing['amount']
                )

        return JsonResponse({'success': True})
    except Recipe.DoesNotExist:
        return JsonResponse({'error': 'Рецепт не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["POST"])
def delete_recipe(request, recipe_id):
    try:
        Recipe.objects.get(id=recipe_id).delete()
        return JsonResponse({'success': True})
    except Recipe.DoesNotExist:
        return JsonResponse({'error': 'Рецепт не найден'}, status=404)

def search_recipes(request):
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'results': []})
    recipes = Recipe.objects.filter(
        models.Q(name__icontains=query) | models.Q(instructions__icontains=query)
    )[:10]
    results = [
        {
            'id': r.id,
            'name': r.name,
            'prep_time': r.prep_time,
            'instructions': r.instructions,
            'ingredients': [{'name': i.name, 'amount': i.amount} for i in r.ingredients.all()]
        }
        for r in recipes
    ]
    return JsonResponse({'results': results})

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