from django.urls import path
from .views import KeyUserApprovalView, AdminVerificationView, OrderCreateView, OrderList, OrderDetailView, NewOrdersListView, AssignOrdersToCraftsman, OrderInProcessAPI, ApproveOrderView, CompletedOrdersView, RejectedOrdersView, CraftsmanOrderResponse, AssignedOrdersList

urlpatterns = [
    path('orders/create', OrderCreateView.as_view(), name='order-create'), # Handles POST (create)
    path('orders/approve/<int:order_no>/', KeyUserApprovalView.as_view(), name='order-approve'),
    path('orders/admin-verification/<str:order_no>/', AdminVerificationView.as_view(), name='admin-verification'),
    path('orders/new-orders/', NewOrdersListView.as_view(), name='new-orders'),
    # path('order-requests/<int:request_id>/verify/', OrderRequestVerificationView.as_view(), name='order-request-verify'),
    path('orders/list', OrderList.as_view(), name='order-list'),  # Handles GET (list)
    path('orders/detail/<str:order_no>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/delete/<int:id>/', OrderCreateView.as_view(), name='update-delete'),  # Handles GET, PUT, DELETE for a specific order
    path('orders/assign-orders/', AssignOrdersToCraftsman.as_view(), name='assign-orders'),
    path('orders/assigned-orders/', AssignedOrdersList.as_view(), name='assigned-orders'),
    path('orders/response-from-order/', CraftsmanOrderResponse.as_view()),
    path('orders/in-process/', OrderInProcessAPI.as_view(), name='order-in-process'),
    path('orders/approve/', ApproveOrderView.as_view(), name='approve-order'),
    path('orders/completed/', CompletedOrdersView.as_view(), name='completed-orders'),
    path('orders/rejected/', RejectedOrdersView.as_view(), name='rejected-orders'),
]