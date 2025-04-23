from rest_framework import serializers
from .models import BusinessPartner, BusinessPartnerKYC,fetch_ifsc_code
import re
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

def validate_pan_number(value):
    """
    Validate if the given value is a valid PAN number.
    """
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
    if not re.match(pan_pattern, value):
        raise serializers.ValidationError("Invalid PAN number format. Expected: ABCDE1234F")
    return value

def validate_gst_number(value):
    """
    Validates if the given value is a valid GSTIN (India).
    Format: 2-digit state code + 10-character PAN + 1 entity code + 'Z' + 1 checksum character.
    Example: 22AAAAA1234A1Z5
    """
    gst_pattern = r'^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$'
    if not re.match(gst_pattern, value):
        raise serializers.ValidationError(f"'{value}' is not a valid GST number. Expected format: 22AAAAA1234A1Z5.")
    return value

def validate_aadhar_no(value):
    if not re.match(r'^[0-9]{12}$', value):
        raise serializers.ValidationError(_("Invalid Aadhar Number. It must be exactly 12 digits."))
    return value

def validate_ifsc_code(value):
    ifsc_pattern = r'^[A-Z]{4}[0-9]{7}$'
    if not re.match(ifsc_pattern, value):
        raise serializers.ValidationError(_("Invalid IFSC Code. Expected format: ABCD0123456."))
    return value

def validate_mobile_no(value):
    if not value.isdigit():
        raise serializers.ValidationError(_("Mobile number must contain only digits."))
    if not (10 <= len(value) <= 15):
        raise serializers.ValidationError(_("Mobile number must be between 10 to 15 digits."))
    return value

def validate_msme_no(value):
    """Validate MSME (Udyog Aadhaar) number."""
    msme_pattern = r'^[Uu][Dd][Yy]\d{2}[A-Za-z]{3}\d{7}$'
    
    if not re.fullmatch(msme_pattern, value, re.IGNORECASE):
        raise serializers.ValidationError(_("Invalid MSME format. Expected format: UDY12ABC1234567."))

    return value  
    

class BusinessPartnerSerializer(serializers.ModelSerializer):
    """
    Serializer for BusinessPartner model with explicit fields and nested KYC details.
    """
    mobile = serializers.CharField(validators=[validate_mobile_no])
    alternate_mobile = serializers.CharField(validators=[validate_mobile_no], required=False, allow_blank=True)
    email = serializers.EmailField(required=True)
    business_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)  # ✅ Allow NULL in serializer
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    bp_code = serializers.SerializerMethodField()

    
    class Meta:
        model = BusinessPartner
        fields = [
            'role', 'bp_code', 'term', 'business_name', 'full_name', 'mobile', 'alternate_mobile',
            'landline', 'alternate_landline', 'email', 'business_email', 'refered_by', 'referer_mobile', 'more', 'door_no', 'shop_no', 'complex_name',
            'building_name', 'street_name', 'area', 'pincode', 'city', 'state', 'map_location', 'location_guide',
        ]
        read_only_fields = ['status','bp_code'] 
        unique_together = ('role', 'business_email')
        
    def get_bp_code(self, obj):
        return f"{obj.bp_code}-{obj.business_name}"
        
        
    def validate(self, data):
        mobile = data.get('mobile')
        email = data.get('email')
        business_email = data.get('business_email', None)
        role = data.get('role', '').upper()
        instance = self.instance

        if not role or role not in ['BUYER', 'CRAFTSMAN']:
            raise serializers.ValidationError({
                "role": _("Invalid role. Must be either 'BUYER' or 'CRAFTSMAN'.")
            })
        queryset = BusinessPartner.objects.filter(role=role)

        if instance:
            queryset = queryset.exclude(id=instance.id)

        if mobile and queryset.filter(mobile=mobile).exists():
            raise serializers.ValidationError({
                "mobile": _("This mobile number is already used in the same role.")
            })

        if email and queryset.filter(email=email).exists():
            raise serializers.ValidationError({
                "email": _("This email is already used in the same role.")
            })
        if business_email:
            qs = BusinessPartner.objects.filter(business_email=business_email, role=role)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'business_email': f'This business email already exists for a {role}.'
                })

        return data

    
    
    def create(self, validated_data):
        if BusinessPartner.objects.filter(business_email=validated_data['business_email']).exists():
            raise ValidationError({"business_email": "A business partner with this email already exists."})
        return super().create(validated_data)
    
    
    def create(self, validated_data):
        user = self.context.get('request').user if self.context.get('request') else None
        if user is None or user.role_name not in ["super_admin", "admin", "Project Owner"]:
            raise serializers.ValidationError("You do not have permission to create a Business Partner.")

        business_name = validated_data.get('business_name', '').strip()
        if not business_name:
            raise serializers.ValidationError({"business_name": "Business name is required to generate BP code."})
        
        role = validated_data.get('role', '').upper()
        if role not in ['BUYER', 'CRAFTSMAN']:
            raise serializers.ValidationError({"role": "Invalid role. Must be either 'BUYER' or 'CRAFTSMAN'."})

        prefix = 'B' if role == 'BUYER' else 'A'
        first_letter = business_name[0].upper()
        last_bp = BusinessPartner.objects.filter(bp_code__regex=rf'^{prefix}{first_letter}\d+$').order_by('-bp_code').first()
        
        new_number = int(last_bp.bp_code[2:]) + 1 if last_bp else 1
        validated_data['bp_code'] = f"{prefix}{first_letter}{new_number:03d}"
        validated_data['user_id'] = user

        return super().create(validated_data)


    def update(self, instance, validated_data):
        new_role = validated_data.get("role", "").upper()
        if instance.role == "BUYER" and new_role == "CRAFTSMAN":
            validated_data.pop("role") 
            new_instance_data = {
                **{field.name: getattr(instance, field.name) for field in instance._meta.fields if field.name not in ['id', 'bp_code']},
                **validated_data,
                "role": "CRAFTSMAN"
            }
            return BusinessPartner.objects.create(**new_instance_data)
        return super().update(instance, validated_data)

class BusinessPartnerKYCSerializer(serializers.ModelSerializer):
    
    
    bp_code = serializers.SlugRelatedField(
            queryset=BusinessPartner.objects.all(),
            slug_field='bp_code',
            required=False,
            allow_null=True
        )
    status = serializers.SerializerMethodField()
    class Meta:
        model = BusinessPartnerKYC
        fields = [
            'bp_code', 'bis_no', 'bis_attachment', 'gst_no', 'gst_attachment', 
            'msme_no', 'msme_attachment', 'pan_no', 'pan_attachment', 
            'tan_no', 'tan_attachment', 'image', 'name', 'aadhar_no', 
            'aadhar_attach', 'bank_name', 'account_name', 'account_no',
            'ifsc_code', 'branch', 'bank_city', 'bank_state', 'note', 'status',
            
        ]

    def get_status(self, obj):
        if obj.revoked:
            return 'Revoked'
        if obj.freezed:
            return 'Freezed'
        if all([
    obj.bp_code, obj.bis_no, obj.bis_attachment, obj.gst_no, obj.gst_attachment,
    obj.msme_no, obj.msme_attachment, obj.pan_no, obj.pan_attachment,
    obj.tan_no, obj.tan_attachment, obj.image, obj.name, obj.aadhar_no,
    obj.aadhar_attach, obj.bank_name, obj.account_name, obj.account_no,
    obj.ifsc_code, obj.branch, obj.bank_city, obj.bank_state, obj.note
]):

           
            return 'Approved'
        return 'Pending'
    
    
    def to_representation(self, instance):
        """Modify the output representation to include business_name with bp_code."""
        data = super().to_representation(instance)
        if instance.bp_code:
            data['bp_code'] = f"{instance.bp_code.bp_code}-{instance.bp_code.business_name}"
        return data


    def create(self, validated_data):
        if 'bp_code' not in validated_data:
            raise serializers.ValidationError({"bp_code": "This field is required."})
        return super().create(validated_data)