from django import forms

class RecipeForm(forms.Form):
    name = forms.CharField(max_length=200, label="Название")
    prep_time = forms.IntegerField(min_value=1, label="Время приготовления (мин)")
    instructions = forms.CharField(widget=forms.Textarea, label="Инструкции")
    ingredients = forms.CharField(
        widget=forms.Textarea,
        help_text="Введите ингредиенты по одному в строке в формате: Название,Количество",
        label="Ингредиенты"
    )