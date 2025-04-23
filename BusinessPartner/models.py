from django.db import models
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.timezone import now
from django.conf import settings
import requests
import logging
import re
from urllib.parse import quote


logger = logging.getLogger(__name__)



ROLE_CHOICES = ['Super Admin', 'Project Owner', 'Admin']

def validate_pan_number(value):
    """
    Validates if the given value is a valid PAN number (Permanent Account Number - India).
    The format should be: 5 uppercase letters, followed by 4 digits, followed by 1 uppercase letter.
    Example: ABCDE1234F
    """
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'

    if not re.match(pan_pattern, value):
        raise ValidationError(
            f"'{value}' is not a valid PAN number. It should be in the format: ABCDE1234F."
        )
#gst validator
def validate_gst_number(value):
    """
    Validates if the given value is a valid GSTIN (Goods and Services Tax Identification Number - India).
    The format should be: 2-digit state code + 10-character PAN + 1 entity code + 'Z' + 1 checksum character.
    Example: 22AAAAA1234A1Z5
    """
    gst_pattern = r'^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$'

    if not re.match(gst_pattern, value):
        raise ValidationError(
            f"'{value}' is not a valid GST number. It should be in the format: 22AAAAA1234A1Z5."
        )
    
def validate_aadhar_no(value):
    if not re.match(r'^[0-9]{12}$', value):
        raise ValidationError(_("Invalid Aadhar Number. It must be exactly 12 digits."))
    
def validate_ifsc_code(value):
    ifsc_pattern = r'^[A-Z]{4}[0-9]{7}$'
    if not re.match(ifsc_pattern, value):
        raise ValidationError(_("Invalid IFSC Code. Expected format: ABCD0123456."))

def validate_mobile_no(value):
    if not value.isdigit():
        raise ValidationError(_("Mobile number must contain only digits."))
    if not (10 <= len(value) <= 15):
        raise ValidationError(_("Mobile number must be between 10 to 15 digits."))
    
def validate_msme_no(value):
    """
    Validate MSME (Udyog Aadhaar) number.
    Format: UDY + 2-digit number + 3 uppercase letters + 7-digit number
    Example: UDY12ABC1234567
    """
    msme_pattern = r'^[Uu][Dd][Yy]\d{2}[A-Za-z]{3}\d{7}$'
    
    if not re.fullmatch(msme_pattern, value):
        raise ValidationError("Invalid MSME format. Expected format: UDY12ABC1234567.")

    return value
class BusinessPartner(models.Model):
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('freezed', 'Freezed'),
        ('revoked', 'Revoked'),
    ]
    ROLE_STATUS = [
        ('BUYER', 'BUYER'),
        ('CRAFTSMAN', 'CRAFTSMAN'),
    ]
    TERM_STATUS = [
        ('T1', 'T1-Credit 30 Days'),
        ('T2', 'T2-Credit 45 Days'),
        ('T3', 'T3-Credit 60 Days'),
        ('CH', 'CH-Cash Customer'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_STATUS, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='approved')
    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='BusinessPartner',
        blank=True,
        null=True)
    
    bp_code = models.CharField(max_length=50, unique=True, blank=False, null=False)
    term = models.CharField(max_length=100, choices=TERM_STATUS, blank=False, null=False)
    business_name = models.CharField(max_length=255)
    freezed = models.BooleanField(default=False)
    revoked = models.BooleanField(default=False)
    full_name = models.CharField(max_length=255, blank=False, null=False)
    mobile = models.CharField(max_length=15, validators=[validate_mobile_no], verbose_name="Mobile No", unique=False, blank=False, null=False)
    alternate_mobile = models.CharField(max_length=15, validators=[validate_mobile_no], blank=True, null=True,unique=False)
    landline = models.CharField(max_length=15, blank=True, null=True)
    alternate_landline = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=False, null=False,unique=False)
    business_email = models.EmailField(max_length=255, null=True, blank=True ,unique=False)
    refered_by = models.TextField(blank=True, null=True)
    referer_mobile = models.CharField(max_length=15,blank=True, null=True) 
    more = models.TextField(blank=True, null=True)
    door_no = models.CharField(max_length=50, blank=True, null=True)
    shop_no = models.CharField(max_length=50, blank=True, null=True)
    complex_name = models.CharField(max_length=255, blank=True, null=True)
    building_name = models.CharField(max_length=255, blank=True, null=True)
    street_name = models.CharField(max_length=255, blank=True, null=True)
    area = models.CharField(max_length=255, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=False, null=False)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    map_location = models.CharField(max_length=500, null=True, blank=True)
    location_guide = models.TextField(blank=True, null=True)
    
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.user_id and self.user_id.role_name not in ROLE_CHOICES:
            raise PermissionDenied("You do not have permission to create a Business Partner.")
        super().save(*args, **kwargs)
        
    def save(self, *args, **kwargs):
        if self.business_email == "":
            self.business_email = None
        
        if self.pk:
            existing = BusinessPartner.objects.filter(pk=self.pk).first()
            if existing and existing.role == "BUYER" and self.role == "CRAFTSMAN":
                self.pk = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bp_code} - {self.business_name}"


class BusinessPartnerKYC(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('freezed', 'Freezed'),
        ('revoked', 'Revoked'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    bp_code = models.ForeignKey(
        BusinessPartner, on_delete=models.CASCADE, related_name='kyc_details'
    )  
    bis_no = models.CharField(max_length=50, blank=True, null=True)
    bis_attachment = models.ImageField(upload_to='attachments/', blank=True, null=True) 
    gst_no = models.CharField(max_length=50,validators=[validate_gst_number], blank=False, null=False)
    gst_attachment = models.ImageField(upload_to='attachments/', blank=False, null=False) 
    msme_no = models.CharField(max_length=50, validators=[validate_msme_no], blank=True, null=True)
    msme_attachment = models.ImageField(upload_to='attachments/', blank=True, null=True) 
    pan_no = models.CharField(max_length=10, blank=True, null=True, validators=[validate_pan_number])  
    pan_attachment = models.ImageField(upload_to='attachments/', blank=True, null=True) 
    tan_no = models.CharField(max_length=10, validators=[validate_pan_number], blank=True, null=True)
    tan_attachment = models.ImageField(upload_to='attachments/', blank=True, null=True)
    image = models.ImageField(upload_to='kyc/business_partner/', blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    aadhar_no = models.CharField(max_length=12, validators=[validate_aadhar_no], default=list, blank=True, null=True)
    aadhar_attach = models.FileField(upload_to='attachments/', blank=True, null=True)   
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    account_no = models.CharField(max_length=50, blank=True, null=True)
    branch = models.CharField(max_length=255, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20,validators=[validate_ifsc_code], blank=True, null=True)
    bank_city = models.CharField(max_length=100, blank=True, null=True)
    bank_state = models.CharField(max_length=100, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    freezed = models.BooleanField(default=False)
    revoked = models.BooleanField(default=False)
    

def __str__(self):
        return self.name

def save(self, *args, **kwargs):
        if not self.ifsc_code and self.bank_name and self.branch:
            fetched_ifsc = fetch_ifsc_code(self.bank_name, self.branch)
            if fetched_ifsc:
                self.ifsc_code = fetched_ifsc
            else:
                logger.warning(f"Could not fetch IFSC Code for {self.bank_name}, {self.branch}. Please enter manually.")
        super().save(*args, **kwargs)
        

def fetch_ifsc_code(bank_name, branch):
    """
    Fetch IFSC Code based on Bank Name and Branch using an external API.
    """
    try:
        url = f"https://ifsc.razorpay.com/{bank_name}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("IFSC")
        else:
            logger.warning(f"Failed to fetch IFSC Code for {bank_name}, {branch}. API Response: {response.status_code}")
            return None
    except requests.RequestException as e:
        logger.error(f"Error fetching IFSC Code: {str(e)}")
        return None 

def fetch_location_from_pincode(pincode):
    if not pincode or not pincode.isdigit() or len(pincode) != 6:
        return None, None
    url = f"https://api.postalpincode.in/pincode/{pincode}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data and data[0]['Status'] == "Success" and data[0]['PostOffice']:
            city = data[0]['PostOffice'][0].get('District', '')
            state = data[0]['PostOffice'][0].get('State', '')
            return city, state
        else:
            logger.warning(f"Invalid pincode response: {data[0].get('Message', 'Unknown error')}")
            return None, None
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
    return None, None

@receiver(pre_save, sender=BusinessPartner)
def fetch_location_pre_save(sender, instance, **kwargs):
    if instance.pincode and (not instance.city or not instance.state):
        city, state = fetch_location_from_pincode(instance.pincode)
        instance.city = city
        instance.state = state
        
        
def get_map_url(self):
        """Generate Google Maps URL based on address details"""
        address_parts = filter(None, [self.door_no, self.street_name, self.area, self.city, self.state, self.pincode])
        address = ", ".join(address_parts)
        encoded_address = quote(address)
        return f"https://www.google.com/maps/search/?api=1&query={encoded_address}"

def save(self, *args, **kwargs):
        if self.user_id and self.user_id.role_name not in ROLE_CHOICES:
            raise PermissionDenied("You do not have permission to create a Business Partner.")
        if not self.map:
            self.map = self.get_map_url()

        super().save(*args, **kwargs)
        
        
def update_status(self):
        if self.revoked:
            self.status = "Revoked"
        elif self.freezed:
            self.status = "Freezed"
        elif all([
                self.bp_code, self.bis_no, self.bis_attachment, self.gst_no, self.gst_attachment,
                self.msme_no, self.msme_attachment, self.pan_no, self.pan_attachment,
                self.tan_no, self.tan_attachment, self.image, self.name, self.aadhar_no,
                self.aadhar_attach, self.bank_name, self.account_name, self.account_no,
                self.ifsc_code, self.branch, self.bank_city, self.bank_state, self.note
            ]):
            self.status = "Approved"
        else:
            self.status = "Pending"
        self.save()

def freeze(self):
        self.is_frozen = True
        self.update_status()

def revoke(self):
        self.is_revoked = True
        self.update_status()

def save(self, *args, **kwargs):
        self.update_status()
        super().save(*args, **kwargs)

def __str__(self):
        return f"{self.bp_code} - {self.business_name}"
