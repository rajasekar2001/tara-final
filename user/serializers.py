# Version: 210518   1.0      Initial version    AB  1.0
# Version: 210518   1.1      Added ResAdminUserSerializer    AB  1.1
# Version: 210518   1.2      Added LoginSerializer    AB  1.2
# Version: 210518   1.3      Added send_otp_via_sms    AB  1.3

from rest_framework import serializers
from django.contrib.auth.models import Group, Permission
from user.models import ResUser
import random
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.exceptions import ValidationError
from django.utils.crypto import get_random_string
from django.core.cache import cache
from django.contrib.auth.hashers import make_password, check_password
from twilio.rest import Client
from rest_framework.exceptions import PermissionDenied
from BusinessPartner.models import BusinessPartner


class ResUserSerializer(serializers.ModelSerializer):
    """
    Base User Serializer for handling general user logic.
    """
    bp_code = serializers.SlugRelatedField(
        queryset=BusinessPartner.objects.all(),
        slug_field='bp_code',  # This ensures bp_code is displayed instead of ID
        required=False,
        allow_null=True
    )

    user_permissions = serializers.PrimaryKeyRelatedField(
    queryset=Permission.objects.all(), many=True, required=False
    )
    # Additional permission fields (without 'source' argument)
    view_only = serializers.BooleanField(default=False)
    copy = serializers.BooleanField(default=False)
    screenshot = serializers.BooleanField(default=False)
    print_perm = serializers.BooleanField(default=False)
    download = serializers.BooleanField(default=False)
    share = serializers.BooleanField(default=False)
    edit = serializers.BooleanField(default=False)
    delete = serializers.BooleanField(default=False)
    manage_roles = serializers.BooleanField(default=False)
    approve = serializers.BooleanField(default=False)
    reject = serializers.BooleanField(default=False)
    archive = serializers.BooleanField(default=False)
    restore = serializers.BooleanField(default=False)
    transfer = serializers.BooleanField(default=False)
    custom_access = serializers.BooleanField(default=False)
    full_control = serializers.BooleanField(default=False)
    delete_flag = serializers.BooleanField(default=False)

    class Meta:
        model = ResUser
        fields = [
            'id', 'profile_picture', 'user_code', 'bp_code', 'full_name', 'email_id', 'mobile_no',
            'company_name', 'password', 'role_name', 'user_state', 'status', 'dob', 'gender',
            'city', 'state', 'country', 'pincode', 'created_at', 'updated_at','user_permissions',
            'view_only', 'copy', 'screenshot', 'print_perm', 'download', 'share', 'edit', 'delete', 
            'manage_roles', 'approve', 'reject', 'archive', 'restore', 'transfer', 'custom_access', 'full_control','delete_flag',
        ]
        

        extra_kwargs = {
            'password': {'write_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True}
        }
    def to_representation(self, instance):
        """Modify the output representation to include business_name with bp_code."""
        data = super().to_representation(instance)
        if instance.bp_code:
            data['bp_code'] = f"{instance.bp_code.bp_code}-{instance.bp_code.business_name}"
        return data
    
        
    def get_permissions(self, obj):
        """
        Dynamically fetch only user-specific permissions (no group-based permissions).
        """
        user_permissions = obj.user_permissions.all()  # Only direct user permissions
        return [{'codename': perm.codename, 'name': perm.name, 'granted': True} for perm in user_permissions]

    def validate_groups(self, value):
        """
        Ensure all group IDs are valid and are Group instances.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Groups must be provided as a list.")

        groups = []
        for group_id in value:
            try:
                group = Group.objects.get(id=group_id)
                groups.append(group)
            except Group.DoesNotExist:
                raise serializers.ValidationError(f"Group with ID {group_id} does not exist.")
        return groups

    
    
    def to_representation(self, instance):
        """
        Modify the response to include BusinessPartner details if bp_code is provided.
        """
        data = super().to_representation(instance)
        
        if instance.bp_code:
            bp = BusinessPartner.objects.filter(bp_code=instance.bp_code.bp_code).first()
            if bp:
                data['bp_email'] = bp.email
                data['bp_mobile'] = bp.mobile
                data['bp_full_name'] = bp.full_name

        return data
    
    

    def generate_user_code(self, role_name):
        """
        Generate user_code based on role_name.
        """
        role_prefix_mapping = {
            "Project Owner": "PO",
            "Super Admin": "SA",
            "Admin": "AD",
            "Key User": "KU",
            "User": "UR",
            "Craftsman": "CF",
            "Walking Customer": "WC"
        }

        prefix = role_prefix_mapping.get(role_name, "UR")  # Default to UR if role not found
        last_user = ResUser.objects.filter(user_code__startswith=prefix + "-").order_by('-user_code').first()
        
        if last_user:
            last_number = int(last_user.user_code.split('-')[1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}-{new_number:04d}"  # Formats as SA-0001, AD-0001, etc.

    def create(self, validated_data):
        """
        Create user with auto-generated user_code based on role_name.
        """
        role_name = validated_data.get('role_name')
        validated_data['user_code'] = self.generate_user_code(role_name)

        password = validated_data.get('password')
        groups = validated_data.pop('groups', [])
        
        user = super().create(validated_data)

        if password:
            user.set_password(password)
            user.save(update_fields=['password'])

        if groups:
            user.groups.set(groups)

        return user

    def update(self, instance, validated_data):
        """
        Update user and reassign groups.
        """
        password = validated_data.get('password')
        groups = validated_data.pop('groups', [])  

        instance = super().update(instance, validated_data)

        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])

        if groups:
            instance.groups.set(groups)

        return instance
   

    
class ResAdminUserSerializer(ResUserSerializer):
    """
    Serializer for Admin users with limited fields.
    """
    class Meta:
        model = ResUser
        fields = ['id', 'user_code', 'bp_code', 'profile_picture', 'company_name', 'full_name', 'mobile_no', 'email_id', 'password']
    
    extra_kwargs = {
        'password': {'write_only': True},
        'created_at': {'read_only': True},
        'updated_at': {'read_only': True}
    }

    def create(self, validated_data):
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email_or_mobile = serializers.CharField(max_length=255)
    user_code = serializers.CharField(max_length=25, required=False)
    password = serializers.CharField(max_length=128, write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        """
        Validate email/mobile and password, and auto-fetch user_code.
        """
        email_or_mobile = data.get('email_or_mobile')
        password = data.get('password')

        if not email_or_mobile or not password:
            raise serializers.ValidationError("Email/mobile and password are required.")

        try:
            if '@' in email_or_mobile:
                user = ResUser.objects.get(email_id=email_or_mobile)
            else:
                user = ResUser.objects.get(mobile_no=email_or_mobile)
            
            data['user_code'] = user.user_code
        except ResUser.DoesNotExist:
            raise serializers.ValidationError("Invalid email/mobile number or password.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email/mobile number or password.")

        if user.status != 'active':
            raise serializers.ValidationError("This account is inactive. Please contact support.")

        return data
    
def send_otp_via_sms(mobile_no, otp):
    """Twilio SMS gateway se OTP bhejne ke liye"""
    client = Client(settings.TWILIO_ACCOUNT, settings.TWILIO_TOKEN)
    message = client.messages.create(
        body=f"Your OTP for password reset is {otp}.",
        from_=settings.TWILIO_FROM,
        to=mobile_no
    )
    print(f"OTP {otp} sent to mobile {mobile_no}. Message SID: {message.sid}")


class ForgotPasswordSerializer(serializers.Serializer):
    email_or_mobile = serializers.CharField(max_length=255, required=False)
    otp = serializers.CharField(max_length=6, required=False)
    new_password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    confirm_new_password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})

    def validate(self, data):
        email_or_mobile = data.get("email_or_mobile")
        otp = data.get("otp")
        new_password = data.get("new_password")
        confirm_new_password = data.get("confirm_new_password")

        # ✅ Resend OTP
        if not email_or_mobile and not otp and not new_password:
            return self.resend_otp()

        # ✅ Send OTP if email/mobile provided
        if email_or_mobile and not otp and not new_password:
            user = self.get_user(email_or_mobile)
            if not user:
                return {"success": False, "message": "User with this email or mobile number does not exist."}
            return self.send_otp(email_or_mobile)

        # ✅ Verify OTP
        elif otp and not new_password:
            cache_key = f"password_reset_{otp}"
            user_id = cache.get(cache_key)

            if not user_id:
                return {"success": False, "message": "Invalid or expired OTP."}

            # OTP verified, store user_id in cache for password reset (without OTP)
            verified_key = f"otp_verified_{user_id}"
            cache.set(verified_key, user_id, timeout=600)  # 10 min validity

            return {"success": True, "message": "OTP verified successfully. You can now reset your password."}

        # ✅ Reset password with confirm password check
        elif new_password and confirm_new_password:
            if new_password != confirm_new_password:
                return {"success": False, "message": "New password and confirm password do not match."}

            verified_user_id = None

            # 🔥 Fetch verified user ID safely
            for user in ResUser.objects.all():
                verified_key = f"otp_verified_{user.id}"
                if cache.get(verified_key):
                    verified_user_id = user.id
                    break

            if not verified_user_id:
                return {"success": False, "message": "OTP not verified. Please verify OTP first."}

            # Reset password logic
            user = ResUser.objects.get(id=verified_user_id)
            user.set_password(new_password)  # ✅ Correct hashing method
            user.save()

            # Cleanup cache after password reset
            cache.delete(f"otp_verified_{verified_user_id}")

            return {"success": True, "message": "Password reset successfully."}

        return {"success": False, "message": "Invalid request. Provide email/mobile to get OTP, OTP to verify, or new password to reset password."}

    def get_user(self, email_or_mobile):
        try:
            if "@" in email_or_mobile:
                return ResUser.objects.get(email_id=email_or_mobile)
            else:
                return ResUser.objects.get(mobile_no=email_or_mobile)
        except ResUser.DoesNotExist:
            return None

    def send_otp(self, email_or_mobile):
        user = self.get_user(email_or_mobile)
        if not user:
            return {"success": False, "message": "User not found."}

        otp_attempts_key = f"otp_attempts_{user.id}"
        attempts = cache.get(otp_attempts_key, 0)

        if attempts >= 5:
            return {"success": False, "message": "Too many OTP requests. Try again later."}

        otp = get_random_string(length=6, allowed_chars="1234567890")
        cache.set(f"password_reset_{otp}", user.id, timeout=300)
        cache.set(otp_attempts_key, attempts + 1, timeout=600)

        if "@" in email_or_mobile:
            send_mail("Your OTP", f"Your new OTP is {otp}.", settings.DEFAULT_FROM_EMAIL, [user.email_id])
        else:
            send_otp_via_sms(user.mobile_no, otp)

        cache.set("last_otp_request", email_or_mobile, timeout=600)

        return {"success": True, "message": "OTP sent successfully."}

    def resend_otp(self):
        email_or_mobile = cache.get("last_otp_request")
        if not email_or_mobile:
            return {"success": False, "message": "No previous OTP request found. Please enter email or mobile."}
        return self.send_otp(email_or_mobile)

class ResetPasswordSerializer(serializers.Serializer):
    email_or_mobile = serializers.CharField(max_length=255)
    old_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, data):
        email_or_mobile = data.get("email_or_mobile")
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not email_or_mobile:
            raise ValidationError("Email or mobile number is required.")

        try:
            if "@" in email_or_mobile:
                user = ResUser.objects.get(email_id=email_or_mobile)
            else:
                user = ResUser.objects.get(mobile_no=email_or_mobile)
        except ResUser.DoesNotExist:
            raise ValidationError("User not found with this email or mobile number.")

        # Verify old password
        if not check_password(old_password, user.password):
            raise ValidationError("Old password is incorrect.")

        # Update password
        user.password = make_password(new_password)
        user.save()

        return {"message": "Password changed successfully."}
    
    def create(self, validated_data):
        user_code = validated_data.get('user_code')
        if ResUser.objects.filter(user_code=user_code).exists():
            raise ValidationError({'user_code': 'A user with this user_code already exists.'})
        return super().create(validated_data)
    
    def create(self, validated_data):
        """
        Create a new user and ensure bp_code is assigned correctly.
        """
        password = validated_data.pop('password', None)
        user_permissions = validated_data.pop('user_permissions', [])

        bp_code = validated_data.pop('bp_code', None)  # Extract the BusinessPartner instance

        user = ResUser.objects.create(**validated_data)

        if bp_code:
            user.bp_code = bp_code  # Assign Business Partner

        if password:
            user.set_password(password)

        if user_permissions:
            user.user_permissions.set(user_permissions)

        user.save()
        return user

    def update(self, instance, validated_data):
        """
        Update an existing user and ensure bp_code is retained.
        """
        password = validated_data.pop('password', None)
        user_permissions = validated_data.pop('user_permissions', [])

        bp_code = validated_data.pop('bp_code', None)  # Extract the BusinessPartner instance

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if bp_code:
            instance.bp_code = bp_code  # Update Business Partner Code

        if password:
            instance.set_password(password)

        if user_permissions is not None:
            instance.user_permissions.set(user_permissions)

        instance.save()
        return instance