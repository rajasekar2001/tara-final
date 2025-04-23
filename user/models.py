from django.db import models
from django.contrib.auth.models import AbstractUser, Permission, Group
from django.core.validators import RegexValidator, EmailValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group, Permission
from BusinessPartner.models import BusinessPartner
import logging
import requests
import time

logger = logging.getLogger(__name__)

def validate_mobile_no(value):
    if not value.isdigit():
        raise ValidationError(_('Mobile number must contain only digits.'))
    if not (10 <= len(value) <= 15):
        raise ValidationError(_('Mobile number must be between 10 to 15 digits.'))

class ActiveUserManager(BaseUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(delete_flag=False)

    def get_by_natural_key(self, username):
        return self.get(username=username)

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The given username must be set")
        
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")

        return self.create_user(username, password, **extra_fields)
    

class ResUser(AbstractUser):
    ROLE_CHOICES = [
        ('Project Owner', 'Project Owner'),
        ('Super Admin', 'Super Admin'),
        ('Admin', 'Admin'),
        ('Key User', 'Key User'),
        ('User', 'User'),
        ('Craftsman', 'Craftsman'),
        ('Walking Customer', 'Walking Customer'),
    ]

    GENDER_CHOICES = [('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    STATUS_CHOICES = [('active', 'Active'), ('inactive', 'Inactive')]
    USER_TYPE_CHOICES = [('internal', 'INTERNAL USER'), ('external', 'EXTERNAL USER')]

    profile_picture = models.ImageField(upload_to='User/Profile', blank=True, null=True)
    user_code = models.CharField(max_length=25, unique=True, null=True, blank=True)
    bp_code = models.ForeignKey(BusinessPartner, on_delete=models.CASCADE, null=True, blank=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    role_name = models.CharField(max_length=50, choices=ROLE_CHOICES)
    user_state = models.CharField(max_length=50, choices=USER_TYPE_CHOICES, default='internal')
    full_name = models.CharField(max_length=255, null=True, blank=True)
    mobile_no = models.CharField(max_length=15, validators=[validate_mobile_no], null=True, blank=True)
    email_id = models.EmailField(unique=True, null=True, blank=True, validators=[EmailValidator()])
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
     # Additional permission fields
    view_only = models.BooleanField(default=False, verbose_name=_("View Only"))
    copy = models.BooleanField(default=False, verbose_name=_("Copy"))
    screenshot = models.BooleanField(default=False, verbose_name=_("Screenshot"))
    print_perm = models.BooleanField(default=False, verbose_name=_("Print"))
    download = models.BooleanField(default=False, verbose_name=_("Download"))
    share = models.BooleanField(default=False, verbose_name=_("Share"))
    edit = models.BooleanField(default=False, verbose_name=_("Edit"))
    delete = models.BooleanField(default=False, verbose_name=_("Delete"))
    manage_roles = models.BooleanField(default=False, verbose_name=_("Manage Roles"))
    approve = models.BooleanField(default=False, verbose_name=_("Approve"))
    reject = models.BooleanField(default=False, verbose_name=_("Reject"))
    archive = models.BooleanField(default=False, verbose_name=_("Archive"))
    restore = models.BooleanField(default=False, verbose_name=_("Restore"))
    transfer = models.BooleanField(default=False, verbose_name=_("Transfer"))
    custom_access = models.BooleanField(default=False, verbose_name=_("Custom Access"))
    full_control = models.BooleanField(default=False, verbose_name=_("Full Control"))
    delete_flag = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, related_name="custom_users", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_users", blank=True)

    def assign_role_permissions(self):
        """
        Dynamically assigns permissions based on user's role and permission fields,
        and creates a specific permission group for each user.
        """
        if not self.pk:
            return

        role_group, created = Group.objects.get_or_create(name=self.role_name)

        if created or not self.groups.filter(name=self.role_name).exists():
            self.groups.add(role_group)

        permission_mapping = {
            'view_only': 'view',
            'copy': 'copy',
            'screenshot': 'screenshot',
            'print_perm': 'print',
            'download': 'download',
            'share': 'share',
            'edit': 'edit',
            'delete': 'delete',
            'manage_roles': 'manage_roles',
            'approve': 'approve',
            'reject': 'reject',
            'archive': 'archive',
            'restore': 'restore',
            'transfer': 'transfer',
            'custom_access': 'custom_access',
            'full_control': 'full_control',
        }
        role_group.permissions.clear()
        for field, codename in permission_mapping.items():
            if getattr(self, field, False):
                permission = Permission.objects.filter(codename=codename).first()
                if permission:
                    role_group.permissions.add(permission)

        self.groups.add(role_group)

        logger.info(f"Permissions assigned to group '{role_group.name}' for user '{self.username}'")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            self.assign_role_permissions()
    
    
def fetch_location_pre_save(sender, instance, **kwargs):
    if instance.pincode:
        url_primary = f"https://api.postalpincode.in/pincode/{instance.pincode}"
        url_backup = f"https://api.zippopotam.us/in/{instance.pincode}"
        retries = 3  
        timeout_seconds = 10

        for attempt in range(retries):
            try:
                response = requests.get(url_primary, timeout=timeout_seconds)
                response.raise_for_status()
                data = response.json()

                if data and data[0]['Status'] == "Success" and data[0]['PostOffice']:
                    post_office = data[0]['PostOffice'][0]
                    instance.city = post_office.get('District', '').strip() or None
                    instance.state = post_office.get('State', '').strip() or None
                    instance.country = post_office.get('Country', '').strip() or None
                    return

            except requests.exceptions.RequestException as e:
                logger.error(f"Attempt {attempt + 1}: Error fetching location for {instance.pincode}: {str(e)}")
                time.sleep(2)
        try:
            response = requests.get(url_backup, timeout=timeout_seconds)
            response.raise_for_status()
            data = response.json()

            if 'places' in data:
                place = data['places'][0]
                instance.city = place.get('place name', '').strip() or None
                instance.state = place.get('state', '').strip() or None
                instance.country = data.get('country', '').strip() or None
                return

        except requests.exceptions.RequestException as e:
            logger.error(f"Backup API failed: {str(e)}")

        logger.error(f"Failed to fetch location for pincode {instance.pincode} after {retries} attempts")
        instance.city = "Unknown"
        instance.state = "Unknown"
        instance.country = "Unknown"

models.signals.pre_save.connect(fetch_location_pre_save, sender=ResUser)

class RoleDashboardMapping(models.Model):
    role = models.CharField(max_length=50, choices=ResUser.ROLE_CHOICES)
    dashboard_url = models.URLField()

    def __str__(self):
        return f'{self.role} - {self.dashboard_url}'
    
    def save(self, *args, **kwargs):
        if ResUser.objects.filter(user_code=self.user_code).exists():
            raise ValidationError("User code already exists.")
        super().save(*args, **kwargs)
