from django.test import TestCase
from django.contrib.auth.models import User
from .models import Order, PickOrder, PackOrder, Delivery
from user.models import ResUser

class OrderProcessingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.res_user = ResUser.objects.create(user=self.user, role_name='staff')
        self.order = Order.objects.create(
            user_id=self.res_user,
            order_no='WR001',
            category='Rings',
            quantity='1',
            weight=10.5,
            weight_unit='g',
            state='accepted'
        )

    def test_pick_order_workflow(self):
        # Create pick order
        pick_order = PickOrder.objects.create(
            order=self.order,
            user=self.user,
            picked_status='pending'
        )
        
        # Confirm pick
        pick_order.confirm_pick()
        pick_order.refresh_from_db()
        
        # Verify pick status and pack order creation
        self.assertEqual(pick_order.picked_status, 'approved')
        self.assertTrue(hasattr(self.order, 'pack_order'))
        self.assertEqual(self.order.pack_order.packed_status, 'pending')

    def test_pack_order_workflow(self):
        # Create pick and confirm it
        pick_order = PickOrder.objects.create(
            order=self.order,
            user=self.user,
            picked_status='pending'
        )
        pick_order.confirm_pick()
        
        # Confirm pack
        pack_order = self.order.pack_order
        pack_order.confirm_pack()
        pack_order.refresh_from_db()
        
        # Verify pack status and delivery creation
        self.assertEqual(pack_order.packed_status, 'approved')
        self.assertTrue(hasattr(self.order, 'delivery'))
        self.assertEqual(self.order.delivery.delivery_status, 'pending')

    def test_delivery_workflow(self):
        # Create pick, confirm it
        pick_order = PickOrder.objects.create(
            order=self.order,
            user=self.user,
            picked_status='pending'
        )
        pick_order.confirm_pick()
        
        # Create pack, confirm it
        pack_order = self.order.pack_order
        pack_order.confirm_pack()
        
        # Confirm delivery
        delivery = self.order.delivery
        delivery.confirm_delivery()
        delivery.refresh_from_db()
        
        # Verify delivery status
        self.assertEqual(delivery.delivery_status, 'delivered')
        self.assertTrue(hasattr(self.order, 'invoice'))
