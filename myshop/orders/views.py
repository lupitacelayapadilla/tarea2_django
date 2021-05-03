#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------------------------
# Archivo: views.py
#
# Descripción:
#   En este archivo se definen las vistas para la app de órdenes.
#
#   A continuación se describen los métodos que se implementaron en este archivo:
#
#                                               Métodos:
#           +------------------------+--------------------------+-----------------------+
#           |         Nombre         |        Parámetros        |        Función        |
#           +------------------------+--------------------------+-----------------------+
#           |                        |                          |  - Verifica la infor- |
#           |                        |  - request: datos de     |    mación y crea la   |
#           |    order_create()      |    la solicitud.         |    orden de compra a  |
#           |                        |                          |    partir de los datos|
#           |                        |                          |    del cliente y del  |
#           |                        |                          |    carrito.           |
#           +------------------------+--------------------------+-----------------------+
#           |                        |                          |  - Crea y envía el    |
#           |        send()          |  - order_id: id del      |    correo electrónico |
#           |                        |    la orden creada.      |    para notificar la  |
#           |                        |                          |    compra.            |
#           +------------------------+--------------------------+-----------------------+
#
#--------------------------------------------------------------------------------------------------

from django.shortcuts import render,redirect
from .models import OrderItem, Order
from catalog.models import Product
from .forms import OrderCreateForm
from django.core.mail import send_mail
from cart.cart import Cart
from django.template.defaulttags import register
from django.utils import timezone
from datetime import datetime, timedelta

def order_create(request):

    # Se crea el objeto Cart con la información recibida.
    cart = Cart(request)

    # Si la llamada es por método POST, es una creación de órden.
    if request.method == 'POST':

        # Se obtiene la información del formulario de la orden,
        # si la información es válida, se procede a crear la orden.
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save()
            for item in cart:
                OrderItem.objects.create(order=order,
                                         product=item['product'],
                                         price=item['price'],
                                         quantity=item['quantity'])
            
            # Se limpia el carrito con ayuda del método clear()
            cart.clear()
            
            # Llamada al método para enviar el email.
            send(order.id, cart)
            return render(request, 'orders/order/created.html', { 'cart': cart, 'order': order })
    else:
        form = OrderCreateForm()
    return render(request, 'orders/order/create.html', {'cart': cart,
                                                        'form': form})

def send(order_id, cart):
    # Se obtiene la información de la orden.
    order = Order.objects.get(id=order_id)

    # Se crea el subject del correo.
    subject = 'Order nr. {}'.format(order.id)

    # Se define el mensaje a enviar.
    message = 'Dear {},\n\nYou have successfully placed an order. Your order id is {}.\n\n\n'.format(order.first_name,order.id)
    message_part2 = 'Your order: \n\n'
    mesagges = []

    for item in cart:
        msg = str(item['quantity']) + 'x '+ str(item['product']) +'  $'+ str(item['total_price'])+ '\n'
        mesagges.append(msg)
    
    message_part3 = ' '.join(mesagges)
    message_part4 = '\n\n\n Total: $'+ str(cart.get_total_price())
    body = message + message_part2 + message_part3 + message_part4

    # Se envía el correo.
    send_mail(subject, body, '<email>', [order.email], fail_silently=False)

def send_cancel(email, first_name, order_id, total):
    # Se crea el subject del correo.
    subject = 'Order nr. {}'.format(order_id)

    # Se define el mensaje a enviar.
    message = 'Dear {},\n\nYou have successfully canceled the order {}.\n\n\n'.format(first_name, order_id)
    message2 = '\n\n\n Total Refund: ${}'.format(total) 
    body = message + message2
    # Se envía el correo.
    send_mail(subject, body, '<email>', [email], fail_silently=False)


def detail(request):
    order = Order.objects.first()
  
    if not order:
        context = {'type':'no_order'}
        return render(request, "orders/order/order_exception.html", context)
    elif get_days(order) > 0:
        context = {'type':'expired'}
        return render(request, "orders/order/order_exception.html", context)
    
    items = get_items(order)
    ids = list(items.values_list('product_id' ,flat=True))
    products = Product.objects.filter(id__in=ids)
    det_prod = []
    total=0
    for item in items:
        subtotal = item.price * item.quantity
        det_prod.append(
            {"id":item.product_id, "quantity":item.quantity,  "subtotal":subtotal, "order_item":item.id}
        )
        total+=subtotal
    context = {'items':det_prod, 'products':products, 'total':total}
    return render(request, "orders/order/order_detail.html", context)


def full_cancel(request):
    order = Order.objects.first()
    order_id = order.id
    email = order.email
    first_name = order.first_name
    total = 0
    items = OrderItem.objects.filter(order = order_id)
    for item in items:
        subtotal = item.price * item.quantity
        total+=subtotal
    order.delete()
    send_cancel(email,first_name, order_id, total)

    return render(request, 'orders/order/canceled.html', {'total':total})


def cancel_item(request, id):
   item = OrderItem.objects.get(id=id)
   item.delete()
   return redirect( 'order_detail')

def parcial_cancel(request):
    pass

def get_items(order):
    items = OrderItem.objects.filter(order = order.id)
    if not items:
        order.delete()
        order = Order.objects.first()
        items = OrderItem.objects.filter(order = order.id)
    return items

def get_days(order):
    now = timezone.now()
    order_date = order.created
    diff =  now - order_date
    days = diff.days
    return days
