from django.urls import path
from .views import BusinessPartnerView, BusinessPartnerDetailView, BusinessPartnerKYCView, BusinessPartnerDeleteView, BusinessPartnerKYCDetailView, BusinessPartnerKycFreeze, BusinessPartnerKycRevoke, BuyerListView, CraftsmanListView

urlpatterns = [
    path('BusinessPartner/create', BusinessPartnerView.as_view(), name='BusinessPartner-create'), 
    path('BusinessPartner/list', BusinessPartnerView.as_view(), name='BusinessPartner-list'), 
    path('BusinessPartner/detail/<str:bp_code>/', BusinessPartnerDetailView.as_view(), name='BusinessPartner-detail'), 
    path('BusinessPartner/delete/<str:bp_code>/', BusinessPartnerDeleteView.as_view(), name='BusinessPartner-delete'),
    path('BusinessPartner/revoke/<str:bp_code>/', BusinessPartnerDetailView.as_view(), {'action': 'revoke'}, name='BusinessPartner-revoke'),
    path('BusinessPartner/freeze/<str:bp_code>/', BusinessPartnerDetailView.as_view(), {'action': 'freeze'}, name='BusinessPartner-freeze'),
    path('BusinessPartner/Buyers/', BuyerListView.as_view(), name="buyer-list"),
    path('BusinessPartner/Craftsmans/', CraftsmanListView.as_view(), name="craftsman-list"),


    # BusinessPartner KYC
    path('BusinessPartnerKYC/create', BusinessPartnerKYCView.as_view(), name='BusinessPartnerKYC-create'),
    path('BusinessPartnerKYC/list', BusinessPartnerKYCView.as_view(), name='BusinessPartnerKYC-list'),
    path('BusinessPartnerKYC/detail/<str:bis_no>/', BusinessPartnerKYCDetailView.as_view(), name='BusinessPartner-detail'), 
    path('BusinessPartner/delete/<str:bis_no>/', BusinessPartnerKYCDetailView.as_view(), name='BusinessPartner-delete'),
    path('BusinessPartnerKYC/freeze/<str:bis_no>/', BusinessPartnerKycFreeze.as_view(), name='freeze_business_partner'),
    path('BusinessPartnerKYC/revoke/<str:bis_no>/', BusinessPartnerKycRevoke.as_view(), name='revoke_business_partner'),

]
