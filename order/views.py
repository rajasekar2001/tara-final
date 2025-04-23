from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from .models import Order
from BusinessPartner.models import BusinessPartner
from .serializers import OrderSerializer, CraftsmanSerializer, OrderCraftsmanSerializer, OrderAssignmentSerializer, OrderActionSerializer
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


# Helper function to check if user role is valid
def is_valid_user_role(user): 
    """
    Check if the user's role is one of the allowed roles:
    'admin', 'staff', 'seller', 'customer'.
    """
    valid_roles = ['Super Admin', 'Admin', 'Key User', 'User']
    return user.role_name in valid_roles

class OrderRequestCreateView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(collected_by=self.request.user, status='pending')
        
class OrderRequestVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        user = request.user
        if user.role_name != 'Key User':
            return Response({"detail": "Only Key Users can verify."}, status=status.HTTP_403_FORBIDDEN)

        order_request = get_object_or_404(Order, id=request_id)
        action = request.data.get('action')
        if order_request.status != 'pending':
            return Response({"detail": "Request already verified."}, status=status.HTTP_400_BAD_REQUEST)
        if action == 'accept':
            order = Order.objects.create(
                product_name=order_request.product_name,
                quantity=order_request.quantity,
                customer_name=order_request.customer_name,
                created_by=user
            )
            order_request.status = 'accepted'
            order_request.save()
            return Response({"detail": "Order accepted and created.", "order_id": order.id}, status=status.HTTP_201_CREATED)

        elif action == 'reject':
            order_request.status = 'rejected'
            order_request.save()
            return Response({"detail": "Order request rejected."}, status=status.HTTP_200_OK)

        return Response({"detail": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
    

class OrderCreateView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Get all Orders or filter by `bp_code`.
        Shows pending orders for regular users, shows all for staff/admin users.
        """
        bp_code = request.query_params.get("bp_code")
        queryset = self.get_queryset()
        
        if bp_code:
            queryset = queryset.filter(bp_code=bp_code)
        if not request.user.is_staff:
            queryset = queryset.filter(created_by=request.user, status='pending')
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, *args, **kwargs):
        """
        User submits an order (status = 'pending').
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.validated_data['status'] = 'pending'
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KeyUserApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_no, *args, **kwargs):
        """
        Key User approves an order – set status to 'in-process'
        """
        order = get_object_or_404(Order, id=order_no)

        if order.status != 'pending':
            return Response(
                {"error": "Only pending orders can be approved by key user."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'in-process'
        order.key_user_approval_notes = request.data.get('approval_notes', '')
        order.approved_by_key_user = request.user
        order.save()

        return Response({
            "message": "Order approved by Key User. Waiting for Admin verification.",
            "order_no": order_no,
            "status": "in-process",
            "approved_by": request.user.username,
        }, status=status.HTTP_200_OK)

    def delete(self, request, order_no, *args, **kwargs):
        """
        Key User rejects an order – delete the pending order
        """
        order = get_object_or_404(Order, id=order_no)

        if order.status != 'pending':
            return Response(
                {"error": "Only pending orders can be rejected by Key User."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejection_notes = request.data.get('rejection_notes', '')
        order.delete()

        return Response({
            "message": "Order rejected by Key User and deleted.",
            "order_no": order_no,
            # "rejected_by": request.user.username,
            "rejection_notes": rejection_notes
        }, status=status.HTTP_200_OK)
        
        
class AdminVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_no, *args, **kwargs):
        """
        Admin approves an order – set status to 'verified'
        """
        order = get_object_or_404(Order, id=order_no)

        if order.status != 'in-process':
            return Response(
                {"error": "Only in-process orders can be verified by admin."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'verified'
        order.admin_approval_notes = request.data.get('approval_notes', '')
        order.verified_by_admin = request.user
        order.save()

        return Response({
            "message": "Order verified by admin. Ready for craftsman assignment.",
            "order_no": order_no,
            "status": "verified",
            "verified_by": request.user.username,
        }, status=status.HTTP_200_OK)

    def delete(self, request, order_no, *args, **kwargs):
        """
        Admin rejects an order – set status to 'admin-rejected'
        """
        order = get_object_or_404(Order, id=order_no)

        if order.status != 'in-process':
            return Response(
                {"error": "Only in-process orders can be rejected by admin."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'admin-rejected'
        order.admin_rejection_notes = request.data.get('rejection_notes', '')
        order.rejected_by_admin = request.user
        order.save()

        return Response({
            "message": "Order rejected by admin.",
            "order_no": order_no,
            "status": "admin-rejected",
            "rejected_by": request.user.username,
        }, status=status.HTTP_200_OK)

class NewOrdersListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        new_orders = Order.objects.filter(status='in-process')
        serializer = OrderSerializer(new_orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

        
class OrderList(generics.GenericAPIView):
    
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        Get all Order or filter by `bp_code`.
        """
        bp_code = request.query_params.get("bp_code")
        queryset = self.get_queryset().filter(bp_code=bp_code) if bp_code else self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
        
class OrderDetailView(generics.GenericAPIView):
    """
    - GET: Retrieve a Order by bp_code.
    - PUT: Update a Order.
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    

    def get_object(self, order_no):
        """Helper method to get the object or return 404 using bp_code."""
        return get_object_or_404(Order, order_no=order_no)

    def get(self, request, order_no, *args, **kwargs):
        """Retrieve a Order by bp_code."""
        instance = self.get_object(order_no)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, order_no, *args, **kwargs):
        """Update an existing Order using bp_code."""
        instance = self.get_object(order_no)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Automatically assign the logged-in user to the order"""
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Custom create method to ensure user authentication"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        return super().create(request, *args, **kwargs)




# class AssignOrdersToCraftsman(APIView):
#     permission_classes = [IsAuthenticated]
    
#     def get(self, request):
#         """Return all new orders (in-process) and available craftsmen."""
#         new_orders = Order.objects.filter(status="in-process")
#         craftsmen = BusinessPartner.objects.filter(role='CRAFTSMAN')

#         # order_serializer = OrderCraftsmanSerializer(new_orders, many=True)
#         craftsman_serializer = CraftsmanSerializer(craftsmen, many=True)

#         return Response({
#             "craftsmen": craftsman_serializer.data
#         })
            
#     def post(self, request, *args, **kwargs):
#         serializer = OrderAssignmentSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             order_no = serializer.validated_data['order_no']
#             combined_bp_code = serializer.validated_data['bp_code']
#             code_part, business_name_part = combined_bp_code.split("-", 1)
#             craftsman = get_object_or_404(
#                 BusinessPartner,
#                 bp_code=code_part,
#                 business_name__iexact=business_name_part.strip(),
#                 role="CRAFTSMAN"
#             )
#             order = get_object_or_404(Order, id=order_no)
#             order.craftsman = craftsman
#             order.status = "assigned"
#             order.save()

#             return Response({
#                 "status": "success",
#                 "message": f"Order {order_no} assigned to {craftsman.full_name}"
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({
#                 "status": "error",
#                 "message": str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)


class AssignOrdersToCraftsman(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return all new orders (in-process) and available craftsmen."""
        new_orders = Order.objects.filter(status="in-process")
        craftsmen = BusinessPartner.objects.filter(role='CRAFTSMAN')

        craftsman_serializer = CraftsmanSerializer(craftsmen, many=True)

        return Response({
            "craftsmen": craftsman_serializer.data
        })
            
    def post(self, request, *args, **kwargs):
        serializer = OrderAssignmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            order_no = serializer.validated_data['order_no']
            combined_bp_code = serializer.validated_data['bp_code']
            due_date = serializer.validated_data.get('due_date')  # Get the due_date from serializer
            
            code_part, business_name_part = combined_bp_code.split("-", 1)
            craftsman = get_object_or_404(
                BusinessPartner,
                bp_code=code_part,
                business_name__iexact=business_name_part.strip(),
                role="CRAFTSMAN"
            )
            order = get_object_or_404(Order, id=order_no)
            order.craftsman = craftsman
            order.status = "assigned"
            
            if due_date:  # Only update due_date if it was provided
                order.due_date = due_date
                
            order.save()

            return Response({
                "status": "success",
                "message": f"Order {order_no} assigned to {craftsman.full_name}",
                "due_date": order.due_date.strftime('%Y-%m-%d') if order.due_date else None
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
    
class AssignedOrdersList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return all orders assigned to a craftsman (regardless of status)."""
        assigned_orders = Order.objects.filter(craftsman__isnull=False)
        order_serializer = OrderCraftsmanSerializer(assigned_orders, many=True)

        return Response({
            "orders": order_serializer.data
        })

class CraftsmanOrderResponse(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = OrderActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order_no = serializer.validated_data['order_no']
        action = serializer.validated_data['action']

        try:
            order = Order.objects.get(order_no=order_no)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.status != "assigned":
            return Response({"error": "Order is already in assigned state"}, status=status.HTTP_400_BAD_REQUEST)

        if action == "accept":
            order.status = "in-process"
            order.save()
            return Response({
                "status": "success",
                "message": f"Order {order_no} accepted and is now in-process",
                "order_status": order.status,
                "craftsman": order.craftsman.full_name
            })

        elif action == "reject":
            current_craftsman = order.craftsman
            order.status = "rejected"
            order.rejected_by = current_craftsman
            order.craftsman = None
            order.save()
            
            
            next_craftsman = self.get_next_available_craftsman(order)            
            if next_craftsman:
                order.craftsman = next_craftsman
                order.status = "assigned"
                order.save()
                
                return Response({
                    "message": f"Order {order_no} reassigned to {next_craftsman.full_name}",
                    "new_craftsman": next_craftsman.full_name,
                    "new_craftsman_bp_code": f"{next_craftsman.bp_code}-{next_craftsman.business_name}",
                    "order_status": order.status
                })
            else:
                return Response({
                    "message": f"Order {order_no} rejected by {current_craftsman}",
                    "order_status": order.status
                })

    def get_next_available_craftsman(self, order):       
        rejected_by = Order.objects.filter(
            order_no=order.order_no,
            status='rejected'
        ).values_list('craftsman__id', flat=True)
        
        return BusinessPartner.objects.filter(
            role="CRAFTSMAN"
        ).exclude(
            id__in=rejected_by
        ).first()
            
class CraftsmanAssignedOrders(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assigned_orders = Order.objects.filter(status='assigned')
        serializer = OrderSerializer(assigned_orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class OrderInProcessAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(status='in-process')
        serializer = OrderCraftsmanSerializer(orders, many=True)
        return Response(serializer.data)
    
# class RejectedOrdersView(APIView):
#     permission_classes = [IsAuthenticated]
    
#     def get(self, request):
#         orders = Order.objects.filter(status='rejected').select_related('craftsman')
#         serializer = OrderCraftsmanSerializer(orders, many=True)
#         return Response(serializer.data)

class RejectedOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rejected_orders = Order.objects.filter(status="rejected").values(
            'order_no',
            'rejected_by__full_name',
            'rejected_by__bp_code',
            'rejected_by__business_name',
        )

        return Response({
            "rejected_orders": list(rejected_orders),
            "total_rejected": rejected_orders.count()
        }, status=status.HTTP_200_OK)
    
class ApproveOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_no = request.data.get("order_no")
        try:
            order = Order.objects.get(order_no=order_no)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.status != "in-process":
            return Response({"error": "Order is not in-process"}, status=status.HTTP_400_BAD_REQUEST)

        order.status = "awaiting-approval"
        order.save()

        return Response({
            "message": f"Order {order_no} marked as completed by craftsman, waiting for approval"
        })

class CompletedOrdersView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        completed_orders = Order.objects.filter(status="complete")
        serializer = OrderCraftsmanSerializer(completed_orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        order_no = request.data.get("order_no")
        try:
            order = Order.objects.get(order_no=order_no)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.status != "awaiting-approval":
            return Response({"error": "Order is not awaiting approval"}, status=status.HTTP_400_BAD_REQUEST)

        order.status = "complete"
        order.save()

        return Response({
            "status": "completed",
            "message": f"Order {order_no} approved and marked as complete"
        })
        
        
        