from django.contrib import admin
from .models import Color, Insumo2, Medida, Producto, ProductoInsumo, Proveedor, Compra, CompraInsumo
from .models import Cliente, Manualista,  Produccion, LineaProduccion, InventarioProducto

admin.site.register(Color)
admin.site.register(Medida)
admin.site.register(Insumo2)
admin.site.register(Producto)
admin.site.register(ProductoInsumo)
admin.site.register(Proveedor)
admin.site.register(Compra)
admin.site.register(CompraInsumo)
admin.site.register(Cliente)
admin.site.register(Manualista)
admin.site.register(Produccion)
admin.site.register(LineaProduccion)
admin.site.register(InventarioProducto)
