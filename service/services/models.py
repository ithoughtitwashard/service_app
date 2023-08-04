from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models.signals import post_delete

from clients.models import Client
from services.signals import delete_cache_total_sum
from services.tasks import set_price, set_comment


class Service(models.Model):
    name = models.CharField(max_length=50)
    full_price = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.name}'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__full_price = self.full_price

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        result = super().save()

        if self.full_price != self.__full_price:
            subscriptions_id = self.subscriptions.values_list('id', flat=True)
            for subscription_id in subscriptions_id:
                set_price.delay(subscription_id)

        return result


class Plan(models.Model):
    PLAN_TYPES = (
        ('full', 'Full'),
        ('student', 'Student'),
        ('discount', 'Discount'),
    )

    plan_type = models.CharField(choices=PLAN_TYPES, max_length=10)
    discount_percent = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__discount_percent = self.discount_percent

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        result = super().save()

        if self.discount_percent != self.__discount_percent:
            subscriptions_id = self.subscriptions.values_list('id', flat=True)
            for subscription_id in subscriptions_id:
                set_price.delay(subscription_id)
                set_comment.delay(subscription_id)

        return result

    def __str__(self):
        return f'{self.plan_type}'


class Subscription(models.Model):
    client = models.ForeignKey(Client, related_name='subscriptions', on_delete=models.PROTECT)
    service = models.ForeignKey(Service, related_name='subscriptions', on_delete=models.PROTECT)
    plan = models.ForeignKey(Plan, related_name='subscriptions', on_delete=models.PROTECT)
    price = models.PositiveIntegerField(default=0)
    comment = models.CharField(max_length=50, default='')

    def __str__(self):
        return f'Client: {self.client} | Service: {self.service}'

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        creating = not bool(self.id)
        result = super().save()

        if creating:
            set_price.delay(self.id)

        return result


post_delete.connect(delete_cache_total_sum, sender=Subscription)