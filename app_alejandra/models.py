from django.db import models

class Color(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Medida(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Referencia(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Nombre(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Insumo(models.Model):
    imagen_url = models.CharField(max_length=500, blank=True, null=True)  # Guardará la URL de la imagen
    referencia = models.ForeignKey('Referencia', on_delete=models.CASCADE)
    nombre = models.ForeignKey('Nombre', on_delete=models.CASCADE)
    medida = models.ForeignKey('Medida', on_delete=models.CASCADE)
    colores = models.ManyToManyField('Color')

    def __str__(self):
        return f"Insumo: {self.nombre.nombre}, Referencia: {self.referencia.nombre}"
    
class Insumo2(models.Model):
    imagen_url = models.CharField(max_length=500, blank=True, null=True)  # Guardará la URL de la imagen
    referencia = models.CharField(max_length=500, unique=True, null=True) 
    nombre = models.CharField(max_length=500, null=True) 
    medida = models.ForeignKey('Medida', on_delete=models.CASCADE)
    colores = models.ManyToManyField('Color')

    def __str__(self):
        return f"Insumo: {self.nombre}, Referencia: {self.referencia}"

class Producto(models.Model):
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    referencia = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=100)
    colores = models.ManyToManyField(Color)

    # NUEVOS CAMPOS
    es_paquete = models.BooleanField(default=False)
    cantidad_por_paquete = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Producto: {self.nombre} (Ref: {self.referencia})"

class ProductoInsumo(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    insumo = models.ForeignKey(Insumo2, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    color = models.ForeignKey('Color', on_delete=models.CASCADE, null=True, blank=True)  # 👈 NUEVO

    def __str__(self):
        return f"{self.producto.nombre} necesita {self.cantidad} de {self.insumo.nombre} ({self.color})"

class Proveedor(models.Model):
    TIPOS_DOCUMENTO = [
        ('CC', 'Cédula de Ciudadanía'),
        ('NIT', 'Número de Identificación Tributaria'),
        ('CE', 'Cédula de Extranjería'),
        ('PAS', 'Pasaporte'),
    ]

    tipo_documento = models.CharField(max_length=3, choices=TIPOS_DOCUMENTO, default='NIT')
    documento = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200, unique=True)
    contacto = models.CharField(max_length=200, blank=True, null=True, help_text="Persona responsable/contacto directo")
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} - {self.documento}"


class Compra(models.Model):
    proveedor = models.ForeignKey('Proveedor', on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    numero = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="Ej: CO-0001")

    def __str__(self):
        return f"{self.numero or self.id} - {self.proveedor.nombre} - {self.fecha.strftime('%d/%m/%Y')}"

class CompraInsumo(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, null=True, blank=True)
    produccion = models.ForeignKey('Produccion', on_delete=models.CASCADE, null=True, blank=True)
    insumo = models.ForeignKey('Insumo2', on_delete=models.CASCADE)
    color = models.ForeignKey('Color', on_delete=models.CASCADE, default=1)  # Usar un ID válido
    cantidad = models.IntegerField()
    medida = models.ForeignKey('Medida', on_delete=models.CASCADE)
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ESTADO_CHOICES = [
        ('Compra', 'Compra'),
        ('Reserva Producción', 'Reserva Producción'),
        ('Cancelado', 'Cancelado'),
        ('Terminado', 'Terminado'),
    ]
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default='Compra')

    def total(self):
        return self.cantidad * self.valor_unitario

    def __str__(self):
        compra_str = f"Compra {self.compra.id}" if self.compra else (f"Producción {self.produccion.id}" if self.produccion else "Sin Origen")
        return f"{compra_str} - {self.insumo.nombre} ({self.cantidad} {self.medida.nombre}) - {self.color.nombre}"

class Cliente(models.Model):
    TIPOS_DOCUMENTO = [
        ('CC', 'Cédula de Ciudadanía'),
        ('NIT', 'Número de Identificación Tributaria'),
        ('CE', 'Cédula de Extranjería'),
        ('PAS', 'Pasaporte'),
        ('SIN', 'Sin Documento'),
    ]

    tipo_documento = models.CharField(max_length=3, choices=TIPOS_DOCUMENTO, default='CC')
    documento = models.CharField(max_length=50, blank=True, null=True, help_text="Opcional - puede quedar vacío")
    nombre = models.CharField(max_length=200, unique=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.documento:
            return f"{self.nombre} - {self.documento}"
        else:
            return f"{self.nombre} - Sin documento"

class Manualista(models.Model):
    TIPOS_DOCUMENTO = [
        ('CC', 'Cédula de Ciudadanía'),
        ('NIT', 'Número de Identificación Tributaria'),
        ('CE', 'Cédula de Extranjería'),
        ('PAS', 'Pasaporte'),
        ('SIN', 'Sin Documento'),
    ]

    tipo_documento = models.CharField(max_length=3, choices=TIPOS_DOCUMENTO, default='CC')
    documento = models.CharField(max_length=50, blank=True, null=True, help_text="Opcional - puede quedar vacío")
    nombre = models.CharField(max_length=200, unique=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)  # Campo opcional

    def __str__(self):
        if self.documento:
            return f"{self.nombre} - {self.documento}"
        else:
            return f"{self.nombre} - Sin documento"

class EstadoProduccion(models.TextChoices):
    PENDIENTE = 'Pendiente', 'Pendiente'
    EN_PROCESO = 'En proceso', 'En proceso'
    TERMINADO = 'Terminado', 'Terminado'

class Produccion(models.Model):
    manualista = models.ForeignKey('Manualista', on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_tentativa = models.DateField()
    estado = models.CharField(max_length=20, choices=EstadoProduccion.choices, default=EstadoProduccion.PENDIENTE)
    valor_a_pagar = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, help_text="Monto acordado a pagar al manualista por esta orden")
    numero = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="Ej: PR-0001")

    def __str__(self):
        return f"{self.numero or self.id} - {self.manualista.nombre} - {self.estado}"

    def total_pagado(self):
        from django.db.models import Sum
        total = self.pagos.aggregate(s=Sum('monto'))['s'] or 0
        return total

    def pendiente_pago(self):
        valor = self.valor_a_pagar or 0
        return max(0, float(valor) - float(self.total_pagado()))

class LineaProduccion(models.Model):
    produccion = models.ForeignKey(Produccion, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    color = models.ForeignKey('Color', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    cantidad_entregada = models.PositiveIntegerField(default=0, help_text="Cantidad ya entregada por el manualista")

    def __str__(self):
        return f"{self.produccion} - {self.producto.nombre} ({self.color.nombre}) x {self.cantidad}"
    
    @property
    def cantidad_pendiente(self):
        return self.cantidad - self.cantidad_entregada
    
    @property
    def porcentaje_completado(self):
        if self.cantidad == 0:
            return 0
        return round((self.cantidad_entregada / self.cantidad) * 100, 1)

class EntregaParcial(models.Model):
    linea_produccion = models.ForeignKey(LineaProduccion, on_delete=models.CASCADE, related_name='entregas_parciales')
    cantidad_entregada = models.PositiveIntegerField()
    fecha_entrega = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True, null=True, help_text="Observaciones sobre la entrega")

    def __str__(self):
        return f"Entrega {self.id} - {self.linea_produccion.producto.nombre} - {self.cantidad_entregada} unidades"


class PagoProduccion(models.Model):
    """Pago realizado a un manualista por una orden de producción."""
    produccion = models.ForeignKey(Produccion, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField()
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Pago {self.monto} - Orden #{self.produccion_id} - {self.fecha}"


class AjusteInsumo(models.Model):
    """Registro de ajuste de insumos en una orden: más enviados al manualista o sobrantes devueltos."""
    TIPO_CHOICES = [
        ('envio_extra', 'Se envían más insumos'),
        ('sobrante', 'Sobran insumos'),
    ]
    produccion = models.ForeignKey(Produccion, on_delete=models.CASCADE, related_name='ajustes_insumos')
    insumo = models.ForeignKey('Insumo2', on_delete=models.CASCADE)
    color = models.ForeignKey('Color', on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad = models.PositiveIntegerField()
    observaciones = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        tipo_label = dict(self.TIPO_CHOICES).get(self.tipo, self.tipo)
        return f"Orden #{self.produccion_id} - {self.insumo.nombre} ({self.color.nombre}): {tipo_label} {self.cantidad}"

class EstadoProducto(models.TextChoices):
    EN_PRODUCCION = 'En producción', 'En producción'
    TERMINADO = 'Terminado', 'Terminado'
    VENDIDO = 'Vendido', 'Vendido'

class Venta(models.Model):
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    numero = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="Ej: FA-0001")

    def __str__(self):
        return f"{self.numero or self.id} - {self.cliente.nombre} - {self.fecha.strftime('%d/%m/%Y')}"


class LineaVenta(models.Model):
    """Línea de una venta: producto, color, cantidad vendida y cantidad ya despachada."""
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    color = models.ForeignKey('Color', on_delete=models.CASCADE, null=True, blank=True)
    cantidad = models.PositiveIntegerField()
    cantidad_despachada = models.PositiveIntegerField(default=0)
    valor_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        color_str = self.color.nombre if self.color else "Sin color"
        return f"Venta {self.venta_id} - {self.producto.nombre} ({color_str}) x {self.cantidad}"

    @property
    def cantidad_pendiente(self):
        return self.cantidad - self.cantidad_despachada

    @property
    def porcentaje_despachado(self):
        if self.cantidad == 0:
            return 0
        return round((self.cantidad_despachada / self.cantidad) * 100, 1)


class DespachoVenta(models.Model):
    """Registro de un despacho parcial sobre una línea de venta."""
    linea_venta = models.ForeignKey(LineaVenta, on_delete=models.CASCADE, related_name='despachos')
    cantidad_despachada = models.PositiveIntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Despacho {self.id} - {self.linea_venta.producto.nombre} - {self.cantidad_despachada} uds"


class InventarioProducto(models.Model):
    produccion = models.ForeignKey('Produccion', on_delete=models.CASCADE, null=True, blank=True)
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    color = models.ForeignKey('Color', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    estado = models.CharField(max_length=20, choices=EstadoProducto.choices, default=EstadoProducto.EN_PRODUCCION)
    valor_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.produccion} {self.producto.nombre} ({self.color.nombre}) x {self.cantidad} - {self.estado}"
    

