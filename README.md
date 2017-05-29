# Optimising Django Queries

Django ORM basics, with some tips and tricks, for writing optimal queries.

## Getting Started

### Setup

Make sure you have python 3.6 installed, and is the default python3 on your
system. There's a docker-compose file included for running postgres in a docker
container if you don't want to install postgres locally.

Make sure you edit the `DATABASES` setting in `shop/shop/settings.py` if you
aren't running `postgres` using `Docker Toolbelt for OSX`.

```bash
xcode-select --install  # OSX only - skip if xcode is already installed
docker-compose up -d db

pip install pipenv
git clone git@github.com:jarshwah/optimising-django-queries.git
cd optimising-django-queries
pipenv --three install
pipenv shell  # activates the virtual environment
cd shop
./manage.py migrate
```

The above commands will install all the dependencies needed,

### Query Logging

When developing it's a good idea to have logging configured so that queries
are printed to the console. A neverending stream of SQL queries in your
terminal is your first hint that you might have some performance issues.

Below is an extremely minimal config you can add (or merge) into your settings
file:

```python
DEBUG = True
LOGGING = {
    'version': 1,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}
```

You can also inspect previously executed queries directly from the django
shell, provided you've set `DEBUG = True` in your settings file. Django will
only remember 9000 queries to avoid memory issues.

```python
In [1]: from django.db import connection, reset_queries

In [2]: print(connection.queries)
[
    {
        'sql': 'SELECT "shop_product"."id", "shop_product"."name", "shop_product"."category_id", "shop_product"."price" FROM "shop_product" ORDER BY "shop_product"."id" ASC LIMIT 1',
        'time': '0.001'
    }
]
In [3]: reset_queries()

In [4]: print(connection.queries)
[]
```

## Database Relations

The Django ORM (Object-Relational Mapper) is an abstraction that uses python
objects to represent database tables and the relations between them.

### Foreign Keys

Foreign Keys are the primary way of defining how two tables are related. They
provide a link from one table to the key of another table. These kind of
relationships are commonly called Many-To-One (M-1) because there are Many
products that map to One Category.

Product

| id        | name            | category_id |
|:----------|:----------------|:------------|
| 1         | Samsung 65 inch | 1           |
| 2         | Samsung 75 inch | 1           |
| 3         | Juicer          | 2           |

Category

| id        | name        |
|:----------|:------------|
| 1         | TVs         |
| 2         | Homeware    |

In the tables above, you can see that product with `id = 3` is a `Juicer`, in
the `category` with `id = 2`. The data is `related` by the `category_id`
foreign key pointing to the `id` field in the `Category` table.

The SQL to retrieve the `Juicer` with it's `category` would be something like:

```sql
SELECT product.id,
       product.name,
       category.id,
       category.name
  FROM product
  JOIN category
    ON product.category_id = category.id
 WHERE product.name = 'Juicer';

 1 | Juicer | 2 | Homeware
```

The equivalent `python` code would be:

```python
>>> product = Product.objects.get(name='Juicer')
>>> print(product.id, product.name, product.category.id, product.category.name)

1 Juicer 2 Homeware
```

You can see that accessing a foreign key in python is equivalent to accessing
an attribute or property.

### Multivalue Relations

It's also possible to start from `Category` and find all linked `Products`. But
since we represent data as rows, and a `Category` can have multiple `Products`
it means we'll end up repeating the same category multiple times.

```sql
SELECT category.id
       category.name
       product.name
  FROM category
  JOIN product
    ON category.id = product.category_id
 WHERE category.name = 'TVs'

1 | TVs  | Samsung 65 inch
1 | TVs  | Samsung 75 inch
```

This is a multivalue relation, as there are multiple links between a category
and the products within that category. This is sometimes referred to as a
One-To-Many (1-M) relationship.

Since Django wants to avoid returning duplicate data, it represents multivalue
relations as `lists`.

```python
>>> category = Category.objects.get(name='TVs')
>>> print(category.id, category.name)

1 TVs

>>> for product in category.product_set.all():
...     print(product.name)

Samsung 65 inch
Samsung 75 inch
```

### Many To Many Relations

There's a third type of relationship in a database called Many To Many (M-M),
which models multiple rows in a table linking to multiple rows in another
table. This is really just a special case of Multivalue relationships, with
an extra table inbetween the two for tracking the links.

Consider a Product table and a Size table, where multiple products will share
similar sizing.

Product

| id        | name   |
|:----------|:-------|
| 1         | Jumper |
| 2         | Tshirt |

Size

| id        | name     |
|:----------|:---------|
| 1         | Small    |
| 2         | Large    |

Product Size

| id        | product_id | size_id |
|:----------|:-----------|:---------
| 1         | 1          | 1       |
| 2         | 2          | 1       |
| 3         | 1          | 2       |

```sql
SELECT product.name
       size.name
  FROM product
  JOIN productsize
    ON product.id = productsize.product_id
  JOIN size
    ON productsize.size_id = size.id

Jumper Small
Jumper Large
Tshirt Small
```

The django ORM hides the `ProductSize` mapping table (through relation) by
default, but it's possible to define it yourself. For a many-to-many relation,
django models both sides as lists.

```python
>>> product = Product.objects.get(name='Jumper')
>>> for size in product.size_set.all():
...     print(size.name)

Small
Large

>>> size = Size.objects.get(name='Large')
>>> for product in size.product_set.all():
...     print(product.name)

Jumper
```

## ORM Models

Django models represent database tables as classes, rows as instances of those
classes, and fields as attributes.

Here we'll see three models, with the relationships between them defined as
fields.

```python

class Category(models.Model):
    name = models.CharField(max_length=32)

class Feature(models.Model):
    name = models.CharField(max_length=32)
    value = models.CharField(max_length=32)
    visible = models.BooleanField(default=True)

class Product(models.Model):
    name = models.CharField(max_length=32)
    category = models.ForeignKey(Category)
    features = models.ManyToManyField(Feature)
    price = models.DecimalField(max_digits=6, decimal_places=2)

```

`Product` is the interesting model here, as it has both a `ForeignKey` field
pointing to `Category`, and a `ManyToMany` field pointing to multiple
`Features`.

### Foreign Key

As we learned before, foreign keys are represented with simple attribute
access. Given a `product`, we access the category via the `product.category`
field.

But what is Django doing to get the data from the database? How many queries
does it need to fetch both `product` and `product.category`? In our examples
above, we seen that all of this data can be generated with a single SQL query.

If we turn on SQL logging (see above), we can see the queries being executed
as we work.

```python
In [24]: product = Product.objects.get(pk=1)
(0.001)
SELECT "shop_product"."id", "shop_product"."name", "shop_product"."category_id", "shop_product"."price"
FROM "shop_product"
WHERE "shop_product"."id" = 1

In [25]: category = product.category
(0.001)
SELECT "shop_category"."id", "shop_category"."name"
FROM "shop_category"
WHERE "shop_category"."id" = 2
```

Django fetches data linked by `ForeignKey` *on-demand*. The main reason for
doing this, is that you could have an extremely deep hierarchy of ForeignKeys,
but you probably wouldn't want Django to pull of that data back.

But there *is* a way to be explicit, and tell Django which relations it should
fetch *eagerly*.

#### Select Related

If you want Django to join the data via SQL and return it in a single query,
you can use [select_related()](https://docs.djangoproject.com/en/1.11/ref/models/querysets/#select-related).

```python
In [26]: product = Product.objects.select_related('category').get(pk=1)
(0.001)
SELECT
"shop_product"."id", "shop_product"."name", "shop_product"."category_id", "shop_product"."price", "shop_category"."id", "shop_category"."name"
FROM "shop_product"
INNER JOIN "shop_category" ON ("shop_product"."category_id" = "shop_category"."id")
WHERE "shop_product"."id" = 1;

In [27]: category = product.category

```
