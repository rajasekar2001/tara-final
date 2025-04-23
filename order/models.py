from django.db import models
from django.utils.translation import gettext_lazy as _
from user.models import ResUser  as user
from django.conf import settings
from django.apps import apps
from django.db.models.signals import post_save
from django.contrib.auth.models import AbstractUser, Permission, Group
from user.models import ResUser
from SuperAdmin.models import SuperAdmin
from BusinessPartner.models import BusinessPartner
from Users.models import Users
from django.utils.timezone import now
from django.conf import settings
from django.dispatch import receiver
from datetime import date
from django.utils import timezone
import pytz
from django.core.exceptions import ValidationError






class YourModel(models.Model):
    your_datetime_field = models.DateTimeField(default=now, blank=True, null=True)


def get_order_no():
    last_order = Order.objects.order_by('-id').first()
    if last_order and last_order.order_no.startswith('WR'):
        order_number = int(last_order.order_no[2:]) + 1
        return f"WR{order_number:03d}"
    return "WR001"

def current_user(request):
    current_user = user.objects.get(id=request.user.id)
    user_type = current_user.ROLE_CHOICES
    return current_user, user_type

def filter_queryset(user, user_type):
    if user_type in ['customer', 'staff']:
        return Order.objects.filter(user=user)
    elif user_type == 'admin':
        return Order.objects.filter(user=user)
    elif user_type == 'superadmin':
        return Order.objects.all()
    else:
        return Order.objects.none()

class User(AbstractUser):
    role_name = models.CharField(max_length=20, choices=[('admin', 'Admin'), ('superadmin', 'Super Admin'), ('keyuser', 'Key User'), ('user', 'User')], default='user')
    groups = models.ManyToManyField(
        Group,
        related_name="order_users",
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="order_user_permissions",
        blank=True
    )

class Order(models.Model):
    SIZE_CHOICES = [
        ('Large', 'Large'),
        ('Medium', 'Medium'),
        ('Small', 'Small'),
    ]

    SCREW_CHOICES = [
        ('Closed', 'Closed'),
        ('Open', 'Open'),
    ]

    HOOK_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
    ]

    RODIUM_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
    ]

    HALLMARK_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
    ]

    STONE_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
    ]

    CATEGORY_CHOICES = [
        ('Rings', 'Rings'),
        ('Chains', 'Chains'),
        ('Pendants', 'Pendants'),
        ('Bangles', 'Bangles'),
        ('Anklets', 'Anklets'),
        ('Necklaces', 'Necklaces'),
        ('Bracelets', 'Bracelets'),
        ('Earrings', 'Earrings'),
    ]

    WEIGHT_UNIT_CHOICES = [
        ('mg', 'Milligram'),
        ('g', 'Gram'),
        ('kg', 'Kilogram'),
        ('oz', 'Ounce'),
        ('lb', 'Pound'),
    ]
    ORDER_TYPES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('preorder', 'Preorder'),
    ]
    DTYPE_CHOICES = [
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('custom', 'Custom'),
    ]
    
    OPEN_CLOSE_CHOICES = [
        ('open', 'Open'),
        ('close', 'Close'),
    ]
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in-process', 'In Process'),
        ("awaiting-approval", "Awaiting Approval"),
        ('completed', 'Completed'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name='orders', blank=True, null=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    order_image = models.ImageField(upload_to='order_images/', verbose_name="Add Images", blank=True, null=True)
    # bp_code = models.CharField(max_length=20, unique=True, blank=True, null=True) 
    order_no = models.CharField(max_length=10, unique=True, blank=True, null=True)
    bp_code = models.ForeignKey(BusinessPartner, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    state = models.CharField(max_length=50, choices=[('draft', 'Draft'), ('pending', 'Pending')])
    name = models.CharField(max_length=255)
    reference_no = models.CharField(max_length=20, unique=True)
    order_date = models.DateTimeField(default=timezone.now, editable=False)
    due_date = models.DateField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPES, default='online')
    quantity = models.CharField(max_length=50, blank=True, null=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    dtype = models.CharField(max_length=10, choices=DTYPE_CHOICES, default='standard')
    branch_code = models.CharField(max_length=10, unique=True)
    product = models.CharField(max_length=100)
    design = models.CharField(max_length=100)
    vendor_design = models.CharField(max_length=100)
    barcoded_quality = models.BooleanField(default=False)
    supplied = models.IntegerField(default=0)
    balance = models.IntegerField(default=0)
    assigned_by = models.CharField(max_length=100, default="Unknown")
    narration = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    sub_brand = models.CharField(max_length=100, blank=True, null=True)
    make = models.CharField(max_length=100, blank=True, null=True)
    work_style = models.CharField(max_length=100, blank=True, null=True)
    form = models.CharField(max_length=100, blank=True, null=True)
    finish = models.CharField(max_length=100, blank=True, null=True)
    theme = models.CharField(max_length=100, blank=True, null=True)
    collection = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    assign_remarks = models.TextField(blank=True, null=True)
    screw = models.CharField(max_length=50, choices=SCREW_CHOICES, blank=True, null=True)
    polish = models.CharField(max_length=100, blank=True, null=True)
    metal_colour = models.CharField(max_length=50, blank=True, null=True)
    purity = models.CharField(max_length=50, blank=True, null=True)
    stone = models.CharField(max_length=50, choices=STONE_CHOICES, blank=True, null=True)
    hallmark = models.CharField(max_length=50, choices=HALLMARK_CHOICES, blank=True, null=True)
    rodium = models.CharField(max_length=50, choices=RODIUM_CHOICES, blank=True, null=True)
    enamel = models.CharField(max_length=50, blank=True, null=True)
    hook = models.CharField(max_length=50, choices=HOOK_CHOICES, blank=True, null=True)
    size = models.CharField(max_length=50, choices=SIZE_CHOICES, blank=True, null=True)
    open_close = models.CharField(max_length=10, choices=OPEN_CLOSE_CHOICES, default='open')
    length = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    hbt_class = models.CharField(max_length=50, blank=True, null=True)
    console_id = models.CharField(max_length=50, blank=True, null=True)
    tolerance_from = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tolerance_to = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    craftsman = models.ForeignKey(BusinessPartner, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_orders')
    rejected_by = models.ForeignKey(BusinessPartner, on_delete=models.SET_NULL, null=True, blank=True, related_name="rejected_orders")
    
    def clean(self):
        super().clean()
        if self.due_date and self.due_date <= timezone.now().date():
            raise ValidationError("Due date must be in the future")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        if not self.order_no:
            self.order_no = get_order_no()
        if not self.bp_code:
            self.bp_code = f"BP{self.order_no}"  
        super().save(*args, **kwargs)
        
    def save(self, *args, **kwargs):
        if not self.id:  # Only on creation
            ist = pytz.timezone('Asia/Kolkata')  # Indian Standard Time
            self.order_date = timezone.now().astimezone(ist)
        super().save(*args, **kwargs)
        
    def __str__(self):
        weight_display = f"{self.weight}{self.weight_unit}" if self.weight and self.weight_unit else "No weight specified"
        return f"Order {self.order_no}-{self.category}-{weight_display}"
    
    def __str__(self):
        return f"Order {self.order_no} - {self.bp_code.bp_code}"
    
    def __str__(self):
        return f"Order {self.order_no} - {self.order_date}"
    
    def __str__(self):
        return f"Order {self.order_no} - {self.bp_code.bp_code if self.bp_code else 'No BP Code'}"
    
    def __str__(self):
        return f"Order {self.order_no} - {self.bp_code.bp_code if self.bp_code else 'No BP Code'} - {self.order_date}"

    def __str__(self):
        return f"Order {self.id} - {self.order_date}"
    
    def __str__(self):
        return f"Order #{self.id} - {self.order_date.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def __str__(self):
        return f"Order {self.order_no}"
    
    
class Craftsman(models.Model):
    full_name = models.CharField(max_length=100)
    bp_code = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.full_name