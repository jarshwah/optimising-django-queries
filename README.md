# Optimising Django Queries

Django ORM basics, with some tips and tricks, for writing optimal queries.

## [](#getting-started)Getting Started

### [](#setup)Setup

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

The above commands will install all the dependencies needed.

### [](#query-logging)Query Logging

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

## [](#database-relations)Database Relations

The Django ORM (Object-Relational Mapper) is an abstraction that uses python
objects to represent database tables and the relations between them.

### [](#foreign-key-columns)Foreign Keys

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

### [](#multivalue-relations)Multivalue Relations

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

### [](#m2m-relations)Many To Many Relations

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
>>> for size in product.sizes.all():
...     print(size.name)

Small
Large

>>> size = Size.objects.get(name='Large')
>>> for product in size.product_set.all():
...     print(product.name)

Jumper
```

## [](#orm-models)ORM Models

Django models represent database tables as classes, rows as instances of those
classes, and columns as attributes.

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

### [](#foreign-key-field)ForeignKey

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
but you probably wouldn't want Django to pull all of that data back.

But there *is* a way to be explicit, and tell Django which relations it should
fetch *eagerly*.

#### [](#select-related)Select Related

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

Here we see that, indeed, a single query is executed to retrieve the product
and the category.

### [](#n-plus-1)1 + N queries

You might have heard the term `1 + N` or `N + 1` queries. It's a common
pitfall when using ORMs to retrieve data from a database.

Let's say we have 3 products, and we want to show the product name and the
category it came from. First, we'll do it the naive way:

```python
In [27]: for p in Product.objects.all():
   ...:     print(p.name, p.category.name)
   ...:
(0.001) SELECT
    "shop_product"."id", "shop_product"."name",
    "shop_product"."category_id", "shop_product"."price"
FROM "shop_product";
(0.000) SELECT
    "shop_category"."id", "shop_category"."name"
FROM "shop_category"
WHERE "shop_category"."id" = 1;

Samsung 65 inch TVs

(0.001) SELECT "shop_category"."id", "shop_category"."name"
FROM "shop_category" WHERE "shop_category"."id" = 1;

Samsung 75 inch TVs

(0.000) SELECT "shop_category"."id", "shop_category"."name"
FROM "shop_category" WHERE "shop_category"."id" = 2;

Juicer Homeware
```

We executed a single query (1) for the product, then we executed an extra query
for each product to get the category (N). This introduces a lot of latency, as
each query is a new network request, and the database has to recompile and
execute lots of very similar queries.

Using `select_related` avoids this issue, allowing data for all Products and
Categories to be retrieved once.

```python
In [28]: for p in Product.objects.select_related('category').all():
   ...:     print(p.name, p.category.name)
   ...:
(0.005) SELECT "shop_product"."id", "shop_product"."name",
"shop_product"."category_id", "shop_product"."price",
"shop_category"."id", "shop_category"."name"
FROM "shop_product"
INNER JOIN "shop_category"
ON ("shop_product"."category_id" = "shop_category"."id");
Samsung 65 inch TVs
Samsung 75 inch TVs
Juicer Homeware
```

### [](#m2m-field)ManyToManyField

`ManyToManyField`'s models a list of data. You generally iterate over many
to many fields. Given a `product`, we access its features via the
`product.features` field.

Remembering that Django tries to avoid returning duplicate data, it must
execute two queries in this instance. One to get the Product, and another to
get the features for that product. Again, with SQL logging activated, we can
see exactly what's happening under the hood.

```python
In [29]: for p in Product.objects.all()[0:3]:
   ...:     print('Product: ', p.name)
   ...:     for f in p.features.all():
   ...:         print(f.name, ': ', f.value)
   ...:     print()
   ...:

(0.001)
SELECT "shop_product"."id", "shop_product"."name", "shop_product"."category_id", "shop_product"."price"
FROM "shop_product";

Product:  Samsung 65 inch

(0.008) SELECT
"shop_feature"."id", "shop_feature"."name", "shop_feature"."value", "shop_feature"."visible"
FROM "shop_feature"
INNER JOIN "shop_product_features"
ON ("shop_feature"."id" = "shop_product_features"."feature_id")
WHERE "shop_product_features"."product_id" = 1 ;

Supplier :  Samsung
Size :  65 inches
Colour :  Black

Product:  Samsung 75 inch
(0.001)
SELECT "shop_feature"."id", "shop_feature"."name", "shop_feature"."value", "shop_feature"."visible"
FROM "shop_feature"
INNER JOIN "shop_product_features"
ON ("shop_feature"."id" = "shop_product_features"."feature_id")
WHERE "shop_product_features"."product_id" = 2;

Supplier :  Samsung
Size :  75 inches
Colour :  Black

Product:  Juicer
(0.001)
SELECT "shop_feature"."id", "shop_feature"."name", "shop_feature"."value", "shop_feature"."visible"
FROM "shop_feature"
INNER JOIN "shop_product_features"
ON ("shop_feature"."id" = "shop_product_features"."feature_id")
WHERE "shop_product_features"."product_id" = 3;

Colour :  LightSeaGreen
Colour :  SpringGreen
Colour :  Azure

```

This is a perfect example of a `1 + N` query. We executed `1` query to fetch
products. Then we issued `1` query for each product `N` to get the features.

Luckily, Django has a way to reduce the number of queries executed when dealing
with lists of related data too.

#### [](#prefetch-related)Prefetch Related

The [prefetch_related()](https://docs.djangoproject.com/en/1.11/ref/models/querysets/#prefetch-related)
queryset method is what Django provides to help minimise the number of queries
required to get the data we need. It's more complicated than `select_related`
but it comes with a lot of power.

We can't actually get the data we need with a single query. But we can do it in
two, which is `1 + 1` queries. One for the product, and then a single query to
fetch all of the features for all of the products.

```python
In [30]: for p in Product.objects.prefetch_related('features').all()[0:3]:
   ...:     print('Product: ', p.name)
   ...:     for f in p.features.all():
   ...:         print(f.name, ': ', f.value)
   ...:     print()
   ...:
(0.001)
SELECT "shop_product"."id", "shop_product"."name", "shop_product"."category_id", "shop_product"."price"
FROM "shop_product";
(0.001)
SELECT
("shop_product_features"."product_id") AS "_prefetch_related_val_product_id", "shop_feature"."id", "shop_feature"."name", "shop_feature"."value", "shop_feature"."visible"
FROM "shop_feature"
INNER JOIN "shop_product_features"
ON ("shop_feature"."id" = "shop_product_features"."feature_id")
WHERE "shop_product_features"."product_id" IN (1, 2, 3);

Product:  Samsung 65 inch
Supplier :  Samsung
Size :  65 inches
Colour :  Black

Product:  Samsung 75 inch
Supplier :  Samsung
Size :  75 inches
Colour :  Black

Product:  Juicer
Colour :  LightSeaGreen
Colour :  SpringGreen
Colour :  Azure
```

Prefetching works by issuing the first query, gathering all of the product
`id`s returned, and then issuing the second query for all features that match
the list of product `id`s. It then uses these features as a cache whenever you
attempt to access `product.features.all()`.

##### [](#prefetch-related-caveats)Prefetch Related Caveats

With great power, comes great responsibility. There are a number of ways to
abuse `prefetch_related`, or to skip using the cache you created and execute
new queries.

**Memory**

Prefetching can end up using quite a bit of memory if there are lots of
relations. If we were querying for 10,000 products, and each product had 10
features, django would first issue a query to features with a `WHERE` clause
containing 10,000 `id`s which is generally not good for a database. But then
it'd return 100,000 features that it would have to keep cached in memory.

**Filtering**

Prefetching only works when you access the many to many field using `.all()`.
But it *is* possible to further filter the many to many field using `.filter()`
and other queryset methods.

```python
In [31]: product = Product.objects.prefetch_related('features').get(pk=1)

(0.001)
SELECT "shop_product"."id", "shop_product"."name", "shop_product"."category_id", "shop_product"."price"
FROM "shop_product"
WHERE "shop_product"."id" = 1; args=(1,)
(0.001)
SELECT ("shop_product_features"."product_id") AS "_prefetch_related_val_product_id", "shop_feature"."id", "shop_feature"."name", "shop_feature"."value", "shop_feature"."visible"
FROM "shop_feature"
INNER JOIN "shop_product_features"
ON ("shop_feature"."id" = "shop_product_features"."feature_id")
WHERE "shop_product_features"."product_id" IN (1);

In [32]: product.features.get(name='Supplier').value

(0.001)
SELECT "shop_feature"."id", "shop_feature"."name", "shop_feature"."value", "shop_feature"."visible"
FROM "shop_feature"
INNER JOIN "shop_product_features" ON ("shop_feature"."id" = "shop_product_features"."feature_id")
WHERE ("shop_product_features"."product_id" = 1 AND "shop_feature"."name" = 'Supplier');

Samsung
```

Our cache isn't able to interpret extra database operations, so django is
forced to execute another query.

**iterator()**

Django provides an [iterator()](https://docs.djangoproject.com/en/1.11/ref/models/querysets/#iterator)
queryset method, which allows django to fetch instances as it iterates through
a loop, rather than loading the entire result set in to memory at once. Since
prefetch_related relies on the entire result being available so that it can
collect all the `id`s, `refetch_related` has no effect when used with
`iterator`.
