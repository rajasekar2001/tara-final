from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import BusinessPartner, BusinessPartnerKYC
from .serializers import BusinessPartnerSerializer, BusinessPartnerKYCSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.generics import ListAPIView

# API for listing only BUYER data
class BuyerListView(ListAPIView):
    queryset = BusinessPartner.objects.filter(role="BUYER")
    serializer_class = BusinessPartnerSerializer

# API for listing only CRAFTSMAN data
class CraftsmanListView(ListAPIView):
    queryset = BusinessPartner.objects.filter(role="CRAFTSMAN")
    serializer_class = BusinessPartnerSerializer



class BusinessPartnerView(generics.GenericAPIView):
    """
    API for BusinessPartner:
    - GET: Retrieve all Business Partners or filter by `bp_code`.
    - POST: Create a new Business Partner.
    """
    queryset = BusinessPartner.objects.all()
    serializer_class = BusinessPartnerSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Get all Business Partners or filter by `bp_code`.
        """
        bp_code = request.query_params.get("bp_code")
        queryset = self.get_queryset().filter(bp_code=bp_code) if bp_code else self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """
        Create a new Business Partner.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BusinessPartnerDetailView(generics.GenericAPIView):
    """
    API for a single Business Partner:
    - GET: Retrieve a Business Partner by bp_code.
    - PUT: Update a Business Partner.
    """
    queryset = BusinessPartner.objects.all()
    serializer_class = BusinessPartnerSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self, bp_code):
        """Helper method to get the object or return 404 using bp_code."""
        return get_object_or_404(BusinessPartner, bp_code=bp_code)

    def get(self, request, bp_code, *args, **kwargs):
        """Retrieve a Business Partner by bp_code."""
        instance = self.get_object(bp_code)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, bp_code, *args, **kwargs):
        """Update an existing Business Partner using bp_code."""
        instance = self.get_object(bp_code)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BusinessPartnerDeleteView(APIView):
    """
    API to delete a Business Partner using bp_code.
    """

    def delete(self, request, bp_code, *args, **kwargs):
        """Delete a Business Partner by bp_code."""
        user = get_object_or_404(BusinessPartner, bp_code=bp_code)
        user.delete()
        return Response({"detail": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    def get(self, request, bp_code, *args, **kwargs):
        """Handle deletion using GET request (Not recommended)."""
        user = get_object_or_404(BusinessPartner, bp_code=bp_code)
        user.delete()
        return Response({"detail": "User deleted successfully using GET request"}, status=status.HTTP_200_OK)



class BusinessPartnerKYCView(generics.GenericAPIView):
    """
    API for BusinessPartnerKYC:
    - GET: Retrieve all KYC entries or filter by `bp_code`.
    - POST: Create a new KYC entry.
    """
    queryset = BusinessPartnerKYC.objects.all()
    serializer_class = BusinessPartnerKYCSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Retrieve Business Partner KYC details or filter by `bp_code`."""
        bp_code = request.query_params.get("bp_code")
        queryset = self.get_queryset().filter(bp_code=bp_code) if bp_code else self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """Create a new BusinessPartnerKYC entry."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BusinessPartnerKYCDetailView(generics.GenericAPIView):
    """
    API for a single Business Partner KYC:
    - GET: Retrieve a KYC entry by bp_code.
    - PUT: Update a KYC entry.
    - DELETE: Delete a KYC entry.
    """
    queryset = BusinessPartnerKYC.objects.all()
    serializer_class = BusinessPartnerKYCSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self, bis_no):
        """Helper method to get the object or return 404 using bp_code."""
        return get_object_or_404(BusinessPartnerKYC, bis_no=bis_no)

    def get(self, request, bis_no, *args, **kwargs):
        """Retrieve a Business Partner KYC entry using bp_code."""
        instance = self.get_object(bis_no)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, bis_no, *args, **kwargs):
        """Update an existing Business Partner KYC entry using bp_code."""
        instance = self.get_object(bis_no)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, bis_no, *args, **kwargs):
        """Delete a Business Partner KYC entry using bp_code."""
        instance = self.get_object(bis_no)
        instance.delete()
        return Response({"message": "Business Partner KYC deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

class BusinessPartnerKycFreeze(APIView):
    """API to retrieve and freeze a Business Partner KYC entry."""

    def get_object(self, bis_no):
        return get_object_or_404(BusinessPartnerKYC, bis_no=bis_no)

    def get(self, request, bis_no, *args, **kwargs):
        """Retrieve Business Partner KYC details before freezing."""
        instance = self.get_object(bis_no)
        serializer = BusinessPartnerKYCSerializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, bis_no, *args, **kwargs):
        """Freeze the Business Partner KYC entry."""
        partner = self.get_object(bis_no)
        partner.freezed = True
        partner.save()
        serializer = BusinessPartnerKYCSerializer(partner)
        return Response(
            # {'message': 'Business Partner freezed successfully', 'data': serializer.data},
            {'message': 'Business Partner freezed successfully'},
            status=status.HTTP_200_OK
        )


class BusinessPartnerKycRevoke(APIView):
    """API to retrieve and revoke (unfreeze) a Business Partner KYC entry."""

    def get_object(self, bis_no):
        return get_object_or_404(BusinessPartnerKYC, bis_no=bis_no)

    def get(self, request, bis_no, *args, **kwargs):
        """Retrieve Business Partner KYC details before revoking."""
        instance = self.get_object(bis_no)
        serializer = BusinessPartnerKYCSerializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, bis_no, *args, **kwargs):
        """Revoke (Unfreeze) the Business Partner KYC entry."""
        partner = self.get_object(bis_no)
        partner.freezed = False
        partner.save()
        serializer = BusinessPartnerKYCSerializer(partner)
        return Response(
            # {'message': 'Business Partner revoked successfully', 'data': serializer.data},
            {'message': 'Business Partner revoked successfully'},
            status=status.HTTP_200_OK
        )
        
class YourModelViewSet(viewsets.ModelViewSet):
    queryset = BusinessPartnerKYC.objects.all()
    serializer_class = BusinessPartnerKYCSerializer
        
        
        
        
        
# Below method super_admin have authority to freeze and revoke
# admin have authority to just view the freeze and revoke data


# class IsSuperAdminOrReadOnly(permissions.BasePermission):
#     """
#     Custom permission to allow only super admins to modify data,
#     while admins can only read (GET).
#     """

#     def has_permission(self, request, view):
#         if request.method == "GET":
#             return request.user.is_authenticated and request.user.role == "admin"
#         return request.user.is_authenticated and request.user.role == "super_admin"


# class BusinessPartnerKycFreeze(APIView):
#     """API to retrieve and freeze a Business Partner KYC entry."""
    
#     permission_classes = [IsSuperAdminOrReadOnly]  # Apply permission

#     def get_object(self, bis_no):
#         return get_object_or_404(BusinessPartnerKYC, bis_no=bis_no)

#     def get(self, request, bis_no, *args, **kwargs):
#         """Retrieve Business Partner KYC details before freezing."""
#         instance = self.get_object(bis_no)
#         serializer = BusinessPartnerKYCSerializer(instance)
#         return Response(serializer.data, status=status.HTTP_200_OK)

#     def post(self, request, bis_no, *args, **kwargs):
#         """Freeze the Business Partner KYC entry (Only Super Admin)."""
#         partner = self.get_object(bis_no)
#         partner.freezed = True
#         partner.save()
#         return Response({'message': 'Business Partner freezed successfully'}, status=status.HTTP_200_OK)


# class BusinessPartnerKycRevoke(APIView):
#     """API to retrieve and revoke (unfreeze) a Business Partner KYC entry."""
    
#     permission_classes = [IsSuperAdminOrReadOnly]  # Apply permission

#     def get_object(self, bis_no):
#         return get_object_or_404(BusinessPartnerKYC, bis_no=bis_no)

#     def get(self, request, bis_no, *args, **kwargs):
#         """Retrieve Business Partner KYC details before revoking."""
#         instance = self.get_object(bis_no)
#         serializer = BusinessPartnerKYCSerializer(instance)
#         return Response(serializer.data, status=status.HTTP_200_OK)

#     def post(self, request, bis_no, *args, **kwargs):
#         """Revoke (Unfreeze) the Business Partner KYC entry (Only Super Admin)."""
#         partner = self.get_object(bis_no)
#         partner.freezed = False
#         partner.save()
#         return Response({'message': 'Business Partner revoked successfully'}, status=status.HTTP_200_OK)



