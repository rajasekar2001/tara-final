from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.hashers import check_password
from user.models import ResUser, RoleDashboardMapping
from user.serializers import ResUserSerializer, ResAdminUserSerializer, LoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.db.models import Q
from django.conf import settings
import random
from rest_framework.views import APIView


class ResUserRegistrationAPI(generics.GenericAPIView):
    """
    API View for user registration.
    """
    serializer_class = ResUserSerializer
    permission_classes = [AllowAny]
    queryset = ResUser.objects.all()

    def post(self, request):
        """
        Create a new user.
        """
        serializer = self.serializer_class(data=request.data)
        
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)  # Debugging

        email_id = serializer.validated_data.get('email_id')  # Safe get
        mobile_no = serializer.validated_data.get('mobile_no')

        # Check for duplicate email and mobile number
        if email_id and ResUser.objects.filter(email_id=email_id).exists():
            return Response({"error": "Email is already taken"}, status=status.HTTP_400_BAD_REQUEST)
        if mobile_no and ResUser.objects.filter(mobile_no=mobile_no).exists():
            return Response({"error": "Mobile number is already taken"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a unique username
        username = f"User{random.randint(1000, 9999)}"
        user = serializer.save(username=username)
        user.set_password(serializer.validated_data['password'])
        user.save()

        return Response(self.serializer_class(user).data, status=status.HTTP_201_CREATED)

    def get(self, request, id=None):
        """
        Retrieve user(s).
        """
        if id:
            user = get_object_or_404(ResUser, id=id)
            serializer = self.serializer_class(user)
        else:
            users = ResUser.objects.all()
            serializer = self.serializer_class(users, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResUserDetailView(generics.GenericAPIView):
    """
    API for a single Business Partner:
    - GET: Retrieve a Business Partner by email or mobile_no.
    - PUT: Update a Business Partner.
    """
    queryset = ResUser.objects.all()
    serializer_class = ResUserSerializer

    def get_object(self, identifier):
        """Helper method to get the object by email or mobile_no or return 404."""
        # First try to find by email
        try:
            return ResUser.objects.get(email_id=identifier)
        except ResUser.DoesNotExist:
            try:
                # If not found by email, try by mobile_no
                return ResUser.objects.get(mobile_no=identifier)
            except ResUser.DoesNotExist:
                raise Http404("No ResUser matches the given query.")

    def get(self, request, identifier, *args, **kwargs):
        """Retrieve a Business Partner by email or mobile_no."""
        instance = self.get_object(identifier)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, identifier, *args, **kwargs):
        """Update an existing Business Partner using email or mobile_no."""
        instance = self.get_object(identifier)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResUserDeleteView(generics.GenericAPIView):
    """
    API for deleting a Business Partner:
    - DELETE: Delete a Business Partner by email or mobile_no
    """
    queryset = ResUser.objects.all()
    serializer_class = ResUserSerializer

    def get_object(self, identifier):
        """Helper method to get the object by email or mobile_no or return 404."""
        try:
            return ResUser.objects.get(email=identifier)
        except ResUser.DoesNotExist:
            try:
                return ResUser.objects.get(mobile_no=identifier)
            except ResUser.DoesNotExist:
                raise Http404("No ResUser matches the given query.")
            

    def delete(self, request, identifier, *args, **kwargs):
        """Delete a Business Partner by email or mobile_no."""
        instance = self.get_object(identifier)
        instance.delete()
        return Response(
            {
                "status": "success",
                "message": "User deleted successfully",
            },
            status=status.HTTP_200_OK
        )


class ResAdminAPI(generics.GenericAPIView):
    """
    API View for admin registration and management.
    """
    serializer_class = ResAdminUserSerializer
    queryset = ResUser.objects.all()
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Create a new admin.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email_id = serializer.validated_data.get("email_id", None)
        mobile_no = serializer.validated_data.get("mobile_no")

        if not email_id and not mobile_no:
            return Response({"error": "At least one of Email or Mobile Number is required"}, status=status.HTTP_400_BAD_REQUEST)

        existing_user = ResUser.objects.filter(Q(email_id=email_id) | Q(mobile_no=mobile_no)).first()
        if existing_user:
            if email_id and existing_user.email_id == email_id:
                return Response({"error": "Email is already taken"}, status=status.HTTP_400_BAD_REQUEST)
            if existing_user.mobile_no == mobile_no:
                return Response({"error": "Mobile number is already taken"}, status=status.HTTP_400_BAD_REQUEST)

        admin = serializer.save()
        admin.set_password(serializer.validated_data['password'])
        admin.save()

        return Response(self.get_serializer(admin).data, status=status.HTTP_201_CREATED)

    def get(self, request, id=None):
        """
        Retrieve admin(s).
        """
        if id:
            admin = get_object_or_404(ResUser, id=id)
            serializer = self.get_serializer(admin)
        else:
            admins = ResUser.objects.filter(role_name__iexact='admin')
            serializer = self.get_serializer(admins, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        admin = get_object_or_404(ResUser, id=id)
        serializer = self.get_serializer(admin, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  # Debug response
        
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, id):
        """
        Delete an admin.
        """
        admin = get_object_or_404(ResUser, id=id)
        admin.delete()
        return Response({"message": "Admin deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

def get_dashboard_url(role):
    try:
        mapping = RoleDashboardMapping.objects.get(role=role)
        return mapping.dashboard_url
    except RoleDashboardMapping.DoesNotExist:
        return None  # Default behavior if no mapping exists

# @method_decorator(csrf_exempt, name='dispatch')
# class LoginAPIView(generics.GenericAPIView):
#     serializer_class = LoginSerializer
#     permission_classes = [AllowAny]

#     def post(self, request):
#         serializer = self.serializer_class(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         email_or_mobile = serializer.validated_data.get('email_or_mobile')
#         password = serializer.validated_data.get('password')

#         try:
#             # Check if input is email or mobile number
#             if '@' in email_or_mobile:  # If it's an email
#                 current_user = ResUser.objects.get(email_id=email_or_mobile)
#             else:  # If it's a mobile number
#                 current_user = ResUser.objects.get(mobile_no=email_or_mobile)

#         except ResUser.DoesNotExist:
#             return Response({"error": "This email or mobile number is not registered."}, status=status.HTTP_404_NOT_FOUND)

#         if not current_user.check_password(password):
#             return Response({"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

#         if current_user.status != 'active':
#             return Response({"error": "This account is inactive."}, status=status.HTTP_403_FORBIDDEN)

#         # Ensure Role-Dashboard Mapping Exists
#         dashboard_url = get_dashboard_url(current_user.role_name) or "/default-dashboard/"

#         # Safe Permission Fetching
#         try:
#             user_permissions = current_user.user_permissions.all()
#             permission_names = [perm.codename for perm in user_permissions]
#         except Exception as e:
#             permission_names = []
#             print(f"Warning: Could not fetch permissions - {e}")

#         user_data = ResUserSerializer(user).data


#         return Response({
#             'msg': f'Login successful! Welcome, {current_user.full_name}',
#             'user_id': current_user.id,
#             'user_code':current_user.user_code,
#             'role_name': current_user.role_name,
#             'status': current_user.status,
#             'dashboard': dashboard_url,
#             'permissions': permission_names
#         }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class LoginAPIView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email_or_mobile = serializer.validated_data.get('email_or_mobile')
        password = serializer.validated_data.get('password')

        try:
            # Email ya Mobile check
            if '@' in email_or_mobile:
                current_user = ResUser.objects.get(email_id=email_or_mobile)
            else:
                current_user = ResUser.objects.get(mobile_no=email_or_mobile)
        except ResUser.DoesNotExist:
            return Response({"error": "This email or mobile number is not registered."}, status=status.HTTP_404_NOT_FOUND)

        if not current_user.check_password(password):
            return Response({"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

        if current_user.status != 'active':
            return Response({"error": "This account is inactive."}, status=status.HTTP_403_FORBIDDEN)

        # Dashboard URL
        dashboard_url = get_dashboard_url(current_user.role_name) or "/default-dashboard/"

        # Safe Permission Fetching
        try:
            user_permissions = current_user.user_permissions.all()
            # permission_keys = current_user.permission_fields.all()
            permission_names = [perm.codename for perm in user_permissions]
        except Exception as e:
            permission_names = []
            print(f"Warning: Could not fetch permissions - {e}")

        # 🔥 Define permission keys
        permission_keys = [
            "view_only", "copy", "screenshot", "print_perm", "download", "share", "edit",
            "delete_perm", "manage_roles", "approve", "reject", "archive", "restore_perm",
            "transfer", "custom_access", "full_control"
        ]

        # ✅ Dynamically fetch unki current values
        permission_values = {}
        for key in permission_keys:
            permission_values[key] = getattr(current_user, key, False)

        # ✅ Full ResUserSerializer ka use
        # user_data = ResUserSerializer(current_user).data

        return Response({
            'msg': f'Login successful! Welcome, {current_user.full_name}',
            'user_id': current_user.id,
            'user_code': current_user.user_code,
            'role_name': current_user.role_name,
            'status': current_user.status,
            'dashboard': dashboard_url,
            'permissions': permission_names,
            'custom_permissions': permission_values  # 🔥 All boolean permission values here
            # 'user_data': user_data  # 🔥 Isme sari custom permissions included hain
        }, status=status.HTTP_200_OK)
        

class ForgotAPIView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Serializer ke andar logic already handle ho raha hai, toh sirf response return karna hai
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class ResetAPIView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
    
    
    
    