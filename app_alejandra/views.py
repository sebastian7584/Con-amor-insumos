from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views import View
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import IntegrityError
import json
from .models import Color, Medida, Referencia, Nombre, Insumo2, Producto, ProductoInsumo, Proveedor, Compra, CompraInsumo
from .models import Cliente, Manualista, Produccion, LineaProduccion, InventarioProducto, Venta, LineaVenta, DespachoVenta, EntregaParcial, PagoProduccion, AjusteInsumo
from datetime import datetime
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Max
from django.db import transaction
import os
import csv
import io
from django.conf import settings
from django.utils.text import slugify


def get_next_numero(model_class, prefix):
    """Genera el siguiente número con prefijo (ej: FA-0001, PR-0002, CO-0003)."""
    last = model_class.objects.filter(numero__startswith=prefix).order_by('-numero').first()
    if last and last.numero:
        try:
            n = int(last.numero.split('-')[-1]) + 1
        except (ValueError, IndexError):
            n = 1
    else:
        n = 1
    return f"{prefix}{n:04d}"


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, 'login.html')

def home_view(request):
    return render(request, 'home.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def supplies_view(request):
    if request.method == "POST":
        action = request.POST.get('action')

        if action == "agregar_color":
            nuevo_color = request.POST.get('nuevo_color')
            if nuevo_color:
                if not Color.objects.filter(nombre__iexact=nuevo_color).exists():
                    Color.objects.create(nombre=nuevo_color)
                    messages.success(request, f"El color '{nuevo_color}' fue agregado correctamente.")
                else:
                    messages.error(request, f"El color '{nuevo_color}' ya existe.")
            return redirect('insumos')

        elif action == "agregar_medida":
            nueva_medida = request.POST.get('nueva_medida')
            if nueva_medida:
                if not Medida.objects.filter(nombre__iexact=nueva_medida).exists():
                    Medida.objects.create(nombre=nueva_medida)
                    messages.success(request, f"La medida '{nueva_medida}' fue agregada correctamente.")
                else:
                    messages.error(request, f"La medida '{nueva_medida}' ya existe.")
            return redirect('insumos')

        elif action == "agregar_nombre":
            nuevo_nombre = request.POST.get('nuevo_nombre')
            if nuevo_nombre:
                if not Nombre.objects.filter(nombre__iexact=nuevo_nombre).exists():
                    Nombre.objects.create(nombre=nuevo_nombre)
                    messages.success(request, f"El nombre '{nuevo_nombre}' fue agregada correctamente.")
                else:
                    messages.error(request, f"El nombre '{nuevo_nombre}' ya existe.")
            return redirect('insumos')

        elif action == "agregar_referencia":
            nueva_referencia = request.POST.get('nueva_referencia')
            if nueva_referencia:
                if not Referencia.objects.filter(nombre__iexact=nueva_referencia).exists():
                    Referencia.objects.create(nombre=nueva_referencia)
                    messages.success(request, f"La referencia '{nueva_referencia}' fue agregada correctamente.")
                else:
                    messages.error(request, f"La referencia '{nueva_referencia}' ya existe.")
            return redirect('insumos')

        elif action == "editar_insumo":
            insumo_id = request.POST.get('insumo_id')
            if insumo_id:
                try:
                    insumo = Insumo2.objects.get(id=insumo_id)
                    # Actualizar datos del insumo
                    insumo.referencia = request.POST.get('nueva_referencia')
                    insumo.nombre = request.POST.get('nuevo_nombre')
                    insumo.medida_id = request.POST.get('medida')
                    
                    # Actualizar imagen si se proporciona
                    imagen_file = request.FILES.get('imagen')
                    if imagen_file:
                        # Guardar nueva imagen
                        imagenes_root = os.path.join(settings.BASE_DIR, 'imagenes')
                        os.makedirs(imagenes_root, exist_ok=True)
                        
                        _, ext = os.path.splitext(imagen_file.name)
                        ext = ext.lower() if ext else '.jpg'
                        base_name = f"insumo-{slugify(insumo.referencia)}"
                        filename = base_name + ext
                        dest_path = os.path.join(imagenes_root, filename)
                        
                        counter = 1
                        while os.path.exists(dest_path):
                            filename = f"{base_name}-{counter}{ext}"
                            dest_path = os.path.join(imagenes_root, filename)
                            counter += 1
                        
                        with open(dest_path, 'wb+') as destination:
                            for chunk in imagen_file.chunks():
                                destination.write(chunk)
                        
                        insumo.imagen_url = os.path.join('imagenes', filename)
                    
                    insumo.save()
                    
                    # Actualizar colores
                    colores_ids = request.POST.getlist('colores')
                    insumo.colores.set(colores_ids)
                    
                    messages.success(request, f"El insumo '{insumo.nombre}' fue actualizado correctamente.")
                except Insumo2.DoesNotExist:
                    messages.error(request, "El insumo no existe.")
                except Exception as e:
                    messages.error(request, f"Error al actualizar el insumo: {str(e)}")
            return redirect('insumos')

        elif action == "eliminar_insumo":
            insumo_id = request.POST.get('insumo_id')
            if insumo_id:
                try:
                    insumo = Insumo2.objects.get(id=insumo_id)
                    nombre_insumo = insumo.nombre
                    insumo.delete()
                    messages.success(request, f"El insumo '{nombre_insumo}' fue eliminado correctamente.")
                except Insumo2.DoesNotExist:
                    messages.error(request, "El insumo no existe.")
                except Exception as e:
                    messages.error(request, f"Error al eliminar el insumo: {str(e)}")
            return redirect('insumos')

        elif action == "guardar_formulario":
            referencia = request.POST.get('nueva_referencia')
            nombre = request.POST.get('nuevo_nombre')
            medida_id = request.POST.get('medida')
            colores_ids = request.POST.getlist('colores')
            imagen_file = request.FILES.get('imagen')  # <<-- la imagen

            # Validar que los campos no estén vacíos
            if not (referencia and nombre and medida_id and colores_ids):
                messages.error(request, "Todos los campos deben estar completos.")
                return redirect('insumos')

            # Obtener las instancias relacionadas
            medida = Medida.objects.get(id=medida_id)
            colores = Color.objects.filter(id__in=colores_ids)

            # --- Guardar imagen en /imagenes con nombre insumo-<referencia>.<ext> ---
            imagen_rel_path = None
            try:
                # Carpeta /imagenes en la raíz del proyecto
                imagenes_root = os.path.join(settings.BASE_DIR, 'imagenes')
                os.makedirs(imagenes_root, exist_ok=True)

                if imagen_file:
                    # Extensión original (si no tiene, usamos .jpg)
                    _, ext = os.path.splitext(imagen_file.name)
                    ext = ext.lower() if ext else '.jpg'

                    # Nombre de archivo: insumo-<referencia-slug>.<ext>
                    base_name = f"insumo-{slugify(referencia)}"
                    filename = base_name + ext
                    dest_path = os.path.join(imagenes_root, filename)

                    # Si ya existe, versionamos: insumo-<ref>-1.ext, -2.ext, ...
                    counter = 1
                    while os.path.exists(dest_path):
                        filename = f"{base_name}-{counter}{ext}"
                        dest_path = os.path.join(imagenes_root, filename)
                        counter += 1

                    # Guardado en disco
                    with open(dest_path, 'wb+') as destination:
                        for chunk in imagen_file.chunks():
                            destination.write(chunk)

                    # Guardamos la ruta relativa para poder usarla en templates
                    imagen_rel_path = os.path.join('imagenes', filename)

            except Exception as e:
                messages.warning(request, f"No se pudo guardar la imagen: {str(e)}")

            # Crear Insumo2
            nuevo_insumo = Insumo2.objects.create(
                imagen_url=imagen_rel_path or "imagenes/placeholder.jpg",  # guarda la ruta (o un placeholder)
                referencia=referencia,
                nombre=nombre,
                medida=medida
            )
            nuevo_insumo.colores.set(colores)

            messages.success(request, "El formulario fue guardado exitosamente.")
            return redirect('insumos')
        

            
    # Obtener parámetros de paginación y ordenamiento
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    order_by = request.GET.get('order_by', 'referencia')
    
    # Validar per_page
    if per_page not in ['5', '10', '50']:
        per_page = 10
    
    # Validar order_by
    if order_by not in ['referencia', 'nombre', 'medida']:
        order_by = 'referencia'
    
    # Obtener todos los datos para los dropdowns y checkboxes
    colores = Color.objects.all()
    medidas = Medida.objects.all()
    referencias = Referencia.objects.all()
    nombres = Nombre.objects.all()
    
    # Obtener insumos con paginación
    insumos_queryset = Insumo2.objects.select_related('medida').prefetch_related('colores').all().order_by(order_by)
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(insumos_queryset, int(per_page))
    
    try:
        insumos_creados = paginator.page(page)
    except:
        insumos_creados = paginator.page(1)

    return render(request, 'supplies.html', {
        'colores': colores,
        'medidas': medidas,
        'referencias': referencias,
        'nombres': nombres,
        'insumos_creados': insumos_creados,
        'per_page': per_page,
        'current_page': page,
        'order_by': order_by
    })

def get_insumo_data(request, insumo_id):
    """Vista AJAX para obtener datos de un insumo específico"""
    try:
        insumo = Insumo2.objects.get(id=insumo_id)
        colores_ids = list(insumo.colores.values_list('id', flat=True))
        
        data = {
            'id': insumo.id,
            'referencia': insumo.referencia,
            'nombre': insumo.nombre,
            'medida_id': insumo.medida.id,
            'imagen_url': insumo.imagen_url,
            'colores': colores_ids
        }
        return JsonResponse(data)
    except Insumo2.DoesNotExist:
        return JsonResponse({'error': 'Insumo no encontrado'}, status=404)

def get_producto_data(request, producto_id):
    """Vista AJAX para obtener datos de un producto específico"""
    try:
        producto = Producto.objects.get(id=producto_id)
        colores_ids = list(producto.colores.values_list('id', flat=True))
        
        # Obtener insumos del producto
        insumos_producto = []
        for producto_insumo in ProductoInsumo.objects.filter(producto=producto):
            insumos_producto.append({
                'insumo_id': producto_insumo.insumo.id,
                'cantidad': producto_insumo.cantidad,
                'color_id': producto_insumo.color.id if producto_insumo.color else None
            })
        
        data = {
            'id': producto.id,
            'referencia': producto.referencia,
            'nombre': producto.nombre,
            'imagen_url': str(producto.imagen) if producto.imagen else None,
            'es_paquete': producto.es_paquete,
            'cantidad_por_paquete': producto.cantidad_por_paquete,
            'colores': colores_ids,
            'insumos': insumos_producto
        }
        return JsonResponse(data)
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)

def product_view(request):
    if request.method == "POST":
        action = request.POST.get('action')

        if action == "editar_producto":
            producto_id = request.POST.get('producto_id')
            if producto_id:
                try:
                    producto = Producto.objects.get(id=producto_id)
                    # Actualizar datos del producto
                    producto.referencia = request.POST.get('nueva_referencia')
                    producto.nombre = request.POST.get('nuevo_nombre')
                    producto.es_paquete = request.POST.get('es_paquete') == 'on'
                    producto.cantidad_por_paquete = int(request.POST.get('cantidad_por_paquete')) if request.POST.get('cantidad_por_paquete') else None
                    
                    # Actualizar imagen si se proporciona
                    imagen_file = request.FILES.get('imagen')
                    if imagen_file:
                        # Guardar nueva imagen
                        imagenes_root = os.path.join(settings.BASE_DIR, 'imagenes')
                        os.makedirs(imagenes_root, exist_ok=True)
                        
                        _, ext = os.path.splitext(imagen_file.name)
                        ext = ext.lower() if ext else '.jpg'
                        base_name = f"producto-{slugify(producto.referencia)}"
                        filename = base_name + ext
                        dest_path = os.path.join(imagenes_root, filename)
                        
                        counter = 1
                        while os.path.exists(dest_path):
                            filename = f"{base_name}-{counter}{ext}"
                            dest_path = os.path.join(imagenes_root, filename)
                            counter += 1
                        
                        with open(dest_path, 'wb+') as destination:
                            for chunk in imagen_file.chunks():
                                destination.write(chunk)
                        
                        producto.imagen = os.path.join('imagenes', filename)
                    
                    producto.save()
                    
                    # Actualizar insumos del producto
                    insumos_ids = request.POST.getlist('insumo_id[]')
                    cantidad_insumos = request.POST.getlist('cantidad[]')
                    colores_insumo_ids = request.POST.getlist('color_id[]')
                    
                    # Eliminar insumos existentes
                    ProductoInsumo.objects.filter(producto=producto).delete()
                    
                    # Agregar nuevos insumos
                    for insumo_id, cantidad, color_id in zip(insumos_ids, cantidad_insumos, colores_insumo_ids):
                        if not insumo_id or not cantidad:
                            continue
                        insumo = Insumo2.objects.get(id=insumo_id)
                        color = Color.objects.get(id=color_id) if color_id else None
                        ProductoInsumo.objects.create(
                            producto=producto,
                            insumo=insumo,
                            cantidad=int(cantidad),
                            color=color
                        )
                    
                    messages.success(request, f"El producto '{producto.nombre}' fue actualizado correctamente.")
                except Producto.DoesNotExist:
                    messages.error(request, "El producto no existe.")
                except Exception as e:
                    messages.error(request, f"Error al actualizar el producto: {str(e)}")
            return redirect('productos')

        elif action == "eliminar_producto":
            producto_id = request.POST.get('producto_id')
            if producto_id:
                try:
                    producto = Producto.objects.get(id=producto_id)
                    nombre_producto = producto.nombre
                    producto.delete()
                    messages.success(request, f"El producto '{nombre_producto}' fue eliminado correctamente.")
                except Producto.DoesNotExist:
                    messages.error(request, "El producto no existe.")
                except Exception as e:
                    messages.error(request, f"Error al eliminar el producto: {str(e)}")
            return redirect('productos')

        elif action == "guardar_formulario":
            referencia = request.POST.get('nueva_referencia')
            nombre = request.POST.get('nuevo_nombre')

            # Estos vienen de la tabla de insumos por fila
            insumos_ids = request.POST.getlist('insumo_id[]')
            cantidad_insumos = request.POST.getlist('cantidad[]')
            colores_insumo_ids = request.POST.getlist('color_id[]')

            # Imagen del producto
            imagen_file = request.FILES.get('imagen')

            # ✅ Paquetes
            es_paquete = request.POST.get('es_paquete') == 'on'
            cantidad_por_paquete = request.POST.get('cantidad_por_paquete')

            # Validación básica
            if not (referencia and nombre and insumos_ids and cantidad_insumos):
                messages.error(request, "Todos los campos obligatorios deben estar completos.")
                return redirect('productos')

            if es_paquete and not cantidad_por_paquete:
                messages.error(request, "Debes ingresar la cantidad por paquete.")
                return redirect('productos')

            # --- Guardar imagen en /imagenes con nombre producto-<referencia>.<ext> ---
            imagen_rel_path = None
            try:
                imagenes_root = os.path.join(settings.BASE_DIR, 'imagenes')
                os.makedirs(imagenes_root, exist_ok=True)

                if imagen_file:
                    _, ext = os.path.splitext(imagen_file.name)
                    ext = ext.lower() if ext else '.jpg'

                    base_name = f"producto-{slugify(referencia)}"
                    filename = base_name + ext
                    dest_path = os.path.join(imagenes_root, filename)

                    counter = 1
                    while os.path.exists(dest_path):
                        filename = f"{base_name}-{counter}{ext}"
                        dest_path = os.path.join(imagenes_root, filename)
                        counter += 1

                    with open(dest_path, 'wb+') as destination:
                        for chunk in imagen_file.chunks():
                            destination.write(chunk)

                    imagen_rel_path = os.path.join('imagenes', filename)
            except Exception as e:
                messages.warning(request, f"No se pudo guardar la imagen del producto: {str(e)}")

            try:
                # Crear o actualizar el producto por referencia
                nuevo_producto, creado = Producto.objects.get_or_create(
                    referencia=referencia,
                    defaults={
                        'nombre': nombre,
                        'imagen': imagen_rel_path or "imagenes/placeholder.jpg",
                        'es_paquete': es_paquete,
                        'cantidad_por_paquete': int(cantidad_por_paquete) if es_paquete else None
                    }
                )

                if not creado:
                    # Actualiza datos si ya existía
                    nuevo_producto.nombre = nombre
                    nuevo_producto.es_paquete = es_paquete
                    nuevo_producto.cantidad_por_paquete = int(cantidad_por_paquete) if es_paquete else None
                    if imagen_rel_path:  # solo si subieron una nueva imagen
                        nuevo_producto.imagen = imagen_rel_path
                    nuevo_producto.save()

                # Guarda líneas de insumos del producto
                if not creado:
                    ProductoInsumo.objects.filter(producto=nuevo_producto).delete()

                for insumo_id, cantidad, color_id in zip(insumos_ids, cantidad_insumos, colores_insumo_ids):
                    if not insumo_id or not cantidad:
                        continue
                    insumo = Insumo2.objects.get(id=insumo_id)
                    color = Color.objects.get(id=color_id) if color_id else None
                    ProductoInsumo.objects.create(
                        producto=nuevo_producto,
                        insumo=insumo,
                        cantidad=int(cantidad),
                        color=color
                    )

                messages.success(request, "El producto y sus insumos fueron guardados correctamente.")
                return redirect('productos')

            except IntegrityError:
                messages.error(request, "Error al guardar el producto. Verifica los datos.")
                return redirect('productos')

            except Exception as e:
                messages.error(request, f"Error inesperado: {str(e)}")
                return redirect('productos')


    # Datos para renderizar el formulario
    colores = Color.objects.all()
    medidas = Medida.objects.all()
    referencias = Referencia.objects.all()
    nombres = Nombre.objects.all()
    insumos_data = Insumo2.objects.select_related('medida').all()
    insumos = [{'id': i.id, 'nombre': i.nombre, 'referencia': i.referencia or '', 'medida': i.medida.nombre if i.medida else ''} for i in insumos_data]
    colores2 = {
        insumo.id: list(insumo.colores.values('id', 'nombre')) for insumo in Insumo2.objects.prefetch_related('colores')
    }

    # Obtener parámetros de paginación y ordenamiento
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    order_by = request.GET.get('order_by', 'referencia')
    
    # Validar per_page
    if per_page not in ['5', '10', '50']:
        per_page = 10
    
    # Validar order_by
    if order_by not in ['referencia', 'nombre']:
        order_by = 'referencia'
    
    # Obtener productos con paginación
    productos_queryset = Producto.objects.prefetch_related('colores').all().order_by(order_by)
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(productos_queryset, int(per_page))
    
    try:
        productos_creados = paginator.page(page)
    except:
        productos_creados = paginator.page(1)

    return render(request, 'productos.html', {
        'colores_json': json.dumps(colores2), 
        'colores': colores,
        'medidas': medidas,
        'referencias': referencias,
        'nombres': nombres,
        'insumos': insumos,
        'productos_creados': productos_creados,
        'per_page': per_page,
        'current_page': page,
        'order_by': order_by
    })



def proveedor_view(request):
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == "editar_proveedor":
            proveedor_id = request.POST.get('proveedor_id')
            if proveedor_id:
                try:
                    proveedor = Proveedor.objects.get(id=proveedor_id)
                    proveedor.tipo_documento = request.POST.get('tipo_documento')
                    proveedor.documento = request.POST.get('documento')
                    proveedor.nombre = request.POST.get('nombre')
                    proveedor.contacto = request.POST.get('contacto')
                    proveedor.telefono = request.POST.get('telefono')
                    proveedor.email = request.POST.get('email')
                    proveedor.direccion = request.POST.get('direccion')
                    proveedor.save()
                    messages.success(request, f"El proveedor '{proveedor.nombre}' fue actualizado correctamente.")
                except Proveedor.DoesNotExist:
                    messages.error(request, "El proveedor no existe.")
                except Exception as e:
                    messages.error(request, f"Error al actualizar el proveedor: {str(e)}")
            return redirect('proveedores')

        elif action == "eliminar_proveedor":
            proveedor_id = request.POST.get('proveedor_id')
            if proveedor_id:
                try:
                    proveedor = Proveedor.objects.get(id=proveedor_id)
                    nombre_proveedor = proveedor.nombre
                    proveedor.delete()
                    messages.success(request, f"El proveedor '{nombre_proveedor}' fue eliminado correctamente.")
                except Proveedor.DoesNotExist:
                    messages.error(request, "El proveedor no existe.")
                except Exception as e:
                    messages.error(request, f"Error al eliminar el proveedor: {str(e)}")
            return redirect('proveedores')

        else:  # Crear nuevo proveedor
            tipo_documento = request.POST.get('tipo_documento')
            documento = request.POST.get('documento')
            nombre = request.POST.get('nombre')
            contacto = request.POST.get('contacto')
            telefono = request.POST.get('telefono')
            email = request.POST.get('email')
            direccion = request.POST.get('direccion')

            # Verificar que los campos no estén vacíos
            if nombre and documento and tipo_documento:
                # Verificar si el proveedor ya existe por su documento
                if not Proveedor.objects.filter(documento=documento).exists():
                    Proveedor.objects.create(
                        tipo_documento=tipo_documento,
                        documento=documento,
                        nombre=nombre,
                        contacto=contacto,
                        telefono=telefono,
                        email=email,
                        direccion=direccion
                    )
                    messages.success(request, f"El proveedor '{nombre}' fue agregado correctamente.")
                else:
                    messages.warning(request, f"El proveedor con documento '{documento}' ya existe.")
            else:
                messages.error(request, "El tipo de documento, documento y nombre son obligatorios.")

            return redirect('proveedores')

    # Obtener todos los proveedores de la base de datos
    proveedores = Proveedor.objects.all()
    return render(request, 'proveedores.html', {'proveedores': proveedores})

def get_proveedor_data(request, proveedor_id):
    """Vista AJAX para obtener datos de un proveedor específico"""
    try:
        proveedor = Proveedor.objects.get(id=proveedor_id)
        
        data = {
            'id': proveedor.id,
            'tipo_documento': proveedor.tipo_documento,
            'documento': proveedor.documento,
            'nombre': proveedor.nombre,
            'contacto': proveedor.contacto,
            'telefono': proveedor.telefono,
            'email': proveedor.email,
            'direccion': proveedor.direccion
        }
        return JsonResponse(data)
    except Proveedor.DoesNotExist:
        return JsonResponse({'error': 'Proveedor no encontrado'}, status=404)

def eliminar_proveedor(request, proveedor_id):
    try:
        proveedor = Proveedor.objects.get(id=proveedor_id)
        proveedor.delete()
        messages.success(request, f"El proveedor '{proveedor.nombre}' ha sido eliminado.")
    except Proveedor.DoesNotExist:
        messages.error(request, "El proveedor no existe.")
    
    return redirect('proveedores')

def compras_view(request):
    if request.method == "POST":
        proveedor_id = request.POST.get('proveedor')
        insumos_ids = request.POST.getlist('insumo_id[]')
        colores_ids = request.POST.getlist('color_id[]')
        cantidades = request.POST.getlist('cantidad[]')
        valores = request.POST.getlist('valor_unitario[]')

        # Validación
        if not proveedor_id or not insumos_ids or not cantidades or not valores or not colores_ids:
            messages.error(request, "Debe seleccionar un proveedor, insumos y valores correctos.")
            return redirect('compras')

        proveedor = Proveedor.objects.get(id=proveedor_id)
        nueva_compra = Compra.objects.create(
            proveedor=proveedor,
            numero=get_next_numero(Compra, 'CO-')
        )

        for insumo_id, color_id, cantidad, valor in zip(insumos_ids, colores_ids, cantidades, valores):
            insumo = Insumo2.objects.get(id=insumo_id)
            color = Color.objects.get(id=color_id)
            medida = insumo.medida
            CompraInsumo.objects.create(
                compra=nueva_compra,
                insumo=insumo,
                color=color,
                cantidad=int(cantidad),
                medida=medida,
                valor_unitario=float(valor)
            )

        messages.success(request, f"Compra {nueva_compra.numero} registrada exitosamente.")
        return redirect('compras')

    proveedores = Proveedor.objects.all()
    insumos = list(Insumo2.objects.values('id', 'nombre', 'medida_id'))
    medidas = {medida.id: medida.nombre for medida in Medida.objects.all()}
    colores = {insumo.id: list(insumo.colores.values('id', 'nombre')) for insumo in Insumo2.objects.prefetch_related('colores')}

    precios_anteriores = {}

    for proveedor in proveedores:
        for insumo in insumos:
            ultima = CompraInsumo.objects.filter(
                compra__proveedor=proveedor,
                insumo_id=insumo["id"]
            ).order_by('-compra__fecha').first()
            if ultima:
                key = f"{proveedor.id}_{insumo['id']}"
                precios_anteriores[key] = float(ultima.valor_unitario)

    

    return render(request, 'compras.html', {
        'proveedores': proveedores,
        'insumos_json': json.dumps(insumos),
        'medidas_json': json.dumps(medidas),
        'colores_json': json.dumps(colores),
        'precios_anteriores': json.dumps(precios_anteriores),
    })

def cliente_view(request):
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == "editar_cliente":
            cliente_id = request.POST.get('cliente_id')
            if cliente_id:
                try:
                    cliente = Cliente.objects.get(id=cliente_id)
                    cliente.tipo_documento = request.POST.get('tipo_documento')
                    documento = (request.POST.get('documento') or '').strip() or None
                    if request.POST.get('tipo_documento') == 'SIN':
                        documento = None
                    cliente.documento = documento
                    cliente.nombre = request.POST.get('nombre')
                    cliente.telefono = request.POST.get('telefono')
                    cliente.email = request.POST.get('email')
                    cliente.direccion = request.POST.get('direccion')
                    cliente.save()
                    messages.success(request, f"El cliente '{cliente.nombre}' fue actualizado correctamente.")
                except Cliente.DoesNotExist:
                    messages.error(request, "El cliente no existe.")
                except Exception as e:
                    messages.error(request, f"Error al actualizar el cliente: {str(e)}")
            return redirect('clientes')

        elif action == "eliminar_cliente":
            cliente_id = request.POST.get('cliente_id')
            if cliente_id:
                try:
                    cliente = Cliente.objects.get(id=cliente_id)
                    nombre_cliente = cliente.nombre
                    cliente.delete()
                    messages.success(request, f"El cliente '{nombre_cliente}' fue eliminado correctamente.")
                except Cliente.DoesNotExist:
                    messages.error(request, "El cliente no existe.")
                except Exception as e:
                    messages.error(request, f"Error al eliminar el cliente: {str(e)}")
            return redirect('clientes')

        else:  # Crear nuevo cliente
            tipo_documento = request.POST.get('tipo_documento')
            documento = (request.POST.get('documento') or '').strip() or None
            nombre = request.POST.get('nombre')
            telefono = request.POST.get('telefono')
            email = request.POST.get('email')
            direccion = request.POST.get('direccion')

            if tipo_documento == 'SIN':
                documento = None

            # Verificar que el nombre no esté vacío
            if nombre:
                # Verificar si el cliente ya existe por su nombre
                if not Cliente.objects.filter(nombre=nombre).exists():
                    # Si tiene documento, verificar que no exista otro con el mismo documento
                    if documento and Cliente.objects.filter(documento=documento).exists():
                        messages.warning(request, f"Ya existe un cliente con el documento '{documento}'.")
                    else:
                        Cliente.objects.create(
                            tipo_documento=tipo_documento,
                            documento=documento,
                            nombre=nombre,
                            telefono=telefono,
                            email=email,
                            direccion=direccion
                        )
                        messages.success(request, f"El cliente '{nombre}' fue agregado correctamente.")
                else:
                    messages.warning(request, f"Ya existe un cliente con el nombre '{nombre}'.")
            else:
                messages.error(request, "El nombre es obligatorio.")

            return redirect('clientes')

    # Obtener parámetros de paginación y ordenamiento
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    order_by = request.GET.get('order_by', 'nombre')
    
    # Validar per_page
    if per_page not in ['5', '10', '50']:
        per_page = 10
    
    # Validar order_by
    if order_by not in ['nombre', 'documento']:
        order_by = 'nombre'
    
    # Obtener todos los clientes de la base de datos
    clientes_queryset = Cliente.objects.all().order_by(order_by)
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(clientes_queryset, int(per_page))
    
    try:
        clientes = paginator.page(page)
    except:
        clientes = paginator.page(1)
    
    return render(request, 'clientes.html', {
        'clientes': clientes,
        'per_page': per_page,
        'current_page': page,
        'order_by': order_by
    })

def get_cliente_data(request, cliente_id):
    """Vista AJAX para obtener datos de un cliente específico"""
    try:
        cliente = Cliente.objects.get(id=cliente_id)
        
        data = {
            'id': cliente.id,
            'tipo_documento': cliente.tipo_documento,
            'documento': cliente.documento,
            'nombre': cliente.nombre,
            'telefono': cliente.telefono,
            'email': cliente.email,
            'direccion': cliente.direccion
        }
        return JsonResponse(data)
    except Cliente.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

def eliminar_cliente(request, cliente_id):
    try:
        cliente = Cliente.objects.get(id=cliente_id)
        cliente.delete()
        messages.success(request, f"El cliente '{cliente.nombre}' ha sido eliminado.")
    except Cliente.DoesNotExist:
        messages.error(request, "El cliente no existe.")
    
    return redirect('clientes')

def manualista_view(request):
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == "editar_manualista":
            manualista_id = request.POST.get('manualista_id')
            if manualista_id:
                try:
                    manualista = Manualista.objects.get(id=manualista_id)
                    manualista.tipo_documento = request.POST.get('tipo_documento')
                    documento = request.POST.get('documento')
                    # Si el tipo es "Sin Documento", limpiar el documento
                    if request.POST.get('tipo_documento') == 'SIN':
                        documento = None
                    manualista.documento = documento
                    manualista.nombre = request.POST.get('nombre')
                    manualista.telefono = request.POST.get('telefono')
                    manualista.email = request.POST.get('email')
                    manualista.direccion = request.POST.get('direccion')
                    fecha_nacimiento = request.POST.get('fecha_nacimiento')
                    if fecha_nacimiento == "":
                        fecha_nacimiento = None
                    else:
                        try:
                            fecha_nacimiento = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
                        except ValueError:
                            messages.error(request, "Formato de fecha inválido.")
                            return redirect('manualistas')
                    manualista.fecha_nacimiento = fecha_nacimiento
                    manualista.save()
                    messages.success(request, f"El manualista '{manualista.nombre}' fue actualizado correctamente.")
                except Manualista.DoesNotExist:
                    messages.error(request, "El manualista no existe.")
                except Exception as e:
                    messages.error(request, f"Error al actualizar el manualista: {str(e)}")
            return redirect('manualistas')

        elif action == "eliminar_manualista":
            manualista_id = request.POST.get('manualista_id')
            if manualista_id:
                try:
                    manualista = Manualista.objects.get(id=manualista_id)
                    nombre_manualista = manualista.nombre
                    manualista.delete()
                    messages.success(request, f"El manualista '{nombre_manualista}' fue eliminado correctamente.")
                except Manualista.DoesNotExist:
                    messages.error(request, "El manualista no existe.")
                except Exception as e:
                    messages.error(request, f"Error al eliminar el manualista: {str(e)}")
            return redirect('manualistas')

        else:  # Crear nuevo manualista
            tipo_documento = request.POST.get('tipo_documento')
            documento = request.POST.get('documento')
            nombre = request.POST.get('nombre')
            telefono = request.POST.get('telefono')
            email = request.POST.get('email')
            direccion = request.POST.get('direccion')
            fecha_nacimiento = request.POST.get('fecha_nacimiento')

            # Si el tipo es "Sin Documento", limpiar el documento
            if tipo_documento == 'SIN':
                documento = None

            # Si el usuario no quiere guardar la fecha, se deja como None
            if fecha_nacimiento == "":
                fecha_nacimiento = None
            else:
                try:
                    fecha_nacimiento = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
                except ValueError:
                    messages.error(request, "Formato de fecha inválido.")
                    return redirect('manualistas')

            # Verificar que el nombre no esté vacío
            if nombre:
                # Verificar si el manualista ya existe por su nombre
                if not Manualista.objects.filter(nombre=nombre).exists():
                    # Si tiene documento, verificar que no exista otro con el mismo documento
                    if documento and Manualista.objects.filter(documento=documento).exists():
                        messages.warning(request, f"Ya existe un manualista con el documento '{documento}'.")
                    else:
                        Manualista.objects.create(
                            tipo_documento=tipo_documento,
                            documento=documento,
                            nombre=nombre,
                            telefono=telefono,
                            email=email,
                            direccion=direccion,
                            fecha_nacimiento=fecha_nacimiento
                        )
                        messages.success(request, f"El manualista '{nombre}' fue agregado correctamente.")
                else:
                    messages.warning(request, f"Ya existe un manualista con el nombre '{nombre}'.")
            else:
                messages.error(request, "El nombre es obligatorio.")

            return redirect('manualistas')

    # Obtener parámetros de paginación y ordenamiento
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    order_by = request.GET.get('order_by', 'nombre')
    
    # Validar per_page
    if per_page not in ['5', '10', '50']:
        per_page = 10
    
    # Validar order_by
    if order_by not in ['nombre', 'documento']:
        order_by = 'nombre'
    
    # Obtener todos los manualistas de la base de datos
    manualistas_queryset = Manualista.objects.all().order_by(order_by)
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(manualistas_queryset, int(per_page))
    
    try:
        manualistas = paginator.page(page)
    except:
        manualistas = paginator.page(1)
    
    return render(request, 'manualistas.html', {
        'manualistas': manualistas,
        'per_page': per_page,
        'current_page': page,
        'order_by': order_by
    })

def get_manualista_data(request, manualista_id):
    """Vista AJAX para obtener datos de un manualista específico"""
    try:
        manualista = Manualista.objects.get(id=manualista_id)
        
        data = {
            'id': manualista.id,
            'tipo_documento': manualista.tipo_documento,
            'documento': manualista.documento,
            'nombre': manualista.nombre,
            'telefono': manualista.telefono,
            'email': manualista.email,
            'direccion': manualista.direccion,
            'fecha_nacimiento': manualista.fecha_nacimiento.strftime('%Y-%m-%d') if manualista.fecha_nacimiento else None
        }
        return JsonResponse(data)
    except Manualista.DoesNotExist:
        return JsonResponse({'error': 'Manualista no encontrado'}, status=404)


def eliminar_manualista(request, manualista_id):
    try:
        manualista = Manualista.objects.get(id=manualista_id)
        manualista.delete()
        messages.success(request, f"La manualista '{manualista.nombre}' ha sido eliminada.")
    except Manualista.DoesNotExist:
        messages.error(request, "La manualista no existe.")
    
    return redirect('manualistas')

def produccion_view(request):
    if request.method == "POST":
        manualista_id = request.POST.get('manualista')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_tentativa = request.POST.get('fecha_tentativa')
        valor_a_pagar = request.POST.get('valor_a_pagar')
        productos_ids = request.POST.getlist('producto_id[]')
        cantidades = request.POST.getlist('cantidad[]')
        colores_ids = request.POST.getlist('color_id[]')

        # Validaciones
        if not (manualista_id and fecha_inicio and fecha_tentativa and productos_ids and cantidades):
            messages.error(request, "Todos los campos deben estar completos.")
            return redirect('produccion')
        if len(cantidades) != len(productos_ids):
            messages.error(request, "Cada producto debe tener una cantidad.")
            return redirect('produccion')
        # Validar cantidades (permite repetir el mismo producto en varias filas)
        try:
            cantidades_int = [int(c) for c in cantidades]
            if any(c <= 0 for c in cantidades_int):
                messages.error(request, "Todas las cantidades deben ser mayores a 0.")
                return redirect('produccion')
        except ValueError:
            messages.error(request, "Las cantidades deben ser números enteros.")
            return redirect('produccion')
        # Asegurar mismo número de colores que de productos (si faltan, rellenar con el primero)
        while len(colores_ids) < len(productos_ids):
            colores_ids.append(colores_ids[0] if colores_ids else '')

        try:
            valor_decimal = float(valor_a_pagar or 0)
        except ValueError:
            valor_decimal = 0

        try:
            with transaction.atomic():
                manualista = Manualista.objects.get(id=manualista_id)
                nueva_produccion = Produccion.objects.create(
                    manualista=manualista,
                    fecha_inicio=fecha_inicio,
                    fecha_tentativa=fecha_tentativa,
                    estado="Pendiente",
                    valor_a_pagar=valor_decimal if valor_decimal > 0 else None,
                    numero=get_next_numero(Produccion, 'PR-')
                )

                ins2 = calcular_produccion_interno(productos_ids, cantidades)

                for i in ins2.values():
                    color_insumo = Color.objects.get(id=i['color'])
                    CompraInsumo.objects.create(
                        compra=None,
                        produccion=nueva_produccion,
                        insumo=i['insumo'],
                        color=color_insumo,
                        cantidad=-i['cantidad'],  # negativo
                        medida=i['insumo'].medida,
                        valor_unitario=0,
                        estado='Reserva Producción'
                    )

                for idx, (producto_id, cantidad, color_id) in enumerate(zip(productos_ids, cantidades, colores_ids)):
                    cantidad_val = cantidades_int[idx]
                    producto = Producto.objects.get(id=producto_id)
                    color = None
                    if color_id and str(color_id).strip():
                        try:
                            color = Color.objects.get(id=color_id)
                        except (Color.DoesNotExist, ValueError):
                            pass
                    if not color:
                        color = producto.colores.first()
                    if not color:
                        raise ValueError(f"El producto '{producto.nombre}' no tiene colores asignados.")
                    LineaProduccion.objects.create(
                        produccion=nueva_produccion,
                        producto=producto,
                        color=color,
                        cantidad=cantidad_val,
                    )
                    InventarioProducto.objects.create(
                        produccion=nueva_produccion,
                        producto=producto,
                        color=color,
                        cantidad=cantidad_val,
                        estado='En producción',
                    )

            messages.success(request, f"Orden de producción {nueva_produccion.numero} creada exitosamente con insumos reservados.")
            return redirect('produccion')
        except (Manualista.DoesNotExist, Producto.DoesNotExist) as e:
            messages.error(request, "Manualista o producto no encontrado.")
            return redirect('produccion')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('produccion')
        except Exception as e:
            messages.error(request, f"Error al crear la orden: {str(e)}")
            return redirect('produccion')

    manualistas = Manualista.objects.all()
    productos_raw = list(Producto.objects.values('id', 'nombre', 'referencia'))
    productos = [{'id': p['id'], 'nombre': f"{p['nombre']} - {p['referencia']}" if p.get('referencia') else p['nombre']} for p in productos_raw]
    colores = {p['id']: list(Color.objects.filter(producto__id=p['id']).values('id', 'nombre')) for p in productos_raw}

    return render(request, 'produccion.html', {
        'manualistas': manualistas,
        'productos_json': json.dumps(productos),
        'colores_json': json.dumps(colores),
    })

def calcular_produccion(request):
    productos_ids = request.GET.getlist('producto_id[]')
    # colores_ids = request.GET.getlist('color_id[]')
    cantidades = request.GET.getlist('cantidad[]')

    # Corregir el problema de los valores concatenados en un solo string
    if len(productos_ids) == 1 and "," in productos_ids[0]:
        productos_ids = productos_ids[0].split(",")

    # if len(colores_ids) == 1 and "," in colores_ids[0]:
    #     colores_ids = colores_ids[0].split(",")

    if len(cantidades) == 1 and "," in cantidades[0]:
        cantidades = cantidades[0].split(",")

    errores = []
    insumos_requeridos = {}

    for producto_id, cantidad in zip(productos_ids, cantidades):
        if not producto_id or not cantidad:  
            continue  

        cantidad = int(cantidad)
        producto = Producto.objects.get(id=producto_id)
        insumos = ProductoInsumo.objects.filter(producto=producto)

        for insumo in insumos:
            insumo_color_valido = True
            # colores_insumo = insumo.insumo.colores.all()

            # Si el insumo tiene "SinColor", se permite cualquier color
            # if colores_insumo.filter(nombre="SinColor").exists():
            #     insumo_color_valido = True
            # elif colores_insumo.filter(id=color.id).exists():
            #     insumo_color_valido = True
            # else:
            #     errores.append(f"El insumo '{insumo.insumo.nombre}' no tiene el color '{color.nombre}'.")

            if insumo_color_valido:
                insumo_total = cantidad * insumo.cantidad  
                insumo_id = insumo.insumo.id
                insumo_color = insumo.color.nombre
                color = insumo.color.id
                insumo_medida = insumo.insumo.medida.nombre if insumo.insumo.medida else "N/A"

                # Obtener la cantidad disponible en `CompraInsumo`
                compras_total = CompraInsumo.objects.filter(
                    insumo=insumo.insumo,
                    color=color
                ).aggregate(total=Sum('cantidad'))['total'] or 0

                

                # Calcular faltantes
                cantidad_disponible = compras_total 
                faltantes = insumo_total - cantidad_disponible if insumo_total > cantidad_disponible else 0

                if f'{insumo_id}-{color}' in insumos_requeridos:
                    insumos_requeridos[f'{insumo_id}-{color}']['cantidad'] += insumo_total
                    insumos_requeridos[f'{insumo_id}-{color}']['faltantes'] += faltantes
                else:
                    nombre_insumo_display = f"{insumo.insumo.nombre} - {insumo.insumo.referencia}" if insumo.insumo.referencia else insumo.insumo.nombre
                    insumos_requeridos[f'{insumo_id}-{color}'] = {
                        'nombre': nombre_insumo_display,
                        'cantidad': insumo_total,
                        'color': insumo_color,
                        'medida': insumo_medida,
                        'faltantes': faltantes
                    }
    for key in insumos_requeridos.keys():
        ids = key.split('-')
        # Obtener la cantidad disponible en `CompraInsumo`
        compras_total = CompraInsumo.objects.filter(
            insumo=ids[0],
            color=ids[1]
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        insumos_requeridos[key]['faltantes'] = insumos_requeridos[key]['cantidad'] - compras_total
        if insumos_requeridos[key]['faltantes'] < 0:
            insumos_requeridos[key]['faltantes'] = 0
        pass

    return JsonResponse({'errores': errores, 'insumos_requeridos': list(insumos_requeridos.values())})
def calcular_produccion_interno(productos_ids, cantidades):
 

    # Corregir el problema de los valores concatenados en un solo string
    if len(productos_ids) == 1 and "," in productos_ids[0]:
        productos_ids = productos_ids[0].split(",")

    # if len(colores_ids) == 1 and "," in colores_ids[0]:
    #     colores_ids = colores_ids[0].split(",")

    if len(cantidades) == 1 and "," in cantidades[0]:
        cantidades = cantidades[0].split(",")

    errores = []
    insumos_requeridos = {}

    for producto_id, cantidad in zip(productos_ids, cantidades):
        if not producto_id or not cantidad:  
            continue  

        cantidad = int(cantidad)
        producto = Producto.objects.get(id=producto_id)
        insumos = ProductoInsumo.objects.filter(producto=producto)

        for insumo in insumos:
            insumo_color_valido = True
            # colores_insumo = insumo.insumo.colores.all()

            # Si el insumo tiene "SinColor", se permite cualquier color
            # if colores_insumo.filter(nombre="SinColor").exists():
            #     insumo_color_valido = True
            # elif colores_insumo.filter(id=color.id).exists():
            #     insumo_color_valido = True
            # else:
            #     errores.append(f"El insumo '{insumo.insumo.nombre}' no tiene el color '{color.nombre}'.")

            if insumo_color_valido:
                insumo_total = cantidad * insumo.cantidad  
                insumo_id = insumo.insumo.id
                insumo_color = insumo.color.nombre
                color = insumo.color.id
                insumo_medida = insumo.insumo.medida.nombre if insumo.insumo.medida else "N/A"

                # Obtener la cantidad disponible en `CompraInsumo`
                compras_total = CompraInsumo.objects.filter(
                    insumo=insumo.insumo,
                    color=color
                ).aggregate(total=Sum('cantidad'))['total'] or 0

                

                # Calcular faltantes
                cantidad_disponible = compras_total 
                faltantes = insumo_total - cantidad_disponible if insumo_total > cantidad_disponible else 0

                if f'{insumo_id}-{color}' in insumos_requeridos:
                    insumos_requeridos[f'{insumo_id}-{color}']['cantidad'] += insumo_total
                else:
                    insumos_requeridos[f'{insumo_id}-{color}'] = {
                        'insumo': insumo.insumo,
                        'cantidad': insumo_total,
                        'color': insumo.color.id,
                        'medida': insumo_medida,
                    }
 

    return insumos_requeridos

def ventas_view(request):
    if request.method == "POST":
        cliente_id = request.POST.get('cliente')
        inventario_ids = request.POST.getlist('inventario_id[]')
        cantidades = request.POST.getlist('cantidad[]')
        valores_venta = request.POST.getlist('valor_venta[]')

        if not cliente_id or not inventario_ids or not valores_venta or not cantidades:
            messages.error(request, "Debes completar todos los campos.")
            return redirect('ventas')

        cliente = Cliente.objects.get(id=cliente_id)
        nueva_venta = Venta.objects.create(
            cliente=cliente,
            numero=get_next_numero(Venta, 'FA-')
        )

        # Permitir varias filas del mismo producto/color (ej. 2 líneas del mismo producto)
        for producto_color_key, cantidad_str, valor_venta_str in zip(inventario_ids, cantidades, valores_venta):
            cantidad = int(cantidad_str)
            valor = float(valor_venta_str)
            
            # Parsear la clave del producto
            if '_' in producto_color_key:
                producto_id, color_id = producto_color_key.split('_', 1)
                producto = Producto.objects.get(id=producto_id)
                
                if color_id == 'sin_color':
                    color, _ = Color.objects.get_or_create(nombre='Sin color', defaults={'nombre': 'Sin color'})
                else:
                    color = Color.objects.get(id=color_id)
            else:
                # Fallback para formato anterior
                inventario = InventarioProducto.objects.get(id=producto_color_key)
                producto = inventario.producto
                color = inventario.color

            # Línea de venta para seguimiento y despachos parciales
            LineaVenta.objects.create(
                venta=nueva_venta,
                producto=producto,
                color=color,
                cantidad=cantidad,
                valor_venta=valor
            )

            # Registrar en inventario como vendido (sin producción asociada)
            InventarioProducto.objects.create(
                produccion=None,
                producto=producto,
                color=color,
                cantidad=cantidad,
                estado='Vendido',
                valor_venta=valor
            )

        messages.success(request, f"Factura {nueva_venta.numero} registrada correctamente.")
        return redirect('ventas')

    clientes = Cliente.objects.all()
    
    # Obtener TODOS los productos creados, no solo los con inventario
    productos_creados = Producto.objects.all()
    colores_disponibles = Color.objects.all()
    
    # Crear datos de productos para el frontend
    productos_data = {}
    for producto in productos_creados:
        # Obtener colores del producto
        colores_producto = list(producto.colores.all())
        
        if colores_producto:
            # Si el producto tiene colores específicos
            for color in colores_producto:
                key = f"{producto.id}_{color.id}"
                productos_data[key] = {
                    'producto_id': producto.id,
                    'producto_nombre': producto.nombre,
                    'producto_referencia': producto.referencia,
                    'color_id': color.id,
                    'color_nombre': color.nombre
                }
        else:
            # Si el producto no tiene colores específicos, usar "Sin color"
            key = f"{producto.id}_sin_color"
            productos_data[key] = {
                'producto_id': producto.id,
                'producto_nombre': producto.nombre,
                'producto_referencia': producto.referencia,
                'color_id': None,
                'color_nombre': 'Sin color'
            }

    return render(request, 'ventas.html', {
        'clientes': clientes,
        'productos_json': json.dumps(productos_data)
    })


def seguimiento_produccion_view(request):
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == "registrar_entrega":
            linea_id = request.POST.get('linea_id')
            cantidad_entregada = int(request.POST.get('cantidad_entregada', 0))
            observaciones = request.POST.get('observaciones', '')
            
            if linea_id and cantidad_entregada > 0:
                try:
                    linea = LineaProduccion.objects.get(id=linea_id)
                    
                    # Verificar que no exceda la cantidad pendiente
                    if cantidad_entregada > linea.cantidad_pendiente:
                        messages.error(request, f"La cantidad entregada ({cantidad_entregada}) no puede exceder la cantidad pendiente ({linea.cantidad_pendiente}).")
                    else:
                        # Registrar la entrega parcial
                        EntregaParcial.objects.create(
                            linea_produccion=linea,
                            cantidad_entregada=cantidad_entregada,
                            observaciones=observaciones
                        )
                        
                        # Actualizar la cantidad entregada en la línea
                        linea.cantidad_entregada += cantidad_entregada
                        linea.save()
                        
                        # Verificar si la línea está completa
                        if linea.cantidad_entregada >= linea.cantidad:
                            # Crear inventario para productos terminados
                            InventarioProducto.objects.create(
                                produccion=linea.produccion,
                                producto=linea.producto,
                                color=linea.color,
                                cantidad=linea.cantidad,
                                estado='Terminado'
                            )
                        
                        messages.success(request, f"Entrega registrada: {cantidad_entregada} unidades de {linea.producto.nombre}.")
                        
                except LineaProduccion.DoesNotExist:
                    messages.error(request, "La línea de producción no existe.")
                except Exception as e:
                    messages.error(request, f"Error al registrar la entrega: {str(e)}")
            else:
                messages.error(request, "Debes ingresar una cantidad válida.")
            
            return redirect('seguimiento_produccion')

        elif action == "marcar_terminado":
            produccion_id = request.POST.get('produccion_id')
            try:
                produccion = Produccion.objects.get(id=produccion_id)
            except Produccion.DoesNotExist:
                messages.error(request, "La producción no existe.")
                return redirect('seguimiento_produccion')

            # Completar todas las líneas pendientes: dar por recibido lo que falte
            lineas = LineaProduccion.objects.filter(produccion=produccion)
            lineas_completadas = 0
            for linea in lineas:
                pendiente = linea.cantidad - linea.cantidad_entregada
                if pendiente > 0:
                    EntregaParcial.objects.create(
                        linea_produccion=linea,
                        cantidad_entregada=pendiente,
                        observaciones="Completado al marcar la orden como terminada"
                    )
                    linea.cantidad_entregada = linea.cantidad
                    linea.save()
                    InventarioProducto.objects.create(
                        produccion=produccion,
                        producto=linea.producto,
                        color=linea.color,
                        cantidad=linea.cantidad,
                        estado='Terminado'
                    )
                    lineas_completadas += 1

            produccion.estado = 'Terminado'
            produccion.save()

            # Actualizar estado de todos los inventarios de esta producción
            InventarioProducto.objects.filter(produccion=produccion).update(estado='Terminado')

            if lineas_completadas > 0:
                messages.success(request, f"La orden {produccion.numero or produccion.id} ha sido marcada como Terminada. Se dieron por recibidas {lineas_completadas} línea(s) pendiente(s).")
            else:
                messages.success(request, f"La orden {produccion.numero or produccion.id} ha sido marcada como Terminada.")
            return redirect('seguimiento_produccion')

        elif action == "registrar_ajuste":
            produccion_id = request.POST.get('produccion_id')
            insumo_color = request.POST.get('insumo_color', '')
            tipo = request.POST.get('tipo', '').strip()
            cantidad_str = request.POST.get('cantidad', '0')
            observaciones = request.POST.get('observaciones', '').strip() or None
            if not produccion_id or not insumo_color or tipo not in ('envio_extra', 'sobrante'):
                messages.error(request, "Faltan datos o tipo de ajuste no válido.")
                return redirect('seguimiento_produccion')
            try:
                insumo_id, color_id = insumo_color.split(',')
            except ValueError:
                messages.error(request, "Insumo/color no válido.")
                return redirect('seguimiento_produccion')
            try:
                cantidad = int(cantidad_str)
                if cantidad <= 0:
                    messages.error(request, "La cantidad debe ser mayor a 0.")
                    return redirect('seguimiento_produccion')
            except ValueError:
                messages.error(request, "Cantidad inválida.")
                return redirect('seguimiento_produccion')
            try:
                produccion = Produccion.objects.get(id=produccion_id)
                insumo = Insumo2.objects.get(id=insumo_id)
                color = Color.objects.get(id=color_id)
                AjusteInsumo.objects.create(
                    produccion=produccion,
                    insumo=insumo,
                    color=color,
                    tipo=tipo,
                    cantidad=cantidad,
                    observaciones=observaciones,
                )
                tipo_label = "Se envían más insumos" if tipo == 'envio_extra' else "Sobran insumos"
                messages.success(request, f"Ajuste registrado: {tipo_label} - {insumo.nombre} ({color.nombre}) x {cantidad}.")
            except (Produccion.DoesNotExist, Insumo2.DoesNotExist, Color.DoesNotExist) as e:
                messages.error(request, "Orden, insumo o color no encontrado.")
            except Exception as e:
                messages.error(request, f"Error al registrar el ajuste: {str(e)}")
            return redirect('seguimiento_produccion')

    # Filtros
    search_query = request.GET.get('search', '')
    estado_filter = request.GET.get('estado', '')
    manualista_filter = request.GET.get('manualista', '')
    
    # Paginación
    per_page = int(request.GET.get('per_page', 10))
    page = int(request.GET.get('page', 1))
    
    # Obtener producciones con filtros
    producciones_query = Produccion.objects.prefetch_related(
        'lineas__entregas_parciales',
        'lineas__producto',
        'lineas__color',
        'manualista',
        'ajustes_insumos__insumo',
        'ajustes_insumos__color',
    ).all()
    
    # Aplicar filtros
    if search_query:
        producciones_query = producciones_query.filter(
            id__icontains=search_query
        )
    
    if estado_filter:
        producciones_query = producciones_query.filter(estado=estado_filter)
    
    if manualista_filter:
        producciones_query = producciones_query.filter(manualista_id=manualista_filter)
    
    # Ordenar por número de orden (ID) descendente
    producciones_query = producciones_query.order_by('-id')
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(producciones_query, per_page)
    producciones = paginator.get_page(page)

    # Insumos por producción (para dropdown de ajustes): insumo+color únicos de CompraInsumo
    produccion_ids = [p.id for p in producciones]
    compras_insumos = CompraInsumo.objects.filter(
        produccion_id__in=produccion_ids
    ).select_related('insumo', 'color')
    insumos_por_produccion = {pid: [] for pid in produccion_ids}
    vistos = {pid: set() for pid in produccion_ids}
    for ci in compras_insumos:
        key = (ci.insumo_id, ci.color_id)
        if key not in vistos[ci.produccion_id]:
            vistos[ci.produccion_id].add(key)
            insumos_por_produccion[ci.produccion_id].append({
                'insumo_id': ci.insumo_id,
                'color_id': ci.color_id,
                'label': f"{ci.insumo.nombre} ({ci.color.nombre})",
            })
    
    # Obtener manualistas para el filtro
    manualistas = Manualista.objects.all().order_by('nombre')
    
    # Estados disponibles
    estados = [
        ('', 'Todos los estados'),
        ('Pendiente', 'Pendiente'),
        ('En proceso', 'En proceso'),
        ('Terminado', 'Terminado'),
    ]

    return render(request, 'seguimiento_produccion.html', {
        'producciones': producciones,
        'insumos_por_produccion': insumos_por_produccion,
        'manualistas': manualistas,
        'estados': estados,
        'search_query': search_query,
        'estado_filter': estado_filter,
        'manualista_filter': manualista_filter,
        'per_page': per_page,
        'page': page,
    })


def orden_fabricante_view(request, produccion_id):
    """Vista tipo PDF para anexar al fabricante: productos, materiales, imágenes y totales de insumos."""
    produccion = get_object_or_404(
        Produccion.objects.prefetch_related('lineas__producto', 'lineas__color', 'manualista'),
        id=produccion_id
    )
    lineas_detalle = []
    resumen_insumos = {}  # key (insumo_id, color_id): {insumo, color_nombre, medida_nombre, cantidad_total}

    for linea in produccion.lineas.all():
        producto = linea.producto
        insumos_linea = list(
            ProductoInsumo.objects.filter(producto=producto).select_related('insumo', 'insumo__medida', 'color')
        )
        detalle_insumos = []
        for pi in insumos_linea:
            cant_total = pi.cantidad * linea.cantidad
            detalle_insumos.append({
                'insumo': pi.insumo,
                'cantidad_por_unidad': pi.cantidad,
                'cantidad_total': cant_total,
                'color_nombre': pi.color.nombre if pi.color else '—',
                'medida_nombre': pi.insumo.medida.nombre if pi.insumo.medida else '—',
            })
            key = (pi.insumo.id, pi.color.id if pi.color else None)
            if key not in resumen_insumos:
                resumen_insumos[key] = {
                    'insumo': pi.insumo,
                    'color_nombre': pi.color.nombre if pi.color else '—',
                    'medida_nombre': pi.insumo.medida.nombre if pi.insumo.medida else '—',
                    'cantidad_total': 0,
                }
            resumen_insumos[key]['cantidad_total'] += cant_total

        lineas_detalle.append({
            'linea': linea,
            'producto': producto,
            'insumos': detalle_insumos,
        })

    return render(request, 'orden_fabricante.html', {
        'produccion': produccion,
        'lineas_detalle': lineas_detalle,
        'resumen_insumos': list(resumen_insumos.values()),
    })


def pagos_manualistas_view(request):
    """Módulo de pagos a manualistas: órdenes con valor a pagar y registro de cada pago."""
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "registrar_pago":
            produccion_id = request.POST.get('produccion_id')
            monto_str = request.POST.get('monto')
            fecha = request.POST.get('fecha')
            observaciones = request.POST.get('observaciones', '').strip() or None
            if produccion_id and monto_str and fecha:
                try:
                    monto = float(monto_str)
                    if monto <= 0:
                        messages.error(request, "El monto debe ser mayor a 0.")
                    else:
                        produccion = Produccion.objects.get(id=produccion_id)
                        pendiente = produccion.pendiente_pago()
                        if monto > pendiente:
                            messages.error(request, f"El monto no puede superar lo pendiente (${pendiente:,.2f}).")
                        else:
                            PagoProduccion.objects.create(
                                produccion=produccion,
                                monto=monto,
                                fecha=fecha,
                                observaciones=observaciones
                            )
                            messages.success(request, f"Pago de ${monto:,.2f} registrado para la orden {produccion.numero or produccion_id}.")
                except (Produccion.DoesNotExist, ValueError) as e:
                    messages.error(request, "Datos inválidos.")
                except Exception as e:
                    messages.error(request, str(e))
            else:
                messages.error(request, "Completa orden, monto y fecha.")
            return redirect('pagos_manualistas')

    manualista_id = request.GET.get('manualista', '')
    producciones_qs = Produccion.objects.prefetch_related('pagos', 'manualista').annotate(
        total_pagado=Sum('pagos__monto')
    ).order_by('-id')

    if manualista_id:
        producciones_qs = producciones_qs.filter(manualista_id=manualista_id)

    # Agrupar por manualista: solo acumulados para la lista
    manualistas_detalle = []
    manualistas_vistos = set()
    for p in producciones_qs:
        m = p.manualista
        if m.id not in manualistas_vistos:
            manualistas_vistos.add(m.id)
            ordenes_m = Produccion.objects.filter(manualista=m).annotate(
                total_pagado=Sum('pagos__monto')
            )
            total_a_pagar = sum(float(prod.valor_a_pagar or 0) for prod in ordenes_m)
            total_pagado = sum(float(prod.total_pagado or 0) for prod in ordenes_m)
            manualistas_detalle.append({
                'manualista': m,
                'total_a_pagar': total_a_pagar,
                'total_pagado': total_pagado,
                'pendiente': max(0, total_a_pagar - total_pagado),
            })

    if not manualista_id:
        manualistas_detalle.sort(key=lambda x: x['manualista'].nombre)

    return render(request, 'pagos_manualistas.html', {
        'manualistas_detalle': manualistas_detalle,
        'manualista_filter': manualista_id,
    })


def pagos_manualista_detalle_view(request, manualista_id):
    """Ventana de detalle: órdenes y pagos de un manualista, con botón Atrás."""
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "registrar_pago":
            produccion_id = request.POST.get('produccion_id')
            monto_str = request.POST.get('monto')
            fecha = request.POST.get('fecha')
            observaciones = request.POST.get('observaciones', '').strip() or None
            if produccion_id and monto_str and fecha:
                try:
                    monto = float(monto_str)
                    if monto <= 0:
                        messages.error(request, "El monto debe ser mayor a 0.")
                    else:
                        produccion = Produccion.objects.get(id=produccion_id, manualista_id=manualista_id)
                        pendiente = produccion.pendiente_pago()
                        if monto > pendiente:
                            messages.error(request, f"El monto no puede superar lo pendiente (${pendiente:,.2f}).")
                        else:
                            PagoProduccion.objects.create(
                                produccion=produccion,
                                monto=monto,
                                fecha=fecha,
                                observaciones=observaciones
                            )
                            messages.success(request, f"Pago de ${monto:,.2f} registrado para la orden {produccion.numero or produccion_id}.")
                except (Produccion.DoesNotExist, ValueError):
                    messages.error(request, "Datos inválidos.")
                except Exception as e:
                    messages.error(request, str(e))
            else:
                messages.error(request, "Completa orden, monto y fecha.")
            return redirect('pagos_manualista_detalle', manualista_id=manualista_id)

    manualista = get_object_or_404(Manualista, id=manualista_id)
    ordenes_qs = Produccion.objects.filter(manualista=manualista).prefetch_related('pagos').annotate(
        total_pagado=Sum('pagos__monto')
    ).order_by('-id')

    total_a_pagar = 0
    total_pagado = 0
    ordenes = []
    for p in ordenes_qs:
        v = float(p.valor_a_pagar or 0)
        pag = float(p.total_pagado or 0)
        pend = max(0, v - pag)
        total_a_pagar += v
        total_pagado += pag
        ordenes.append({
            'produccion': p,
            'valor_a_pagar': v,
            'total_pagado': pag,
            'pendiente': pend,
        })
    pendiente_total = max(0, total_a_pagar - total_pagado)

    return render(request, 'pagos_manualista_detalle.html', {
        'manualista': manualista,
        'total_a_pagar': total_a_pagar,
        'total_pagado': total_pagado,
        'pendiente_total': pendiente_total,
        'ordenes': ordenes,
    })


def seguimiento_ventas_view(request):
    """Seguimiento de ventas: listar ventas y registrar despachos parciales (múltiples líneas a la vez)."""
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "registrar_despachos":
            # Despacho múltiple: linea_id[] y cantidad_despachada[] en el mismo orden
            linea_ids = request.POST.getlist('linea_id[]')
            cantidades = request.POST.getlist('cantidad_despachada[]')
            observaciones = request.POST.get('observaciones', '').strip() or None
            registrados = 0
            errores = []
            for linea_id, cant_str in zip(linea_ids, cantidades):
                try:
                    cantidad = int(cant_str or 0)
                except ValueError:
                    continue
                if not linea_id or cantidad <= 0:
                    continue
                try:
                    linea = LineaVenta.objects.get(id=linea_id)
                    pendiente = linea.cantidad_pendiente
                    if cantidad > pendiente:
                        errores.append(f"{linea.producto.nombre}: máx. {pendiente} uds.")
                        continue
                    DespachoVenta.objects.create(
                        linea_venta=linea,
                        cantidad_despachada=cantidad,
                        observaciones=observaciones
                    )
                    linea.cantidad_despachada += cantidad
                    linea.save()
                    registrados += 1
                except LineaVenta.DoesNotExist:
                    pass
                except Exception as e:
                    errores.append(str(e))
            if errores:
                for err in errores:
                    messages.error(request, err)
            if registrados:
                messages.success(request, f"Despacho registrado: {registrados} ítem(s) de la orden.")
            elif not errores:
                messages.warning(request, "Indica al menos una cantidad a despachar.")
            return redirect('seguimiento_ventas')
        elif action == "registrar_despacho":
            # Compatibilidad: despacho de una sola línea (modal)
            linea_id = request.POST.get('linea_id')
            cantidad = int(request.POST.get('cantidad_despachada', 0))
            observaciones = request.POST.get('observaciones', '').strip() or None
            if linea_id and cantidad > 0:
                try:
                    linea = LineaVenta.objects.get(id=linea_id)
                    pendiente = linea.cantidad_pendiente
                    if cantidad > pendiente:
                        messages.error(request, f"La cantidad a despachar ({cantidad}) no puede exceder lo pendiente ({pendiente}).")
                    else:
                        DespachoVenta.objects.create(
                            linea_venta=linea,
                            cantidad_despachada=cantidad,
                            observaciones=observaciones
                        )
                        linea.cantidad_despachada += cantidad
                        linea.save()
                        messages.success(request, f"Despacho registrado: {cantidad} uds de {linea.producto.nombre}.")
                except LineaVenta.DoesNotExist:
                    messages.error(request, "La línea de venta no existe.")
                except Exception as e:
                    messages.error(request, f"Error al registrar el despacho: {str(e)}")
            else:
                messages.error(request, "Ingresa una cantidad válida.")
            return redirect('seguimiento_ventas')

    # Filtros
    search = request.GET.get('search', '')
    cliente_id = request.GET.get('cliente', '')
    per_page = max(5, min(50, int(request.GET.get('per_page', 10))))
    page = request.GET.get('page', 1)

    ventas_qs = Venta.objects.prefetch_related(
        'lineas__producto',
        'lineas__color',
        'lineas__despachos',
        'cliente'
    ).order_by('-fecha')

    if search:
        if search.isdigit():
            ventas_qs = ventas_qs.filter(id=search)
        else:
            ventas_qs = ventas_qs.filter(cliente__nombre__icontains=search)
    if cliente_id:
        ventas_qs = ventas_qs.filter(cliente_id=cliente_id)

    from django.core.paginator import Paginator
    paginator = Paginator(ventas_qs, per_page)
    ventas_page = paginator.get_page(page)

    clientes = Cliente.objects.all().order_by('nombre')

    return render(request, 'seguimiento_ventas.html', {
        'ventas': ventas_page,
        'clientes': clientes,
        'search_query': search,
        'cliente_filter': cliente_id,
        'per_page': per_page,
        'page': page,
    })


def _get_informe_vendido_sin_inventario():
    """Productos/colores vendidos cuya cantidad vendida supera el inventario disponible (Terminado + En producción)."""
    from django.db.models import Sum
    vendido = {}
    for row in LineaVenta.objects.values('producto_id', 'color_id').annotate(total=Sum('cantidad')):
        key = (row['producto_id'], row['color_id'])
        vendido[key] = row['total']
    disponible = {}
    for row in InventarioProducto.objects.filter(
        estado__in=['Terminado', 'En producción']
    ).values('producto_id', 'color_id').annotate(total=Sum('cantidad')):
        key = (row['producto_id'], row['color_id'])
        disponible[key] = row['total']
    report = []
    all_keys = set(vendido.keys()) | set(disponible.keys())
    for (producto_id, color_id) in all_keys:
        v = vendido.get((producto_id, color_id), 0)
        d = disponible.get((producto_id, color_id), 0)
        if v > d:
            try:
                producto = Producto.objects.get(id=producto_id)
                color = Color.objects.get(id=color_id)
                report.append({
                    'producto_nombre': producto.nombre,
                    'producto_referencia': producto.referencia or '',
                    'color_nombre': color.nombre,
                    'vendido': v,
                    'disponible': d,
                    'faltante': v - d,
                })
            except (Producto.DoesNotExist, Color.DoesNotExist):
                pass
    return sorted(report, key=lambda x: (-x['faltante'], x['producto_nombre']))


def _get_informe_insumos_faltantes():
    """Insumos requeridos por órdenes de producción (Pendiente/En proceso) que no tienen cantidad suficiente."""
    from django.db.models import Sum
    # Requerido por producciones activas
    requerido = {}
    for linea in LineaProduccion.objects.filter(
        produccion__estado__in=['Pendiente', 'En proceso']
    ).select_related('producto'):
        cantidad_linea = linea.cantidad
        for pi in ProductoInsumo.objects.filter(producto=linea.producto).select_related('insumo', 'color', 'insumo__medida'):
            key = (pi.insumo_id, pi.color_id)
            req = cantidad_linea * pi.cantidad
            if key not in requerido:
                requerido[key] = {
                    'insumo_id': pi.insumo_id,
                    'insumo_nombre': pi.insumo.nombre,
                    'insumo_referencia': pi.insumo.referencia or '',
                    'color_id': pi.color_id,
                    'color_nombre': pi.color.nombre,
                    'medida_nombre': pi.insumo.medida.nombre if pi.insumo.medida else '—',
                    'requerido': 0,
                }
            requerido[key]['requerido'] += req
    if not requerido:
        return []
    # Disponible en CompraInsumo (suma por insumo+color)
    disponible = {}
    for row in CompraInsumo.objects.values('insumo_id', 'color_id').annotate(total=Sum('cantidad')):
        key = (row['insumo_id'], row['color_id'])
        disponible[key] = row['total']
    report = []
    for key, data in requerido.items():
        disp = disponible.get(key, 0)
        faltante = data['requerido'] - disp
        if faltante > 0:
            report.append({
                'insumo_nombre': data['insumo_nombre'],
                'insumo_referencia': data['insumo_referencia'],
                'color_nombre': data['color_nombre'],
                'medida_nombre': data['medida_nombre'],
                'requerido': data['requerido'],
                'disponible': max(0, disp),
                'faltante': faltante,
            })
    return sorted(report, key=lambda x: (-x['faltante'], x['insumo_nombre']))


def informes_view(request):
    """Área de informes: vendido sin inventario e insumos faltantes para producción."""
    reporte_vendido = _get_informe_vendido_sin_inventario()
    reporte_insumos = _get_informe_insumos_faltantes()
    return render(request, 'informes.html', {
        'reporte_vendido': reporte_vendido,
        'reporte_insumos': reporte_insumos,
    })


def informes_pdf_view(request):
    """Vista para imprimir / guardar como PDF el mismo informe."""
    from django.utils import timezone
    reporte_vendido = _get_informe_vendido_sin_inventario()
    reporte_insumos = _get_informe_insumos_faltantes()
    return render(request, 'informes_pdf.html', {
        'reporte_vendido': reporte_vendido,
        'reporte_insumos': reporte_insumos,
        'now': timezone.now(),
    })


# --- Importar / Exportar (guardar y editar en masa) ---

EXPORT_ENTITIES = {
    'clientes': {
        'label': 'Clientes',
        'filename': 'clientes',
        'model': Cliente,
        'headers': ['id', 'tipo_documento', 'documento', 'nombre', 'telefono', 'email', 'direccion'],
        'get_row': lambda o: [o.id, o.tipo_documento or '', o.documento or '', o.nombre, o.telefono or '', o.email or '', o.direccion or ''],
    },
    'manualistas': {
        'label': 'Manualistas',
        'filename': 'manualistas',
        'model': Manualista,
        'headers': ['id', 'tipo_documento', 'documento', 'nombre', 'telefono', 'email', 'direccion'],
        'get_row': lambda o: [o.id, o.tipo_documento or '', o.documento or '', o.nombre, o.telefono or '', o.email or '', o.direccion or ''],
    },
    'proveedores': {
        'label': 'Proveedores',
        'filename': 'proveedores',
        'model': Proveedor,
        'headers': ['id', 'tipo_documento', 'documento', 'nombre', 'contacto', 'telefono', 'email', 'direccion'],
        'get_row': lambda o: [o.id, o.tipo_documento or '', o.documento or '', o.nombre, o.contacto or '', o.telefono or '', o.email or '', o.direccion or ''],
    },
    'productos': {
        'label': 'Productos',
        'filename': 'productos',
        'model': Producto,
        'headers': ['id', 'referencia', 'nombre', 'colores', 'es_paquete', 'cantidad_por_paquete'],
        'get_row': lambda o: [o.id, o.referencia, o.nombre, '|'.join(c.nombre for c in o.colores.all()), o.es_paquete, o.cantidad_por_paquete or ''],
    },
    'insumos': {
        'label': 'Insumos',
        'filename': 'insumos',
        'model': Insumo2,
        'headers': ['id', 'referencia', 'nombre', 'medida', 'colores'],
        'get_row': lambda o: [o.id, o.referencia or '', o.nombre or '', o.medida.nombre if o.medida_id else '', '|'.join(c.nombre for c in o.colores.all())],
    },
    'detalle_productos': {
        'label': 'Det productos',
        'filename': 'detalle_productos',
        'model': ProductoInsumo,
        'headers': ['id', 'producto_id', 'producto_referencia', 'producto_nombre', 'insumo_id', 'insumo_referencia', 'insumo_nombre', 'color_id', 'color_nombre', 'cantidad', 'delete'],
        'get_row': lambda o: [
            o.id,
            o.producto_id,
            o.producto.referencia,
            o.producto.nombre,
            o.insumo_id,
            o.insumo.referencia or '',
            o.insumo.nombre or '',
            o.color_id or '',
            o.color.nombre if o.color_id else '',
            o.cantidad,
            '',  # delete: vacío en export; poner True para eliminar al importar
        ],
    },
}


def export_csv_view(request):
    """Descarga CSV de la entidad indicada (entity=clientes|manualistas|proveedores|productos|insumos|detalle_productos)."""
    entity = request.GET.get('entity', '')
    if entity not in EXPORT_ENTITIES:
        return HttpResponse('Entidad no válida', status=400)
    conf = EXPORT_ENTITIES[entity]
    qs = conf['model'].objects.all().order_by('id')
    if entity == 'productos':
        qs = qs.prefetch_related('colores')
    elif entity == 'insumos':
        qs = qs.select_related('medida').prefetch_related('colores')
    elif entity == 'detalle_productos':
        qs = qs.select_related('producto', 'insumo', 'color')
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(conf['headers'])
    for obj in qs:
        row = [str(v) for v in conf['get_row'](obj)]
        writer.writerow(row)
    response = HttpResponse(buffer.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{conf["filename"]}.csv"'
    return response


def _import_clientes(reader, created_count, updated_count, errors, deleted_count=None):
    for i, row in enumerate(reader, start=2):
        if len(row) < 4:
            continue
        try:
            row_id = row[0].strip() if len(row) > 0 else ''
            tipo_doc = (row[1].strip() or 'CC') if len(row) > 1 else 'CC'
            doc = row[2].strip() if len(row) > 2 else None
            nombre = row[3].strip() if len(row) > 3 else ''
            telefono = row[4].strip() if len(row) > 4 else None
            email = row[5].strip() if len(row) > 5 else None
            direccion = row[6].strip() if len(row) > 6 else None
            if not nombre:
                errors.append(f"Fila {i}: nombre obligatorio")
                continue
            obj = None
            if row_id and row_id.isdigit():
                obj = Cliente.objects.filter(id=int(row_id)).first()
            if not obj:
                obj = Cliente.objects.filter(nombre=nombre).first()
            if obj:
                obj.tipo_documento = tipo_doc or 'CC'
                obj.documento = doc or None
                obj.nombre = nombre
                obj.telefono = telefono or None
                obj.email = email or None
                obj.direccion = direccion or None
                obj.save()
                updated_count[0] += 1
            else:
                Cliente.objects.create(
                    tipo_documento=tipo_doc or 'CC',
                    documento=doc,
                    nombre=nombre,
                    telefono=telefono,
                    email=email,
                    direccion=direccion,
                )
                created_count[0] += 1
        except Exception as e:
            errors.append(f"Fila {i}: {str(e)}")


def _import_manualistas(reader, created_count, updated_count, errors, deleted_count=None):
    for i, row in enumerate(reader, start=2):
        if len(row) < 4:
            continue
        try:
            row_id = row[0].strip() if len(row) > 0 else ''
            tipo_doc = (row[1].strip() or 'CC') if len(row) > 1 else 'CC'
            doc = row[2].strip() if len(row) > 2 else None
            nombre = row[3].strip() if len(row) > 3 else ''
            telefono = row[4].strip() if len(row) > 4 else None
            email = row[5].strip() if len(row) > 5 else None
            direccion = row[6].strip() if len(row) > 6 else None
            if not nombre:
                errors.append(f"Fila {i}: nombre obligatorio")
                continue
            obj = None
            if row_id and row_id.isdigit():
                obj = Manualista.objects.filter(id=int(row_id)).first()
            if not obj:
                obj = Manualista.objects.filter(nombre=nombre).first()
            if obj:
                obj.tipo_documento = tipo_doc or 'CC'
                obj.documento = doc or None
                obj.nombre = nombre
                obj.telefono = telefono or None
                obj.email = email or None
                obj.direccion = direccion or None
                obj.save()
                updated_count[0] += 1
            else:
                Manualista.objects.create(
                    tipo_documento=tipo_doc or 'CC',
                    documento=doc,
                    nombre=nombre,
                    telefono=telefono,
                    email=email,
                    direccion=direccion,
                )
                created_count[0] += 1
        except Exception as e:
            errors.append(f"Fila {i}: {str(e)}")


def _import_proveedores(reader, created_count, updated_count, errors, deleted_count=None):
    for i, row in enumerate(reader, start=2):
        if len(row) < 4:
            continue
        try:
            row_id = row[0].strip() if len(row) > 0 else ''
            tipo_doc = (row[1].strip() or 'NIT') if len(row) > 1 else 'NIT'
            doc = row[2].strip() if len(row) > 2 else ''
            nombre = row[3].strip() if len(row) > 3 else ''
            contacto = row[4].strip() if len(row) > 4 else None
            telefono = row[5].strip() if len(row) > 5 else None
            email = row[6].strip() if len(row) > 6 else None
            direccion = row[7].strip() if len(row) > 7 else None
            if not nombre or not doc:
                errors.append(f"Fila {i}: nombre y documento obligatorios")
                continue
            obj = None
            if row_id and row_id.isdigit():
                obj = Proveedor.objects.filter(id=int(row_id)).first()
            if not obj:
                obj = Proveedor.objects.filter(nombre=nombre).first() or Proveedor.objects.filter(documento=doc).first()
            if obj:
                obj.tipo_documento = tipo_doc or 'NIT'
                obj.documento = doc
                obj.nombre = nombre
                obj.contacto = contacto
                obj.telefono = telefono or None
                obj.email = email or None
                obj.direccion = direccion or None
                obj.save()
                updated_count[0] += 1
            else:
                Proveedor.objects.create(
                    tipo_documento=tipo_doc or 'NIT',
                    documento=doc,
                    nombre=nombre,
                    contacto=contacto,
                    telefono=telefono,
                    email=email,
                    direccion=direccion,
                )
                created_count[0] += 1
        except Exception as e:
            errors.append(f"Fila {i}: {str(e)}")


def _import_productos(reader, created_count, updated_count, errors, deleted_count=None):
    for i, row in enumerate(reader, start=2):
        if len(row) < 3:
            continue
        try:
            row_id = row[0].strip() if len(row) > 0 else ''
            referencia = row[1].strip() if len(row) > 1 else ''
            nombre = row[2].strip() if len(row) > 2 else ''
            colores_str = row[3].strip() if len(row) > 3 else ''
            es_paquete = (row[4].strip().lower() in ('1', 'true', 'si', 'sí', 'yes')) if len(row) > 4 else False
            cant_paquete = row[5].strip() if len(row) > 5 else None
            if not referencia or not nombre:
                errors.append(f"Fila {i}: referencia y nombre obligatorios")
                continue
            obj = None
            if row_id and row_id.isdigit():
                obj = Producto.objects.filter(id=int(row_id)).first()
            if not obj:
                obj = Producto.objects.filter(referencia=referencia).first()
            colores = []
            if colores_str:
                for nom in colores_str.replace('|', ',').split(','):
                    nom = nom.strip()
                    if nom:
                        c, _ = Color.objects.get_or_create(nombre=nom, defaults={'nombre': nom})
                        colores.append(c)
            if obj:
                obj.referencia = referencia
                obj.nombre = nombre
                obj.es_paquete = es_paquete
                if cant_paquete and cant_paquete.isdigit():
                    obj.cantidad_por_paquete = int(cant_paquete)
                else:
                    obj.cantidad_por_paquete = None
                obj.save()
                if colores is not None:
                    obj.colores.set(colores)
                updated_count[0] += 1
            else:
                obj = Producto.objects.create(
                    referencia=referencia,
                    nombre=nombre,
                    es_paquete=es_paquete,
                    cantidad_por_paquete=int(cant_paquete) if cant_paquete and cant_paquete.isdigit() else None,
                )
                if colores:
                    obj.colores.set(colores)
                created_count[0] += 1
        except Exception as e:
            errors.append(f"Fila {i}: {str(e)}")


def _import_insumos(reader, created_count, updated_count, errors, deleted_count=None):
    for i, row in enumerate(reader, start=2):
        if len(row) < 3:
            continue
        try:
            row_id = row[0].strip() if len(row) > 0 else ''
            referencia = row[1].strip() if len(row) > 1 else ''
            nombre = row[2].strip() if len(row) > 2 else ''
            medida_nombre = row[3].strip() if len(row) > 3 else ''
            colores_str = row[4].strip() if len(row) > 4 else ''
            if not nombre:
                errors.append(f"Fila {i}: nombre obligatorio")
                continue
            medida = None
            if medida_nombre:
                medida, _ = Medida.objects.get_or_create(nombre=medida_nombre, defaults={'nombre': medida_nombre})
            else:
                medida = Medida.objects.first()
            if not medida:
                errors.append(f"Fila {i}: debe existir al menos una Medida en el sistema")
                continue
            colores = []
            if colores_str:
                for nom in colores_str.replace('|', ',').split(','):
                    nom = nom.strip()
                    if nom:
                        c, _ = Color.objects.get_or_create(nombre=nom, defaults={'nombre': nom})
                        colores.append(c)
            obj = None
            if row_id and row_id.isdigit():
                obj = Insumo2.objects.filter(id=int(row_id)).first()
            if not obj and referencia:
                obj = Insumo2.objects.filter(referencia=referencia).first()
            if not obj:
                obj = Insumo2.objects.filter(nombre=nombre).first()
            if obj:
                obj.referencia = referencia or None
                obj.nombre = nombre
                obj.medida = medida
                obj.save()
                if colores is not None:
                    obj.colores.set(colores)
                updated_count[0] += 1
            else:
                obj = Insumo2.objects.create(
                    referencia=referencia or None,
                    nombre=nombre,
                    medida=medida,
                )
                if colores:
                    obj.colores.set(colores)
                created_count[0] += 1
        except Exception as e:
            errors.append(f"Fila {i}: {str(e)}")


def _import_detalle_productos(reader, created_count, updated_count, errors, deleted_count=None):
    """Importa detalle de productos (ProductoInsumo). Columna delete=True elimina esa relación."""
    if deleted_count is None:
        deleted_count = [0]
    for i, row in enumerate(reader, start=2):
        if len(row) < 10:
            continue
        try:
            row_id = row[0].strip() if len(row) > 0 else ''
            producto_id = row[1].strip() if len(row) > 1 else ''
            producto_ref = row[2].strip() if len(row) > 2 else ''
            insumo_id = row[4].strip() if len(row) > 4 else ''
            insumo_ref = row[5].strip() if len(row) > 5 else ''
            color_id = row[7].strip() if len(row) > 7 else ''
            color_nombre = row[8].strip() if len(row) > 8 else ''
            cantidad_str = row[9].strip() if len(row) > 9 else '1'
            delete_val = row[10].strip().lower() if len(row) > 10 else ''
            delete = delete_val in ('1', 'true', 'si', 'sí', 'yes', 'eliminar')

            if delete:
                obj = None
                if row_id and row_id.isdigit():
                    obj = ProductoInsumo.objects.filter(id=int(row_id)).first()
                if not obj and (producto_id or producto_ref) and (insumo_id or insumo_ref):
                    try:
                        prod = Producto.objects.get(id=int(producto_id)) if producto_id.isdigit() else Producto.objects.get(referencia=producto_ref)
                        ins = Insumo2.objects.get(id=int(insumo_id)) if insumo_id.isdigit() else Insumo2.objects.get(referencia=insumo_ref)
                        if color_id or color_nombre:
                            col = Color.objects.get(id=int(color_id)) if color_id.isdigit() else Color.objects.get(nombre=color_nombre)
                            obj = ProductoInsumo.objects.filter(producto=prod, insumo=ins, color=col).first()
                        else:
                            obj = ProductoInsumo.objects.filter(producto=prod, insumo=ins, color__isnull=True).first()
                    except (Producto.DoesNotExist, Insumo2.DoesNotExist, Color.DoesNotExist, ValueError):
                        pass
                if obj:
                    obj.delete()
                    deleted_count[0] += 1
                else:
                    errors.append(f"Fila {i}: no se encontró el detalle para eliminar (id o producto/insumo/color).")
                continue

            producto = None
            if producto_id.isdigit():
                producto = Producto.objects.filter(id=int(producto_id)).first()
            if not producto and producto_ref:
                producto = Producto.objects.filter(referencia=producto_ref).first()
            if not producto:
                errors.append(f"Fila {i}: producto no encontrado (id o referencia).")
                continue

            insumo = None
            if insumo_id.isdigit():
                insumo = Insumo2.objects.filter(id=int(insumo_id)).first()
            if not insumo and insumo_ref:
                insumo = Insumo2.objects.filter(referencia=insumo_ref).first()
            if not insumo:
                errors.append(f"Fila {i}: insumo no encontrado (id o referencia).")
                continue

            color = None
            if color_id.isdigit():
                color = Color.objects.filter(id=int(color_id)).first()
            elif color_nombre:
                color, _ = Color.objects.get_or_create(nombre=color_nombre, defaults={'nombre': color_nombre})

            cantidad = int(cantidad_str) if cantidad_str.isdigit() else 1
            if cantidad < 1:
                errors.append(f"Fila {i}: cantidad debe ser >= 1.")
                continue

            pi, created = ProductoInsumo.objects.get_or_create(
                producto=producto,
                insumo=insumo,
                color=color,
                defaults={'cantidad': cantidad}
            )
            if created:
                created_count[0] += 1
            else:
                pi.cantidad = cantidad
                pi.save()
                updated_count[0] += 1
        except Exception as e:
            errors.append(f"Fila {i}: {str(e)}")


IMPORT_HANDLERS = {
    'clientes': _import_clientes,
    'manualistas': _import_manualistas,
    'proveedores': _import_proveedores,
    'productos': _import_productos,
    'insumos': _import_insumos,
    'detalle_productos': _import_detalle_productos,
}


def importar_exportar_view(request):
    """Vista principal: exportar CSV o importar CSV (guardar/editar en masa)."""
    if request.method == 'POST' and request.FILES.get('archivo'):
        entity = request.POST.get('entity', '')
        if entity not in IMPORT_HANDLERS:
            messages.error(request, 'Entidad no válida.')
            return redirect('importar_exportar')
        archivo = request.FILES['archivo']
        if not archivo.name.lower().endswith('.csv'):
            messages.error(request, 'Solo se aceptan archivos CSV.')
            return redirect('importar_exportar')
        try:
            content = archivo.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                content = archivo.read().decode('latin-1')
            except Exception:
                messages.error(request, 'No se pudo decodificar el archivo. Use UTF-8.')
                return redirect('importar_exportar')
        reader = csv.reader(io.StringIO(content))
        headers = next(reader, None)
        created_count = [0]
        updated_count = [0]
        deleted_count = [0]
        errors = []
        IMPORT_HANDLERS[entity](reader, created_count, updated_count, errors, deleted_count)
        if errors:
            for err in errors[:20]:
                messages.warning(request, err)
            if len(errors) > 20:
                messages.warning(request, f'... y {len(errors) - 20} errores más.')
        msg = f"✅ Se importó de forma exitosa. {created_count[0]} registro(s) creado(s), {updated_count[0]} actualizado(s)."
        if deleted_count[0] > 0:
            msg += f" {deleted_count[0]} eliminado(s)."
        messages.success(request, msg)
        return redirect('importar_exportar')

    return render(request, 'importar_exportar.html', {
        'export_entities': EXPORT_ENTITIES,
    })

