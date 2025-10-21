from django.db import models
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


# Create your models here.
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    first_name= models.CharField(max_length=30)
    last_name= models.CharField(max_length=30)
    phone_number = PhoneNumberField(blank=True)
    address = models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_active=models.BooleanField(default=True)
    ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('vendor', 'Vendor'),
    ('customer', 'Customer'),
    ('driver', 'Driver'),
]   
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    def get_full_name(self):
       return f"{self.first_name} {self.last_name}".strip()
   
   
   
    
class CustomerProfile(models.Model):
    user=models.OneToOneField(CustomUser,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='customer_profile')
    
    class Meta:
        verbose_name = _('customer profile')
        verbose_name_plural = _('customer profiles')
        
    
    default_payment_method = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Customer Profile: {self.user.get_full_name()}"
    
    def clean(self):
        if self.user.role != "customer":
            raise ValidationError("This user is not a customer.")

    def save(self, *args, **kwargs):
        self.full_clean()  # calls clean()
        super().save(*args, **kwargs)
    
    
    
    
class VendorProfile(models.Model):
    user=models.OneToOneField(CustomUser,on_delete=models.CASCADE,primary_key=True,related_name='vendor_profile')
    class Meta:
        verbose_name = _('vendor profile')
        verbose_name_plural = _('vendor profiles')
        
    store_name=models.CharField(max_length=100)

    store_description=models.TextField(blank=True, verbose_name=_('store description'))

    store_logo =models.ImageField(upload_to='vendor_logos/', null=True, blank=True, verbose_name=_('company logo'))


    business_address=models.CharField(max_length=200)

    is_verified =models.BooleanField(default=False)
    #(bool — admin approves vendors)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_vendors')
    
    
def clean(self):
        if self.user.role !="vendor":
            raise ValidationError("This user is not a vendor.")

def save(self, *args, **kwargs):
        self.full_clean()  # calls clean()
        super().save(*args, **kwargs)
    
    
    
def __str__(self):
        return f"Vendor Profile: {self.store_name}"
    
    
    
class DriverProfile(models.Model):
    user=models.OneToOneField(CustomUser,on_delete=models.CASCADE,primary_key=True,related_name='driver_profile')
    class Meta:
        verbose_name = _('driver profile')
        verbose_name_plural = _('driver profiles')
    vehicle_type = models.CharField(
    max_length=20,
    choices=[
        ("bike", "Bike"),
        ("car", "Car"),
        ("truck", "Truck"),
    ]
)
    license_number=models.CharField(max_length=50)
    availability_status = models.CharField(
    max_length=15,
    choices=[
        ("available", "Available"),
        ("unavailable", "Unavailable"),
    ],
    default="available"
)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    
    
    def __str__(self):
        return f"Driver Profile: {self.user.get_full_name}"
    def clean(self):
        if self.user.role != "driver":
            raise ValidationError("This user is not a driver.")

    def save(self, *args, **kwargs):
        self.full_clean()  # calls clean()
        super().save(*args, **kwargs)
        
class Category(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True,null=True)
    
        
        
        
class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10,decimal_places=2)
    description = models.TextField(blank=True,null=True)
    stock = models.PositiveIntegerField()
    is_available=models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    vendor=models.ForeignKey(VendorProfile,on_delete=models.CASCADE)
    category=models.ForeignKey(Category,on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name
    
    


class Cart (models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    
    
    
class CartItem(models.Model):
    cart=models.ForeignKey(Cart,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.PROTECT)
    quantity=models.PositiveIntegerField()
    
    
    @property
    
    def item_subtotal(self):
        return self.product.price * self.quantity
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in order {self.order.order_id}"
    
    
    
class Order(models.Model):
    
    order_number=models.CharField(max_length=100, unique=True, editable=False)
    class statueschoices(models.TextChoices):
        PENDING ='pending'
        CONFIRMED = 'confirmed'
        SHIPED='shiped'
        DELIVERED='delivered'
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    driver=models.ForeignKey(DriverProfile,on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    statue=models.CharField(max_length=10,
                            choices=statueschoices.choices,
                            default=statueschoices.PENDING)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate: ORD-20251004-12345
            import random
            from django.utils import timezone
            date = timezone.now().strftime('%Y%m%d')
            rand = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            self.order_number = f"ORD-{date}-{rand}"
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)  # keep history safe
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    def item_subtotal(self):
        return self.price_at_purchase * self.quantity
    
    
    
    
    #payement
    


import uuid

class Payment(models.Model):
    CARD_TYPE_CHOICES = [
        ('dahabia', 'Dahabia'),
        ('cib', 'CIB'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    card_type = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Mock card details (last 4 digits only for display)
    card_last_four = models.CharField(max_length=4, blank=True, null=True)
    
    # Transaction details
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method_details = models.JSONField(default=dict, blank=True)
    
    # Metadata
    order_reference = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.card_type.upper()} - {self.amount} DZD - {self.status}"


class PaymentLog(models.Model):
    """Track all payment status changes"""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20)
    message = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.payment.id} - {self.status} at {self.timestamp}"