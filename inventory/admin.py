from django.contrib import admin
from .models import (
    Category,
    Warehouse,
    Location,
    UnitOfMeasure,
    Product,
    StockRecord,
    Receipt,
    ReceiptItem,
    DeliveryOrder,
    DeliveryItem,
    InventoryAdjustment,
    AdjustmentItem,
    InternalTransfer,
    TransferItem,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name", "description"]
    date_hierarchy = "created_at"


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "location", "is_active", "created_at"]
    list_filter = ["is_active", "location"]
    search_fields = ["name", "code", "location"]
    date_hierarchy = "created_at"


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "warehouse", "is_active"]
    list_filter = ["warehouse", "is_active"]
    search_fields = ["name", "warehouse__name", "code"]
    autocomplete_fields = ["warehouse"]


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ["name", "symbol"]
    search_fields = ["name", "symbol"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "category", "uom", "is_active", "created_at"]
    list_filter = ["category", "uom", "is_active"]
    search_fields = ["name", "sku", "description"]
    date_hierarchy = "created_at"
    autocomplete_fields = ["category", "uom"]


@admin.register(StockRecord)
class StockRecordAdmin(admin.ModelAdmin):
    list_display = ["product", "location", "current_stock", "reorder_point", "maximum_stock", "last_counted"]
    list_filter = ["location", "product__category"]
    search_fields = ["product__name", "product__sku", "location__name"]
    autocomplete_fields = ["product", "location"]
    date_hierarchy = "last_counted"


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ["reference_number", "supplier", "status", "received_at", "created_by"]
    list_filter = ["status", "received_at"]
    search_fields = ["reference_number", "supplier", "notes"]
    date_hierarchy = "received_at"
    autocomplete_fields = ["created_by"]


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = ["receipt", "product", "quantity", "unit_price", "total_price"]
    search_fields = ["receipt__reference_number", "product__name", "batch_number"]
    autocomplete_fields = ["receipt", "product"]


@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ["reference_number", "customer_name", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["reference_number", "customer_name", "notes"]
    date_hierarchy = "created_at"
    autocomplete_fields = ["created_by"]


@admin.register(DeliveryItem)
class DeliveryItemAdmin(admin.ModelAdmin):
    list_display = ["delivery", "product", "quantity", "unit_price", "total_price"]
    search_fields = ["delivery__reference_number", "product__name"]
    autocomplete_fields = ["delivery", "product"]


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = ["reference_number", "adjustment_type", "status", "reason", "created_at"]
    list_filter = ["adjustment_type", "status", "created_at"]
    search_fields = ["reference_number", "reason", "notes"]
    date_hierarchy = "created_at"


@admin.register(AdjustmentItem)
class AdjustmentItemAdmin(admin.ModelAdmin):
    list_display = ["adjustment", "product", "location", "quantity_change", "previous_stock", "new_stock"]
    search_fields = ["adjustment__reference_number", "product__name"]
    autocomplete_fields = ["adjustment", "product", "location"]


@admin.register(InternalTransfer)
class InternalTransferAdmin(admin.ModelAdmin):
    list_display = ["reference_number", "from_location", "to_location", "status", "quantity", "created_at"]
    list_filter = ["status", "from_location", "to_location", "created_at"]
    search_fields = ["reference_number", "notes"]
    date_hierarchy = "created_at"
    autocomplete_fields = ["from_location", "to_location"]


@admin.register(TransferItem)
class TransferItemAdmin(admin.ModelAdmin):
    list_display = ["transfer", "product", "quantity"]
    search_fields = ["transfer__reference_number", "product__name"]