
    
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router1 = DefaultRouter()
router1.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    # Authentication URLs
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    
    # Cart URLs
    path('cart/add/', AddToCartView.as_view(), name='add-to-cart'),
    path('cart/remove/', Delete_Product_fromCart.as_view(), name='remove-from-cart'),
    path('cart/total/', total_price, name='cart-total'),
    
    # Order URLs
    path('order/create/', Make_order.as_view(), name='create-order'),
    path('order/cancel/<int:order_id>/', CancelOrder.as_view(), name='cancel-order'),
    path('order/vendor-orders/', watching_order_product, name='vendor-orders'),
    path('orders/<int:pk>/driver/<int:pk1>/', Select_Driver_To_Delivery.as_view(), name='assign-driver'),
    
    
    # Driver URL
    path('driver/location/', Track_Driver.as_view(), name='track-driver'),
    
    
    # Include router URLs
    path('', include(router.urls)),
    
    
     path('', include(router1.urls)),
]