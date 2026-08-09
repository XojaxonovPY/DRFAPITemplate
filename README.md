# Django ORM Performance Cheat Sheet

Django ORM'da performance optimizatsiyasining asosiy maqsadi:

* Database query sonini kamaytirish
* N+1 query muammosini oldini olish
* Keraksiz ma'lumotlarni yuklamaslik
* Database'da filtering/aggregation bajarish
* Indexlardan to‘g‘ri foydalanish
* Katta dataset bilan samarali ishlash
* Django application va database o‘rtasidagi workload'ni balanslash

---

# 1. `select_related()`

### Qachon?

`ForeignKey` va `OneToOneField` uchun.

### Mexanizm

```text
Django ORM
    ↓
SQL JOIN
    ↓
1 query
```

### Misol

```python
products = Product.objects.select_related("category")
```

O‘rniga:

```python
products = Product.objects.all()

for product in products:
    print(product.category.name)
```

`select_related()` N+1 query muammosini kamaytiradi.

### Rule

```text
ForeignKey / OneToOne
        ↓
select_related()
        ↓
JOIN
```

---

# 2. `prefetch_related()`

### Qachon?

* Reverse ForeignKey
* ManyToMany

uchun asosan ishlatiladi.

### Mexanizm

```text
Query #1 → Parent
Query #2 → Children
             ↓
       Python merge
```

### Misol

```python
categories = Category.objects.prefetch_related("products")
```

### Rule

```text
Reverse FK / M2M
        ↓
prefetch_related()
        ↓
Separate queries
        ↓
Python merge
```

---

# 3. `select_related()` + `prefetch_related()`

Ularni birga ishlatish mumkin.

```python
orders = Order.objects.select_related(
    "customer"
).prefetch_related(
    "products"
)
```

Masalan:

```text
Order
 ├── Customer       → select_related()
 └── Products       → prefetch_related()
```

Bu real loyihalarda juda ko‘p ishlatiladigan pattern.

---

# 4. N+1 Query Problem

### Yomon:

```python
orders = Order.objects.all()

for order in orders:
    print(order.customer.name)
```

Agar 100 ta order bo‘lsa:

```text
1 + 100 = 101 queries
```

### Yaxshi:

```python
orders = Order.objects.select_related("customer")

for order in orders:
    print(order.customer.name)
```

Natija:

```text
1 query
```

---

# 5. `Prefetch`

`prefetch_related()`ga custom queryset berish mumkin.

```python
from django.db.models import Prefetch

categories = Category.objects.prefetch_related(
    Prefetch(
        "products",
        queryset=Product.objects.filter(is_active=True)
    )
)
```

Faqat active product'lar olinadi.

---

# 6. `to_attr`

Prefetch qilingan ma'lumotni custom attribute'da saqlash:

```python
categories = Category.objects.prefetch_related(
    Prefetch(
        "products",
        queryset=Product.objects.filter(is_active=True),
        to_attr="active_products"
    )
)
```

Keyin:

```python
for category in categories:
    for product in category.active_products:
        print(product.name)
```

---

# 7. `filter()`ni Database'ga topshirish

### Yomon:

```python
products = Product.objects.all()

active_products = [
    product
    for product in products
    if product.is_active
]
```

Bu barcha product'larni application serverga olib keladi.

### Yaxshi:

```python
active_products = Product.objects.filter(
    is_active=True
)
```

Database filtering'ni o‘zi bajaradi.

### Rule

> Ma'lumotni imkon qadar database'da filter qil.

---

# 8. `exists()`

Faqat obyekt mavjudligini tekshirish kerak bo‘lsa:

### Yomon:

```python
if Product.objects.filter(name="Phone"):
    ...
```

### Yaxshi:

```python
if Product.objects.filter(name="Phone").exists():
    ...
```

SQL:

```sql
SELECT 1
FROM product
WHERE name = 'Phone'
LIMIT 1;
```

---

# 9. `count()`

Queryset sonini olish:

```python
count = Product.objects.filter(
    is_active=True
).count()
```

Database `COUNT()` bajaradi:

```sql
SELECT COUNT(*)
FROM product
WHERE is_active = true;
```

---

# 10. `len(queryset)` vs `count()`

Agar faqat soni kerak bo‘lsa:

```python
products.count()
```

ishlat.

```python
len(products)
```

Queryset evaluation qilishi va barcha obyektlarni yuklashi mumkin.

### Rule

```text
Faqat count kerak
        ↓
count()
```

---

# 11. `values()`

Agar Model object kerak bo‘lmasa:

```python
products = Product.objects.values(
    "id",
    "name",
    "price"
)
```

Natija:

```python
[
    {
        "id": 1,
        "name": "Phone",
        "price": 500
    }
]
```

Bu API response uchun ham foydali bo‘lishi mumkin.

---

# 12. `values_list()`

Faqat bitta yoki bir nechta field kerak bo‘lsa:

```python
product_ids = Product.objects.values_list(
    "id",
    flat=True
)
```

Natija:

```python
[1, 2, 3, 4, 5]
```

Bir nechta field:

```python
products = Product.objects.values_list(
    "id",
    "name"
)
```

Natija:

```python
[
    (1, "Phone"),
    (2, "Laptop")
]
```

---

# 13. `only()`

Faqat kerakli field'larni olish:

```python
products = Product.objects.only(
    "id",
    "name"
)
```

### Ehtiyot bo‘lish kerak

Keyinchalik yuklanmagan field'ga murojaat qilinsa, qo‘shimcha query paydo bo‘lishi mumkin.

```python
product.description
```

Agar `description` `only()`da bo‘lmasa, Django uni alohida query bilan yuklashi mumkin.

---

# 14. `defer()`

Ma'lum field'ni keyinga qoldirish:

```python
products = Product.objects.defer(
    "large_description"
)
```

Katta text/blob field'lar uchun ba'zi holatlarda foydali.

Lekin `only()` va `defer()`ni faqat real profiling asosida ishlatish kerak.

---

# 15. `iterator()`

Juda katta queryset'ni memory'ga birdaniga yuklamaslik uchun:

```python
for product in Product.objects.iterator():
    process(product)
```

Bu ayniqsa:

* migration
* export
* batch processing
* katta dataset

uchun foydali.

---

# 16. `bulk_create()`

Ko‘p obyekt yaratish kerak bo‘lsa:

### Yomon:

```python
for data in products:
    Product.objects.create(**data)
```

Bu ko‘p INSERT query beradi.

### Yaxshi:

```python
products = [
    Product(name="Phone"),
    Product(name="Laptop"),
    Product(name="Tablet"),
]

Product.objects.bulk_create(products)
```

Bu database'ga sezilarli kamroq query bilan yozish imkonini beradi.

---

# 17. `bulk_update()`

Ko‘p obyektni update qilish:

```python
products = Product.objects.filter(
    category=category
)

for product in products:
    product.is_active = False

Product.objects.bulk_update(
    products,
    ["is_active"]
)
```

Ko‘plab individual `UPDATE` query'lar o‘rniga bulk operation ishlatiladi.

---

# 18. `update()`

Agar Model instance kerak bo‘lmasa:

### Yomon:

```python
products = Product.objects.filter(
    category=category
)

for product in products:
    product.is_active = False
    product.save()
```

### Yaxshi:

```python
Product.objects.filter(
    category=category
).update(
    is_active=False
)
```

Bu database'da bitta bulk `UPDATE` bo‘lishi mumkin.

---

# 19. `delete()`

Bulk delete:

```python
Product.objects.filter(
    is_active=False
).delete()
```

Barcha matching record'larni o‘chirish uchun ishlatiladi.

Model signal'lari va `on_delete` kabi xatti-harakatlarni hisobga olish kerak.

---

# 20. `F()`

Database'dagi mavjud qiymat asosida update qilish.

### Yomon:

```python
product.stock -= 1
product.save()
```

### Yaxshi:

```python
from django.db.models import F

Product.objects.filter(
    id=product_id
).update(
    stock=F("stock") - 1
)
```

Bu operation database tarafida bajariladi.

### Afzalligi

Race condition xavfini kamaytirishga yordam beradi.

---

# 21. `Q()`

Murakkab query'lar uchun:

```python
from django.db.models import Q

products = Product.objects.filter(
    Q(name__icontains="phone") |
    Q(description__icontains="phone")
)
```

SQL:

```sql
WHERE
    name ILIKE '%phone%'
    OR description ILIKE '%phone%'
```

---

# 22. `annotate()`

Har bir object uchun qo‘shimcha hisoblangan field yaratish.

Masalan, Category'dagi product soni:

```python
from django.db.models import Count

categories = Category.objects.annotate(
    product_count=Count("products")
)
```

Keyin:

```python
for category in categories:
    print(category.name)
    print(category.product_count)
```

Bu hisoblashni Python'da emas, database'da bajarishga imkon beradi.

---

# 23. `aggregate()`

Butun queryset bo‘yicha umumiy calculation:

```python
from django.db.models import Avg, Sum, Max

result = Product.objects.aggregate(
    average_price=Avg("price"),
    total_price=Sum("price"),
    max_price=Max("price")
)
```

Natija:

```python
{
    "average_price": 250.5,
    "total_price": 10000,
    "max_price": 1000
}
```

---

# 24. `Subquery`

Murakkab query'larda subquery ishlatish mumkin.

Masalan, har bir customer uchun oxirgi order:

```python
from django.db.models import OuterRef, Subquery

latest_order = Order.objects.filter(
    customer=OuterRef("pk")
).order_by("-created_at")

customers = Customer.objects.annotate(
    latest_order_id=Subquery(
        latest_order.values("id")[:1]
    )
)
```

Bu Python loop bilan qilishdan ko‘ra database'da bajariladi.

---

# 25. `Exists`

Faqat related record mavjudligini tekshirish uchun:

```python
from django.db.models import Exists, OuterRef

orders = Order.objects.filter(
    customer=OuterRef("pk")
)

customers = Customer.objects.annotate(
    has_orders=Exists(orders)
)
```

Keyin:

```python
customer.has_orders
```

Bu `COUNT()` qilishdan ko‘ra ayrim holatlarda samaraliroq bo‘lishi mumkin, chunki database birinchi mos record topilganda yetarli bo‘ladi.

---

# 26. Database Index

Frequently searched/filter qilinadigan field'larda index muhim.

Masalan:

```python
class Product(models.Model):
    name = models.CharField(
        max_length=255,
        db_index=True
    )
```

Yoki:

```python
class Product(models.Model):
    sku = models.CharField(
        max_length=100,
        unique=True
    )
```

`unique=True` odatda unique index yaratishga olib keladi.

---

# 27. `Meta.indexes`

Murakkab yoki composite index:

```python
class Product(models.Model):

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["category", "is_active"]
            )
        ]
```

Bu kabi index quyidagi query uchun foydali bo‘lishi mumkin:

```python
Product.objects.filter(
    category=category,
    is_active=True
)
```

Indexni query pattern'ga qarab loyihalash kerak.

---

# 28. `order_by()` performance

Keraksiz sortingdan qochish.

```python
products = Product.objects.order_by(
    "-created_at"
)
```

Agar `created_at` bo‘yicha juda ko‘p query qilinsa, mos index foydali bo‘lishi mumkin.

---

# 29. `distinct()`

Duplicate natijalarni olib tashlash:

```python
products = Product.objects.filter(
    tags__name__in=["python", "django"]
).distinct()
```

Lekin `distinct()` database'ga qo‘shimcha workload berishi mumkin.

Faqat kerak bo‘lganda ishlat.

---

# 30. QuerySet Lazy Evaluation

Django QuerySet odatda darhol database'ga query yubormaydi.

```python
products = Product.objects.filter(
    is_active=True
)
```

Bu paytda query hali bajarilmagan bo‘lishi mumkin.

Evaluation quyidagi holatlarda sodir bo‘ladi:

```python
list(products)
```

```python
for product in products:
    ...
```

```python
len(products)
```

```python
bool(products)
```

```python
products.exists()
```

```python
products.first()
```

### Muhim

QuerySet'ning lazy ekanligini tushunish Django performance uchun juda muhim.

---

# 31. QuerySet Caching

Bir xil QuerySet evaluation qilingandan keyin natija cache'da saqlanishi mumkin.

```python
products = Product.objects.all()

for product in products:
    print(product.name)

for product in products:
    print(product.price)
```

Ko‘pincha birinchi evaluation'dan keyin queryset result cache ishlatiladi.

Lekin:

```python
Product.objects.all()
```

har safar yangi QuerySet bo‘lsa, bu boshqa masala.

---

# 32. QuerySet chaining

Django QuerySet'lar chain qilinadi:

```python
products = (
    Product.objects
    .filter(is_active=True)
    .select_related("category")
    .prefetch_related("tags")
    .order_by("-created_at")
)
```

Bu clean va readable ORM query hisoblanadi.

---

# 33. `get()`dan ehtiyotkor foydalanish

```python
product = Product.objects.get(
    id=product_id
)
```

`get()` aynan bitta object kutilganda ishlatiladi.

Agar object topilmasa:

```text
DoesNotExist
```

Agar bir nechta topilsa:

```text
MultipleObjectsReturned
```

API'da ko‘pincha:

```python
get_object_or_404()
```

qulay:

```python
from django.shortcuts import get_object_or_404

product = get_object_or_404(
    Product,
    id=product_id
)
```

---

# 34. Pagination

Katta dataset'ni:

```python
Product.objects.all()
```

bilan birdaniga API response'ga yuborish yomon amaliyot.

Pagination ishlat:

```text
Page 1 → 20 records
Page 2 → 20 records
Page 3 → 20 records
```

DRF'da pagination built-in mavjud.

---

# 35. DRF Serializer'dagi N+1

Bu juda muhim.

Serializer:

```python
class ProductSerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(
        source="category.name"
    )
```

Agar View'da:

```python
Product.objects.all()
```

bo‘lsa, serializer har bir Product uchun `category` query chaqirishi mumkin.

### Yaxshi:

```python
Product.objects.select_related(
    "category"
)
```

---

# 36. DRF + Prefetch

Masalan:

```python
class ProductSerializer(serializers.ModelSerializer):

    tags = TagSerializer(
        many=True
    )
```

View:

```python
queryset = Product.objects.prefetch_related(
    "tags"
)
```

Bu serializer ichidagi N+1 query'ni kamaytiradi.

---

# 37. `select_related()` + `prefetch_related()` + DRF

Real production pattern:

```python
class OrderViewSet(ModelViewSet):

    queryset = (
        Order.objects
        .select_related(
            "customer",
            "customer__address"
        )
        .prefetch_related(
            "products",
            "products__tags"
        )
    )
```

Bu nested serializerlar bilan ishlaganda ayniqsa muhim.

---

# 38. `select_for_update()`

Transaction ichida row lock qilish:

```python
from django.db import transaction

with transaction.atomic():

    account = (
        Account.objects
        .select_for_update()
        .get(id=account_id)
    )

    account.balance -= amount
    account.save()
```

Bu concurrent transaction'larda data consistency uchun ishlatiladi.

### Muhim

`select_for_update()` performance optimizatsiyasi emas. Bu **concurrency control** mexanizmi.

---

# 39. `transaction.atomic()`

Bir nechta database operation'ni bitta transaction sifatida bajarish:

```python
from django.db import transaction

with transaction.atomic():

    order = Order.objects.create(...)

    Payment.objects.create(
        order=order,
        amount=100
    )
```

Agar operation'larning bir qismi xato bersa, transaction rollback qilinadi.

---

# 40. `QuerySet.explain()`

Query qanday bajarilayotganini database'dan ko‘rish:

```python
queryset = Product.objects.filter(
    is_active=True
)

print(queryset.explain())
```

PostgreSQL kabi database'larda query execution plan'ni ko‘rish uchun juda foydali.

Masalan:

```text
Seq Scan
Index Scan
Bitmap Index Scan
Nested Loop
Hash Join
```

kabi ma'lumotlarni ko‘rish mumkin.

---

# 41. Query profiling

Performance muammosini taxmin qilmasdan, o‘lchash kerak.

### Django Debug Toolbar

Development muhitida:

```text
SQL Queries
Query Time
Duplicate Queries
```

kabi ma'lumotlarni ko‘rsatadi.

### Django connection

Development/debug uchun:

```python
from django.db import connection

print(len(connection.queries))
```

Production profiling uchun esa application monitoring va database monitoring vositalaridan foydalanish ma'qul.

---

# 42. `select_related()` vs `prefetch_related()`

| Feature             | `select_related()` | `prefetch_related()` |
| ------------------- | ------------------ | -------------------- |
| ForeignKey          | ✅                  | ✅                    |
| OneToOne            | ✅                  | ✅                    |
| Reverse FK          | ❌ Odatda emas      | ✅                    |
| ManyToMany          | ❌                  | ✅                    |
| SQL JOIN            | ✅                  | ❌                    |
| Separate query      | ❌                  | ✅                    |
| Python merge        | ❌                  | ✅                    |
| Typical query count | 1                  | 2+                   |

### Yodlash:

```text
select_related
    ↓
JOIN
    ↓
FK / OneToOne
```

```text
prefetch_related
    ↓
Separate queries
    ↓
Reverse FK / M2M
```

---

# 43. Performance Anti-Patterns

## ❌ 1. Loop ichida query

```python
for product in products:
    category = Category.objects.get(
        id=product.category_id
    )
```

### ✅

```python
products = Product.objects.select_related(
    "category"
)
```

---

## ❌ 2. Loop ichida `save()`

```python
for product in products:
    product.is_active = False
    product.save()
```

### ✅

```python
Product.objects.filter(
    category=category
).update(
    is_active=False
)
```

---

## ❌ 3. Barcha data'ni yuklash

```python
products = Product.objects.all()
```

Agar faqat ID kerak bo‘lsa:

```python
product_ids = Product.objects.values_list(
    "id",
    flat=True
)
```

---

## ❌ 4. Python'da filtering

```python
products = Product.objects.all()

result = [
    p for p in products
    if p.price > 100
]
```

### ✅

```python
result = Product.objects.filter(
    price__gt=100
)
```

---

## ❌ 5. Keraksiz nested serializer query'lari

```python
Product.objects.all()
```

### ✅

```python
Product.objects.select_related(
    "category"
).prefetch_related(
    "tags"
)
```

---

# 44. Golden Rules

### Rule 1

> Query'ni loop ichida yozma.

### Rule 2

> `ForeignKey` / `OneToOne` → `select_related()`.

### Rule 3

> Reverse FK / M2M → `prefetch_related()`.

### Rule 4

> Faqat kerakli field'larni ol.

```python
values()
values_list()
only()
```

### Rule 5

> Filtering va aggregation'ni database'ga topshir.

```python
filter()
annotate()
aggregate()
```

### Rule 6

> Bulk operationlardan foydalan.

```python
bulk_create()
bulk_update()
update()
```

### Rule 7

> Frequently queried field'lar uchun indexlarni o‘yla.

### Rule 8

> Katta dataset'ni pagination qil.

### Rule 9

> Performance muammosini taxmin qilma — o‘lcha.

```text
Debug Toolbar
EXPLAIN
Query profiling
Database monitoring
```

### Rule 10

> Query count kamayishi har doim performance yaxshilanishini anglatmaydi.

Asosiy metrikalar:

```text
Query count
Query execution time
DB CPU
DB memory
Network transfer
Application memory
Total response time
```

---

# 45. Quick Reference

```python
# JOIN
.select_related("category")

# Separate queries
.prefetch_related("products")

# Custom prefetch
Prefetch(
    "products",
    queryset=Product.objects.filter(is_active=True)
)

# Select fields
.values("id", "name")

# Select field list
.values_list("id", flat=True)

# Check existence
.exists()

# Count
.count()

# Bulk create
.bulk_create(objects)

# Bulk update
.bulk_update(objects, ["status"])

# Database-side update
.update(status="active")

# Database expression
F("stock") - 1

# Complex conditions
Q(...)

# Aggregation per object
.annotate(...)

# Aggregation for whole queryset
.aggregate(...)

# Subquery
Subquery(...)

# Existence subquery
Exists(...)

# Large queryset iteration
.iterator()

# Query execution plan
.explain()

# Row locking
.select_for_update()

# Transaction
transaction.atomic()
```

---

# 46. Performance Optimization Workflow

Production'da quyidagi tartibda ishlash yaxshi:

```text
                 Application
                      │
                      ▼
              Performance issue
                      │
                      ▼
              Profile / Measure
                      │
                      ▼
              Check SQL Queries
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
       N+1?                 Slow Query?
          │                       │
          ▼                       ▼
select_related()           EXPLAIN
prefetch_related()         Index
          │                 Query optimization
          └───────────┬───────────┘
                      ▼
                 Measure Again
                      │
                      ▼
                Compare Results
```

---

# 47. One-Minute Cheat Sheet

```text
┌─────────────────────────────────────────┐
│         DJANGO ORM PERFORMANCE          │
├─────────────────────────────────────────┤
│ FK / OneToOne        → select_related   │
│ Reverse FK / M2M     → prefetch_related │
│ N+1                  → optimize relations│
│ Existence            → exists()         │
│ Count                → count()          │
│ Few fields           → values()         │
│ IDs only             → values_list()    │
│ Bulk INSERT          → bulk_create()    │
│ Bulk UPDATE          → bulk_update()    │
│ DB-side UPDATE       → update() + F()   │
│ Complex conditions   → Q()              │
│ Per-row calculation  → annotate()       │
│ Global calculation   → aggregate()      │
│ Complex subquery     → Subquery()       │
│ Existence check      → Exists()         │
│ Large queryset       → iterator()       │
│ Query plan           → explain()        │
│ Frequently filtered  → Index            │
│ Large API response   → Pagination       │
│ Concurrent updates   → transaction +    │
│                        select_for_update │
└─────────────────────────────────────────┘
```

## Final principle

Django ORM performance'ni optimallashtirishning eng muhim fikri:

> **Application'da bajarish mumkin bo‘lgan ishni database'ga topshirish, database'dan esa faqat kerakli ma'lumotni olish.**

Ya'ni:

```text
❌ Database → barcha data → Python → filter/calculate

✅ Database → filter/calculate → faqat kerakli data → Python
```

Va eng muhimi:

```text
Don't optimize blindly.
Measure → Identify bottleneck → Optimize → Measure again.
```

