from django.db.models.signals import post_save, post_delete
from django.conf import settings
from django.dispatch import receiver

from TradConnect.models import Pedido, Detallepedido, Historialestadopedido
from .order_sync import schedule_order_sync


@receiver(post_save, sender=Pedido, dispatch_uid='nosql_pedido_save')
@receiver(post_delete, sender=Pedido, dispatch_uid='nosql_pedido_delete')
@receiver(post_save, sender=Detallepedido, dispatch_uid='nosql_detalle_save')
@receiver(post_delete, sender=Detallepedido, dispatch_uid='nosql_detalle_delete')
@receiver(post_save, sender=Historialestadopedido, dispatch_uid='nosql_historial_save')
@receiver(post_delete, sender=Historialestadopedido, dispatch_uid='nosql_historial_delete')
def order_changed(sender, instance, using, **kwargs):
    if kwargs.get('raw'):
        return
    if sender is not Pedido:
        previous = getattr(instance, '_nosql_previous_order', None)
        if previous is not None and previous != instance.pedidoid_id:
            schedule_order_sync(previous, using)
    schedule_order_sync(instance.pk if sender is Pedido else instance.pedidoid_id, using)


# Si se reasigna un detalle/historial, también se limpia la proyección del padre anterior.
from django.db.models.signals import pre_save


@receiver(pre_save, sender=Detallepedido, dispatch_uid='nosql_detalle_previous')
@receiver(pre_save, sender=Historialestadopedido, dispatch_uid='nosql_historial_previous')
def remember_previous_order(sender, instance, using, **kwargs):
    if settings.MONGODB_URI and using == 'default' and instance.pk and not kwargs.get('raw'):
        instance._nosql_previous_order = sender.objects.using(using).filter(pk=instance.pk).values_list('pedidoid_id', flat=True).first()
