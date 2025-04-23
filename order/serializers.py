from django.utils import timezone
import pytz
from rest_framework import serializers
from SuperAdmin.models import SuperAdmin
from .models import Order
from BusinessPartner.models import BusinessPartner
from user.models import ResUser, BusinessPartner  
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from datetime import date


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer class for the Order model.
    """
    bp_code = serializers.SlugRelatedField(
        queryset=BusinessPartner.objects.all(),
        slug_field='bp_code',
        required=False,
        allow_null=True
    )
    order_date = serializers.SerializerMethodField() 
       
    def get_order_date(self, obj):
        ist = pytz.timezone('Asia/Kolkata')
        return obj.order_date.astimezone(ist).strftime('%d-%m-%Y %H:%M:%S IST')
    class Meta:
        model = Order
        fields = [
            'order_image', 'order_no', 'bp_code', 'name', 'reference_no', 'order_date', 'due_date', 'category', 'order_type',
            'quantity', 'weight', 'dtype', 'branch_code', 'product', 'design', 'vendor_design', 'barcoded_quality',
            'supplied', 'balance', 'assigned_by', 'narration', 'note', 'sub_brand', 'make', 'work_style', 'form',
            'finish', 'theme', 'collection', 'description', 'assign_remarks', 'screw', 'polish', 'metal_colour',
            'purity', 'stone', 'hallmark', 'rodium', 'enamel', 'hook', 'size', 'open_close', 'length', 'hbt_class',
            'console_id', 'tolerance_from', 'tolerance_to'
        ]
        read_only_fields = ['order_no', 'order_date'] 

    def create(self, validated_data):
        if 'bp_code' not in validated_data:
            raise serializers.ValidationError({"bp_code": "This field is required."})
        return super().create(validated_data)

    def to_representation(self, instance):
        """Modify the output representation to include business_name with bp_code."""
        data = super().to_representation(instance)
        if instance.bp_code:
            data['bp_code'] = f"{instance.bp_code.bp_code}-{instance.bp_code.business_name}"
        return data
    
    def validate(self, data):
        if 'order_date' in data:
            raise serializers.ValidationError("Order date is auto-set to today's date")
        return data
    
    def validate_due_date(self, value):
        """
        Validate that due_date is at least tomorrow (future date only).
        """
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        
        if value <= today:
            raise serializers.ValidationError("Due date must be tomorrow or later. Cannot be today or in the past.")
        return value
    
    def create(self, validated_data):
        if 'bp_code' not in validated_data:
            raise serializers.ValidationError({"bp_code": "This field is required."})
        last_order = Order.objects.all().order_by('id').last()
        
        if not last_order:
            new_order_no = '001'
        else:
            try:
                last_number = int(last_order.order_no)
                new_number = last_number + 1
                new_order_no = f"{new_number:02d}"
            except (ValueError, AttributeError):
                new_order_no = f"{Order.objects.count() + 1:02d}"
        
        validated_data['order_no'] = new_order_no
        return super().create(validated_data)
    

class OrderUpdateSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=[
        ('accepted', 'Accepted'), ('rejected', 'Rejected')
    ])
    text = serializers.CharField(max_length=255, required=False)
    selection = serializers.ChoiceField(choices=[], required=False)
    flag = serializers.HiddenField(default='flag')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        users = ResUser.objects.filter(role_name='craftsman')
        if self.context.get('state') != 'rejected':
            self.fields['selection'].choices = [(user.id, user.username) for user in users]
        else:
            self.fields.pop('selection', None)


class BackSellerOrderUpdateSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=[
        ('accepted', 'Accepted'), ('rejected', 'Rejected')
    ])
    text = serializers.CharField()
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

class AssignOrdersSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    craftsman_id = serializers.IntegerField()

    def validate(self, data):
        # Check if order exists
        if not Order.objects.filter(id=data['order_id']).exists():
            raise serializers.ValidationError("Order does not exist")
        
        # Check if craftsman exists and has the correct role
        craftsman = BusinessPartner.objects.filter(
            id=data['craftsman_id'], 
            role='CRAFTSMAN'
        ).first()
        
        if not craftsman:
            raise serializers.ValidationError("Craftsman does not exist or is not valid")
            
        return data
    
class CraftsmanSerializer(serializers.ModelSerializer):
    """Serializer for listing available craftsmen."""
    bp_code = serializers.SerializerMethodField()
    class Meta:
        model = BusinessPartner
        fields = ['id', 'full_name', 'bp_code']
    
    def get_bp_code(self, obj):
        if hasattr(obj, 'business_name'):
            return f"{obj.bp_code}-{obj.business_name}"
        return str(obj.bp_code)
    

class OrderActionSerializer(serializers.Serializer):
    order_no = serializers.CharField()
    action = serializers.ChoiceField(choices=["accept", "reject"])

class OrderCraftsmanSerializer(serializers.ModelSerializer):
    """Serializer for listing all orders."""
    craftsman = CraftsmanSerializer(read_only=True)
    

    class Meta:
        model = Order
        fields = ['order_no', 'status', 'due_date', 'craftsman']
        
        
class OrderCraftsman(serializers.ModelSerializer):
    craftsman_full_name = serializers.CharField(source='craftsman.full_name', read_only=True)
    craftsman_bp_code = serializers.CharField(source='craftsman.bp_code', read_only=True)

    class Meta:
        model = Order
        fields = ['order_no', 'status', 'created_at', 'craftsman_full_name', 'craftsman_bp_code']
        
        
        
class OrderAssignmentSerializer(serializers.ModelSerializer):
    order_no = serializers.IntegerField()
    bp_code = serializers.CharField()
    due_date = serializers.DateField(required=False)
    
    class Meta:
        model = Order 
        fields = ['order_no', 'bp_code', 'due_date']

    def validate_bp_code(self, value):
        try:
            code_part, business_name_part = value.split("-", 1)
            if not BusinessPartner.objects.filter(
                bp_code=code_part,
                business_name__iexact=business_name_part.strip(),
                role="CRAFTSMAN"
            ).exists():
                raise serializers.ValidationError("No CRAFTSMAN found with this BP Code and Business Name.")
            
            return value
        
        except ValueError:
            raise serializers.ValidationError("BP Code must be in format 'CODE-Business Name'.")

    def validate_order_no(self, value):
        if not Order.objects.filter(id=value).exists():
            raise serializers.ValidationError("Order does not exist.")
        return value
    
class CraftsmanAssignmentSerializer(serializers.Serializer):
    order_no = serializers.CharField(required=True)
    bp_code = serializers.CharField(required=True)  

    def validate_order_no(self, value):
        if not Order.objects.filter(order_no=value).exists():
            raise serializers.ValidationError("Order not found")
        return value

    def validate_bp_code(self, value):
        if not BusinessPartner.objects.filter(bp_code=value, role='CRAFTSMAN').exists():
            raise serializers.ValidationError("Invalid craftsman code or not a craftsman")
        return value
        
class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status by craftsman."""
    order_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=[('in-process', 'In Process')])

    def validate(self, data):
        """Validate order exists and is assigned to the craftsman."""
        request = self.context.get('request')
        SuperAdmin = request.SuperAdmin if request else None

        if not SuperAdmin or SuperAdmin.role_name != 'craftsman':
            raise serializers.ValidationError("Only craftsmen can update orders.")

        try:
            order = Order.objects.get(id=data['order_id'], craftsman=SuperAdmin, state='assigned')
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found or not assigned to you.")

        data['order'] = order
        return data

    def update(self, instance, validated_data):
        """Update order state to in-process."""
        instance.state = 'in-process'
        instance.save()
        return instance
    
class ApproveOrderSerializer(serializers.Serializer):
    """
    Serializer for craftsmen to mark an order as completed and for Admin/Super Admin to approve.
    """
    order_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=[
        ("completed_by_craftsman", "Completed by Craftsman"),
        ("approved", "Approved by Admin"),
    ])

    def validate(self, data):
        """Validate order state and user role."""
        user = self.context['request'].user

        try:
            order = Order.objects.get(id=data['order_id'])
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")

        if data['status'] == "completed_by_craftsman":
            # Craftsman can only mark their own orders as completed
            if order.craftsman != user:
                raise serializers.ValidationError("You can only mark your own orders as completed.")
            if order.state != "assigned":
                raise serializers.ValidationError("Only assigned orders can be marked as completed.")

        elif data['status'] == "approved":
            # Only Admin/Super Admin can approve completed orders
            if user.role_name not in ["admin", "super_admin"]:
                raise serializers.ValidationError("Only Admin or Super Admin can approve orders.")
            if order.state != "completed_by_craftsman":
                raise serializers.ValidationError("Only completed orders can be approved.")

        return data

    def update(self, instance, validated_data):
        """Update the order status."""
        order = Order.objects.get(id=validated_data['order_id'])
        order.state = validated_data['status']
        order.save()
        return order


class CompletedOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for listing completed orders.
    """
    craftsman = serializers.StringRelatedField()

    class Meta:
        model = Order
        fields = ['id', 'name', 'reference_no', 'craftsman', 'state']


class OrderRejectSerializer(serializers.ModelSerializer):
    rejected_by = CraftsmanSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['order_no', 'status', 'created_at', 'craftsman', 'rejected_by']



@receiver(post_save, sender=ResUser)
def assign_bp_code_to_orders(sender, instance, created, **kwargs):
    """Assign user's bp_code to their orders when a new user is created."""
    if created and instance.bp_code:
        Order.objects.filter(user=instance).update(bp_code=instance.bp_code)
        
        
@receiver(post_save, sender=Order)
def set_order_date(sender, instance, created, **kwargs):
    if created and not instance.order_date:
        instance.order_date = date.today()
        instance.save()
 