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

def search_recipes(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    from django.db.models import Q
    recipes = Recipe.objects.filter(
        Q(name__icontains=query) | Q(instructions__icontains=query)
    )[:10]
    results = []
    for r in recipes:
        results.append({
            'id': r.id,
            'name': r.name,
            'prep_time': r.prep_time,
            'instructions': r.instructions,
            'ingredients': [{'name': i.name, 'amount': i.amount} for i in r.ingredients.all()]
        })
    return JsonResponse({'results': results})

@require_http_methods(["POST"])
def delete_recipe(request, recipe_id):
    try:
        Recipe.objects.get(id=recipe_id).delete()
        return JsonResponse({'success': True})
    except Recipe.DoesNotExist:
        return JsonResponse({'error': 'Рецепт не найден'}, status=404)

def index(request):
    if request.method == 'POST':
        # Сохранение через форму
        if 'save_target' in request.POST:
            form = RecipeForm(request.POST)
            if form.is_valid():
                name = form.cleaned_data['name']
                prep_time = form.cleaned_data['prep_time']
                instructions = form.cleaned_data['instructions']
                ingredients_text = form.cleaned_data['ingredients']
                ingredients = [
                    {"name": part.split(",", 1)[0].strip(), "amount": part.split(",", 1)[1].strip()}
                    for part in ingredients_text.splitlines() if part.strip()
                ]

                save_target = request.POST.get('save_target', 'file')
                recipe_data = {"name": name, "prep_time": prep_time, "instructions": instructions, "ingredients": ingredients}

                if save_target == 'db':
                    if Recipe.objects.filter(name=name).exists():
                        messages.warning(request, f"Рецепт '{name}' уже существует в базе данных.")
                    else:
                        recipe_obj = Recipe.objects.create(name=name, prep_time=prep_time, instructions=instructions)
                        for ing in ingredients:
                            Ingredient.objects.create(recipe=recipe_obj, name=ing['name'], amount=ing['amount'])
                        messages.success(request, f"Рецепт '{name}' сохранён в базу данных")
                else:
                    filename = sanitize_filename("recipe.xml")
                    save_recipe_as_xml(recipe_data, filename)
                    messages.success(request, f"Рецепт '{name}' сохранён в XML-файл")
                return HttpResponseRedirect(reverse('index'))

        # Загрузка XML
        elif request.FILES.get('file'):
            # ... (оставьте ваш существующий код загрузки XML без изменений)
            uploaded_file = request.FILES['file']
            if not uploaded_file.name.lower().endswith('.xml'):
                messages.error(request, "Разрешены только XML файлы.")
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

    # GET: выбор источника
    source = request.GET.get('source', 'files')
    form = RecipeForm()

    if source == 'db':
        db_recipes = Recipe.objects.prefetch_related('ingredients').all()
        recipes = []
        for r in db_recipes:
            recipes.append({
                'id': r.id,
                'name': r.name,
                'prep_time': r.prep_time,
                'instructions': r.instructions,
                'ingredients': [{'name': i.name, 'amount': i.amount} for i in r.ingredients.all()]
            })
    else:
        recipes = load_xml_files()
        for r in recipes:
            r['id'] = None

    return render(request, 'index.html', {
        'form': form,
        'recipes': recipes,
        'source': source
    })