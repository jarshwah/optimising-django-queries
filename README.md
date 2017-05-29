# optimising-django-queries

Django ORM basics, with some tips and tricks, for writing optimal queries.

## Query Logging

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
