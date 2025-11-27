from django.db import models

class Recipe(models.Model):
    name = models.CharField(max_length=200, unique=True)
    prep_time = models.PositiveIntegerField()  # в минутах
    instructions = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Ingredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='ingredients', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    amount = models.CharField(max_length=100)

    class Meta:
        unique_together = ('recipe', 'name')  # нельзя добавить два раза "Соль" к одному рецепту
