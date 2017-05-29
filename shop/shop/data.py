import random

from faker import Faker
from django.utils import timezone


def create_initial_data(apps, schema_editor):
    Category = apps.get_model('shop', 'Category')
    Feature = apps.get_model('shop', 'Feature')
    Product = apps.get_model('shop', 'Product')
    Sale = apps.get_model('shop', 'Sale')

    fake = Faker()

    categories = [
        Category(name='Mens'),
        Category(name='Womens'),
        Category(name='Kids')
    ]
    categories = Category.objects.bulk_create(categories)

    features = [
        Feature(name='Size', value='XS'),
        Feature(name='Size', value='S'),
        Feature(name='Size', value='M'),
        Feature(name='Size', value='L'),
        Feature(name='Size', value='XL'),
    ]
    for _ in range(30):
        features.append(
            Feature(
                name='Colour',
                value=fake.color_name(),
                visible=fake.boolean(chance_of_getting_true=70)
            )
        )
    features = Feature.objects.bulk_create(features)

    products = []
    for _ in range(30):
        products.append(
            Product(
                name=fake.company(),
                category=random.choice(categories),
                price=fake.pydecimal(left_digits=3, right_digits=2, positive=True),
            )
        )
    products = Product.objects.bulk_create(products)

    for product in products:
        product.features.add(*set(random.choices(features, k=10)))

    sales = []
    for _ in range(1000):
        sales.append(
            Sale(
                product=random.choice(products),
                sale_date=fake.date_time_this_year(before_now=True, after_now=False, tzinfo=timezone.utc)
            )
        )
    Sale.objects.bulk_create(sales)
