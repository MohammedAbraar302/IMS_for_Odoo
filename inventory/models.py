from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="Warehouse code/ID")
    location = models.CharField(max_length=200, blank=True, help_text="City, state, or address")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Location(models.Model):
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="locations"
    )
    name = models.CharField(max_length=100, help_text="e.g., Main Aisle, Rack A, Floor")
    code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        unique_together = ("warehouse", "name")

    def __str__(self):
        return f"{self.warehouse.name} - {self.name}"


class UnitOfMeasure(models.Model):
    name = models.CharField(max_length=20, unique=True, help_text="e.g., pcs, kg, liters, boxes")
    symbol = models.CharField(max_length=10, blank=True, help_text="e.g., pc, kg, L")

    class Meta:
        verbose_name = "Unit of Measure"
        verbose_name_plural = "Units of Measure"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(
        max_length=50, unique=True, help_text="Stock Keeping Unit code"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    uom = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.sku}"


class StockRecord(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    current_stock = models.IntegerField(default=0, help_text="Current on-hand quantity")
    reorder_point = models.IntegerField(
        default=10,
        help_text="Minimum stock level that triggers reorder alert",
    )
    maximum_stock = models.IntegerField(
        default=1000,
        help_text="Maximum stock level to prevent overstocking",
    )
    last_counted = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock Record"
        verbose_name_plural = "Stock Records"
        unique_together = ("product", "location")

    def __str__(self):
        return f"{self.product.name} @ {self.location} - Stock: {self.current_stock}"

    def can_fulfill(self, quantity):
        return self.current_stock >= quantity

    def reserve(self, quantity):
        if self.can_fulfill(quantity):
            self.current_stock -= quantity
            self.save()
            return True
        return False


class Receipt(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Waiting for Validation"),
        ("validated", "Validated"),
        ("cancelled", "Cancelled"),
    ]

    reference_number = models.CharField(
        max_length=50, unique=True, help_text="Auto-generated receipt number"
    )
    supplier = models.CharField(max_length=200, help_text="Supplier name")
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    received_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"
        ordering = ["-received_at"]

    def __str__(self):
        return f"Receipt {self.reference_number} - {self.supplier}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("inventory:receipt_detail", args=[self.pk])


class ReceiptItem(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, help_text="Default location for these items"
    )
    quantity = models.IntegerField(help_text="Quantity received")
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False
    )
    batch_number = models.CharField(max_length=100, blank=True)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Receipt Item"
        verbose_name_plural = "Receipt Items"

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.uom.name}"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class DeliveryOrder(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("picking", "Picking"),
        ("packed", "Packed"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    reference_number = models.CharField(
        max_length=50, unique=True, help_text="Auto-generated delivery number"
    )
    customer_name = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Delivery Order"
        verbose_name_plural = "Delivery Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Delivery {self.reference_number} - {self.customer_name or 'N/A'}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("inventory:delivery_detail", args=[self.pk])


class DeliveryItem(models.Model):
    delivery = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, help_text="Location being picked from"
    )
    quantity = models.IntegerField(help_text="Quantity to deliver")
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False
    )

    class Meta:
        verbose_name = "Delivery Item"
        verbose_name_plural = "Delivery Items"

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.uom.name}"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class InventoryAdjustment(models.Model):
    ADJUSTMENT_TYPE_CHOICES = [
        ("add", "Add Stock"),
        ("remove", "Remove Stock"),
        ("transfer", "Transfer Between Locations"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    reference_number = models.CharField(
        max_length=50, unique=True, help_text="Auto-generated adjustment number"
    )
    adjustment_type = models.CharField(
        max_length=20, choices=ADJUSTMENT_TYPE_CHOICES, default="add"
    )
    reason = models.CharField(max_length=200, help_text="Reason for adjustment")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Inventory Adjustment"
        verbose_name_plural = "Inventory Adjustments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Adjustment {self.reference_number} - {self.get_adjustment_type_display()}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("inventory:adjustment_detail", args=[self.pk])


class AdjustmentItem(models.Model):
    adjustment = models.ForeignKey(
        InventoryAdjustment, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, help_text="Affected location"
    )
    quantity_change = models.IntegerField(
        help_text="Positive for add, negative for remove, net for transfer"
    )
    previous_stock = models.IntegerField(default=0)
    new_stock = models.IntegerField(default=0)
    reason_detail = models.TextField(blank=True)

    class Meta:
        verbose_name = "Adjustment Item"
        verbose_name_plural = "Adjustment Items"

    def __str__(self):
        return f"{self.product.name} - Change: {self.quantity_change}"


class InternalTransfer(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("in_transit", "In Transit"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    reference_number = models.CharField(
        max_length=50, unique=True, help_text="Auto-generated transfer number"
    )
    from_location = models.ForeignKey(
        Location, on_delete=models.PROTECT,
        related_name="transfers_out", help_text="Source location"
    )
    to_location = models.ForeignKey(
        Location, on_delete=models.PROTECT,
        related_name="transfers_in", help_text="Destination location"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    quantity = models.IntegerField(help_text="Quantity being transferred")
    notes = models.TextField(blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Internal Transfer"
        verbose_name_plural = "Internal Transfers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Transfer {self.reference_number} - {self.from_location} → {self.to_location}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("inventory:transfer_detail", args=[self.pk])


class TransferItem(models.Model):
    transfer = models.ForeignKey(
        InternalTransfer, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(help_text="Quantity being transferred")

    class Meta:
        verbose_name = "Transfer Item"
        verbose_name_plural = "Transfer Items"

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"