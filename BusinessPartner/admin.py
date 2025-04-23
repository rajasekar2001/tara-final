from django.contrib import admin
from .models import BusinessPartnerKYC,BusinessPartner

admin.site.register(BusinessPartner)
admin.site.register(BusinessPartnerKYC)
