from django.db import models
from django.utils.functional import cached_property as buffered_property
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=32)

    def __str__(self):
        return self.name


class Feature(models.Model):
    name = models.CharField(max_length=32)
    value = models.CharField(max_length=32)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} = {self.value}'


class Product(models.Model):
    name = models.CharField(max_length=32)
    category = models.ForeignKey(Category)
    features = models.ManyToManyField(Feature)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return self.name

    @buffered_property
    def all_features(self):
        return list(self.features.all())

    @property
    def visible_features_python(self):
        return [feature for feature in self.all_features if feature.visible]

    @property
    def invisible_features_python(self):
        return [feature for feature in self.all_features if not feature.visible]

    @property
    def visible_features_database(self):
        return self.features.filter(visible=True)

    @property
    def invisible_features_database(self):
        return self.features.filter(visible=False)


class Sale(models.Model):
    product = models.ForeignKey(Product)
    sale_date = models.DateTimeField(default=timezone.now)
