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

### [](#reverse-relations)Reverse Relations

Given a `ForeignKey` field linking a `product` to a `category`, Django will
setup the reverse link from a `category` to the set (or list) of `products`.
The convention is to name the reverse field `modelname_set`, but this can be
overridden.

For our examples above, we'd access the products of a category using
`product_set.all()`.

```python
In [33]: category = Category.objects.get(pk=1)
(0.001)
SELECT "shop_category"."id", "shop_category"."name"
FROM "shop_category" WHERE "shop_category"."id" = 1;

In [34]: products = list(category.product_set.all())
(0.001)
SELECT "shop_product"."id", "shop_product"."name", "shop_product"."category_id", "shop_product"."price"
FROM "shop_product"
WHERE "shop_product"."category_id" = 1;
```

Reverse relations function identically to `ManyToMany` fields, so they can be
prefetched, filtered, or ordered.

### [](#prefetch-or-select-related)Prefetch Related vs Select Related

**select_related**

Use `select_related()` on `ForeignKey` fields **only**. It has no affect on
`ManyToManyField`s or reverse relations.

> select_related is used to access a single related object

**prefetch_related**

Use `prefetch_related()` on `ManyToManyField`s or reverse relations. It can
also be used on `ForeignKey` fields, but `select_related` is nearly always a
better choice.

> prefetch_related is used to access multiple related objects

## [](#query-counts)Query Count Examples

Given the following count of objects in the database, how many queries are
executed for each example below?

- 1000 products
- 5 categories (200 products per category)
- 5000 features (10 features per product, some shared)

```python
In [35]: for p in Product.objects.all():
    ...:     print(p.category.name)
    ...:     for feature in p.features.all():
    ...:         print(f'{feature.name}: {feature.value}')
    ...:
```

<details>
<summary>Answer</summary>
2001 - 1 for product, 1000 for category, 1000 for features
</details>


```python
In [36]: for p in Product.objects.select_related('category').all():
    ...:     print(p.category.name)
    ...:     for feature in p.features.all():
    ...:         print(f'{feature.name}: {feature.value}')
    ...:
```

<details>
<summary>Answer</summary>
1001 - 1 for product and category, and 1000 for features
</details>

```python
In [37]: for p in Product.objects.prefetch_related('features').all():
    ...:     print(p.category.name)
    ...:     for feature in p.features.all():
    ...:         print(f'{feature.name}: {feature.value}')
    ...:
```

<details>
<summary>Answer</summary>
1002 - 1 for product, 1000 for category, and 1 for features
</details>

```python
In [38]: for p in Product.objects.select_related(
    ...:         'category'
    ...:         ).prefetch_related('features').all():
    ...:     print(p.category.name)
    ...:     for feature in p.features.all():
    ...:         print(f'{feature.name}: {feature.value}')
    ...:
```

<details>
<summary>Answer</summary>
2 - 1 for product and category, and 1 for features
</details>

```python
In [39]: for p in Product.objects.select_related(
    ...:         'category'
    ...:         ).prefetch_related('features').all():
    ...:     print(p.category.name)
    ...:     for feature in p.features.filter(name='Supplier'):
    ...:         print(f'{feature.name}: {feature.value}')
    ...:
```

<details>
<summary>Answer</summary>
1003 - 1 for product and category, and 1 for features cache, 1000 for features
</details>

## [](#query-optimisation)Query Optimisation

There are a bunch of optimisations you can make at the SQL layer, some of them
obvious, some of them requiring a great deal of knowledge about the specific
database you're using. We're going to focus on the optimisations we can make
at the django ORM level.

### [](#query-optimisation-sorting)Sorting

This one is fairly simple. Don't sort results if they don't absolutely need
to be sorted! Sorting can often take up a large portion of the actual query
time.

```sql
postgres=# explain analyze select * from shop_product;
                                                QUERY PLAN
----------------------------------------------------------------------------------------------------------
 Seq Scan on shop_product  (cost=0.00..1.30 rows=30 width=104) (actual time=0.011..0.014 rows=30 loops=1)
 Planning time: 0.049 ms
 Execution time: 0.031 ms

postgres=# explain analyze select * from shop_product order by price;
                                                   QUERY PLAN
----------------------------------------------------------------------------------------------------------------
 Sort  (cost=2.04..2.11 rows=30 width=104) (actual time=0.031..0.033 rows=30 loops=1)
   Sort Key: price
   Sort Method: quicksort  Memory: 27kB
   ->  Seq Scan on shop_product  (cost=0.00..1.30 rows=30 width=104) (actual time=0.009..0.013 rows=30 loops=1)
 Planning time: 0.060 ms
 Execution time: 0.051 ms
```

Sometimes, though, sneaky awful ORM developers will add a **default ordering**
to models. So even though we aren't adding ordering ourselves, there is an
implicit ordering added to every single query against that model.

```python

class Feature(models.Model):
    name = models.CharField(max_length=32)
    value = models.CharField(max_length=32)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

In [13]: features = list(Feature.objects.all())
(0.001)
SELECT "shop_feature"."id", "shop_feature"."name", "shop_feature"."value", "shop_feature"."visible"
FROM "shop_feature"
ORDER BY "shop_feature"."name" ASC;
```

You can be explicit about removing any default ordering though, which is
especially important when doing any kind of aggregation. Ordering fields are
added to the `GROUP BY`, which can give incorrect results if you weren't
expecting them.

```python
In [14]: features = list(Feature.objects.order_by())
(0.001)
SELECT "shop_feature"."id", "shop_feature"."name", "shop_feature"."value", "shop_feature"."visible"
FROM "shop_feature";
```

Much better.

### [](#filtering-early)Filter Early

You want your filters (WHERE clauses) to be as restrictive as possible. You
want to return the fewest possible number of rows at each step of a query. This
includes `__in` filters with subqueries!

Let's write a queryset, and `explain analyze` the SQL that would have been
executed.

```python
In [21]: features = Feature.objects.filter(
             name='Supplier', product__in=Product.objects.filter(price__gt=500)
         )

In [22]: print(features.query)
SELECT
"shop_feature"."id", "shop_feature"."name", "shop_feature"."value", "shop_feature"."visible"
FROM "shop_feature"
INNER JOIN "shop_product_features"
ON ("shop_feature"."id" = "shop_product_features"."feature_id")
WHERE ("shop_feature"."name" = 'Supplier' AND "shop_product_features"."product_id" IN (
    SELECT U0."id" AS Col1
    FROM "shop_product" U0 WHERE U0."price" > 500
))
ORDER BY "shop_feature"."name" ASC
```

```sql
postgres=# explain analyze SELECT
"shop_feature"."id", "shop_feature"."name", "shop_feature"."value", "shop_feature"."visible"
FROM "shop_feature"
INNER JOIN "shop_product_features" ON ("shop_feature"."id" = "shop_product_features"."feature_id")
WHERE ("shop_feature"."name" = 'Supplier' AND "shop_product_features"."product_id" IN (
    SELECT U0."id" AS Col1
    FROM "shop_product" U0 WHERE U0."price" > 500)
)
ORDER BY "shop_feature"."name" ASC;
                                                         QUERY PLAN
-----------------------------------------------------------------------------------------------------------------------------
 Nested Loop Semi Join  (cost=15.29..21.03 rows=1 width=169) (actual time=0.034..0.034 rows=0 loops=1)
   ->  Hash Join  (cost=15.15..20.76 rows=1 width=173) (actual time=0.034..0.034 rows=0 loops=1)
         Hash Cond: (shop_product_features.feature_id = shop_feature.id)
         ->  Seq Scan on shop_product_features  (cost=0.00..4.62 rows=262 width=8) (actual time=0.015..0.015 rows=1 loops=1)
         ->  Hash  (cost=15.12..15.12 rows=2 width=169) (actual time=0.011..0.011 rows=0 loops=1)
               Buckets: 1024  Batches: 1  Memory Usage: 8kB
               ->  Seq Scan on shop_feature  (cost=0.00..15.12 rows=2 width=169) (actual time=0.011..0.011 rows=0 loops=1)
                     Filter: ((name)::text = 'Supplier'::text)
                     Rows Removed by Filter: 35
   ->  Index Scan using shop_product_pkey on shop_product u0  (cost=0.14..0.20 rows=1 width=4)
         Index Cond: (id = shop_product_features.product_id)
         Filter: (price > '500'::numeric)
 Planning time: 0.313 ms
 Execution time: 0.093 ms
(14 rows)
```

### [](#optimising-indexes)Indexes

Indexes are usually the first thing people think about when trying to
optimise a query. Finding the ideal set of indexes to add to a particular
table is an art form, and always evolving depending on the number and nature
of various queries hitting that table.

When you add an index, always check to see if it's being used. Simply having
one does not mean it'll be used. `EXPLAIN ANALYZE` a couple of real queries
before and after.

Good candidates for indexes (all conditions below should be met):

- A table with rows > 100 or so. A table with fewer rows will probably just
  scan each row.
- A column that has lots of different values (cardinality). No use having an
  index if it matches 50% of data.
- If 50% of your data is NULL, but the rest is quite varied, then a
  `filtered index` might be a good fit.
- If many different queries use the same column in a WHERE clause
- Consider multiple column index if multiple columns exist in a WHERE clause
- Order is important in multiple column indexes. Use the most common column first.
- If there are lots of different WHERE clauses in a single query, an index is
  sometimes unlikely to be used.

### [](#values-querysets)Values Query Set

Model objects are very expensive to construct. For large querysets, it can
often add up to a significant percentage of overall time spent in python. Fields
need to be set, signals need to fire, reverse relations need to be set up. There's
a lot of work that goes into building up the model hierarchy.

If you just need the data from the database, and don't need to access model
properties at all, then use a [values()](https://docs.djangoproject.com/en/1.11/ref/models/querysets/#values)
or a [values_list()](https://docs.djangoproject.com/en/1.11/ref/models/querysets/#values-list)
method, which returns the data as simple dictionaries or tuples instead.

```python
In [25]: %time model_objects = list(Product.objects.all())

CPU times: user 985 µs, sys: 1.92 ms, total: 2.9 ms
Wall time: 3.09 ms

In [26]: %time model_objects = list(Product.objects.values())

CPU times: user 978 µs, sys: 465 µs, total: 1.44 ms
Wall time: 1.65 ms

In [27]: %time model_objects = list(Product.objects.values('name', 'price'))

CPU times: user 704 µs, sys: 597 µs, total: 1.3 ms
Wall time: 1.39 ms
```

### [](#queryset-calculations)Calculations

Some people like to speak about *Fat Models*, meaning that a lot of logic is
encapsulated within methods and properties of the model itself. This can be
a good thing in some cases, unless the method depends on data in a different
table, or a different model depends on the calculation in your method.

Ideally, we can execute a single query (plus any necessary prefetches) to get
all of the information we need for a particular goal. Sometimes though, we don't
get to choose how the query is constructed, or how it's used once executed.

If you need to use a model method for a particular calculation, then you have
to have that python object available. You're no longer just depending on the
database.

Here's an example:

```python
def customer_price(self):
    return Price.objects.get(
        product=self,
        start__lte=timezone.now(),
        end__isnull=True
    ).price
```

Now, a bunch of views and other models rely on this `customer_price` method,
so they need to construct a full model object, but it'll also execute a query
every time the price needs to be shown. This can be hugely expensive when
iterating over a large list of products.

Instead, design your models so that all important questions can be answered
with a `values` queryset.

[Query expressions](https://docs.djangoproject.com/en/1.11/ref/models/expressions/)
can be extremely helpful by performing calculations across a set of objects,
rather than performing them in python for each object. See my presentation/talk
on [customising sql](https://github.com/jarshwah/customsql_talk/) for more ideas.

### [](#advanced-prefetching)Advanced Prefetch Related

#### Prefetch Objects

[Prefetch](https://docs.djangoproject.com/en/1.11/ref/models/querysets/#django.db.models.Prefetch)
is a class that gives users greater control over the query executed to fill the
cache.

In our examples earlier, we seen what happened when you add filtering onto a
ManyToMany field -- it'll skip the cache. But if you only really care about
a subset of the related values, you can filter it in the `Prefetch` object.

```python
In [29]: products = (
    ...:     Product
    ...:     .objects
    ...:     .select_related('category')
    ...:     .prefetch_related(
    ...:         Prefetch('features', queryset=Feature.objects.filter(name='Supplier'))
    ...:     )
    ...: )

In [30]: for p in products:
    ...:     for f in p.features.all():
    ...:         print(f'{p.name}: {f.value}')
    ...:

    Samsung 65 inch: Samsung
    Samsung 75 inch: Samsung
    Juicer: Breville
```

That's only two queries.

#### Overwriting Inefficient Methods

Sometimes it's just not possible to avoid adding complex behaviour into our
models. But we can design our methods to be as optimal as possible locally,
while allowing a savvy caller that's using `Prefetch` to take it even further.

This is a pattern I haven't seen in the wild before, and I was surprised it
worked.

The concept is to cache the results of the many to many field on first access,
and to perform all filtering from within python. This keeps any access of the
many to many field down to a single query maximum per instance.

```python

from django.utils.functional import cached_property

class Product(models.Model):
    ...
    features = models.ManyToManyField(Feature)

    @cached_property
    def all_features(self):
        return list(self.features.all())

    @property
    def visible_features_python(self):
        return [feature for feature in self.all_features if feature.visible]

    @property
    def invisible_features_python(self):
        return [feature for feature in self.all_features if not feature.visible]

```

If `visible_features_python` is accessed, all features will be queried, stored
on the instance, and then only the visible features are returned. If
`invisible_features_python` is accessed after that, we skip the query execution,
and immediately filter the cached values. We've reduced the number of queries
from 2 to 1 for each Product. 500 products will result in 501 queries.

The great trick here, is that we can use a `Prefetch` objects to store our
cache directly on the `all_features` property, so that any access of visible
or invisible features results in 0 extra queries per product!

```python
In [33]: products = (
    ...:     Product
    ...:     .objects
    ...:     .select_related('category')
    ...:     .prefetch_related(
    ...:         Prefetch(
    ...:            'features',
    ...:            queryset=Feature.objects.all(),
    ...:            to_attr='all_features')
    ...:     )
    ...: )

In [34]: for p in products:
    ...:     for f in p.visible_features_python:
    ...:         print(f'{p.name}: {f.value}')
    ...:
```

There are a total of 2 queries executed for this query. 1 for the products,
and 1 for the features prefetch cache.

This pattern allows models to retain their methods and properties, while allowing
callers to inject ideal caches into a large number of objects for very little
cost.

## [](#summary)Summary

We started by going through how the Django ORM maps database concepts to
python concepts, mainly through relations. How relations work is important
when trying to optimise query counts with `select_related` and
`prefetch_related.`

Then we went over some techniques for improving performance of our queries. The
concepts were:

1. Reduction in number of queries - avoiding 1 + N queries.
2. Utilising data caches to avoid going to the database.
3. Making the database do less work:
    - Avoid sorting
    - Filter the data as much as possible
    - Create indexes to efficiently filter
4. Prefer performing calculations at the queryset level, rather than the
   model instance level.
5. Design your models so that callers can take advantage by providing prefetch
   caches.

What tips and tricks do you use for query performance tuning?
