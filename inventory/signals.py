# from django.db.models.signals import post_save
# from django.dispatch import receiver

# from inventory.models import SalesOrder
# from logistics.models import DeliveryOrder


# @receiver(post_save, sender=SalesOrder)
# def create_delivery_order(sender, instance, created, **kwargs):
# 
#     if created:
# 
#         DeliveryOrder.objects.create(
#             company=instance.company,
#             sales_order=instance
#         )