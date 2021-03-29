## Тестовое задание для школы бэкенда Яндекса

### Описание

REST API сервис, который позволяет нанимать курьеров на работу, принимать заказы и оптимально распределять заказы между курьерами.

### Запуск
```
$ git clone git@github.com:maria-kho/slasti_shop.git
$ cd slasti_shop
$ docker-compose up -d
$ docker-compose exec web python manage.py migrate
```

### Использование
ТЗ с описанием API: **assignment.pdf**  
Запуск тестов: `$ docker-compose exec web python manage.py test`
