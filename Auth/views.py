from rest_framework import generics, permissions,status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import generics,filters,viewsets
from .serializers import *
from .models import *
from .permission import is_VendorandOwner
from .filter import ProductFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .serializers import CartSerializer
from django.db.models import F, Sum
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from rest_framework.decorators import action
from django.utils import timezone
import random
import string






class AllowAnyPermission(permissions.AllowAny):
    pass


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAnyPermission]
    serializer_class = RegisterSerializer
    
    
class LoginView(TokenObtainPairView):
    permission_classes = [AllowAnyPermission]
    serializer_class = EmailTokenObtainPairSerializer


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAnyPermission]

class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=204)
    
    

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    
    earch_fields=['name','description']
    ordering_fields=['name','price','stock']
    permission_classes = [is_VendorandOwner]
    
    def perform_create(self, serializer):
        # Automatically set the vendor to the current user
        serializer.save(vendor=self.request.user)
        
        
        
        
        
        
        
        
         

####all what is below i didn't do a url


class AddToCartView(APIView):
    def post(self, request):
        user = request.user
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        product = get_object_or_404(Product, id=product_id)

        # Get or create a cart for this user
        cart, created = Cart.objects.get_or_create(user=user)

        # Check if the item already exists
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity, "price": product.price}
        )

        if not created:
            # If it already exists, just update the quantity
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
class Delete_Product_fromCart(APIView):
    def delete(self,request):
        user=request.user
        product_id=request.data.get("product_id")
        cart=get_object_or_404(Cart,user=user)
        product=CartItem.objects.filter(product_id=product_id).first()
        if product:
            product.delete()
            return Response({"message":"product deleted succesfully"},status=200)

        return Response({"error":"there is not the product in your cart"},status=404)
    
    

def total_price(request):
    user=request.user
    cart=get_object_or_404(Cart,user=user)
    cartitems=CartItem.objects.filter(cart=cart)


    result = cart.items.aggregate(
        total=Sum(F("quantity") * F("product__price"))
    )
    total = result["total"] or 0
    return Response({"total": total}, status=200)
        

class Make_order(APIView):
    def post(self, request):
        user = request.user
        cart = get_object_or_404(Cart, user=user)
        
        # Optimized: Use select_related to fetch product data in one query
        cartitems = CartItem.objects.filter(cart=cart).select_related('product')
        
        # Check if cart is empty
        if not cartitems.exists():
            return Response(
                {"error": "Cart is empty"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Optimized: Calculate total in database using aggregation
        total_price = cartitems.aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total']
        
        # Use transaction to ensure data integrity 
        #ya tfayli ga3 l'order wla ydkhoul ga3 
        #bch maykoun items f l'order w w7dokhr lala
        with transaction.atomic():
            
            order = Order.objects.create(
                user=user,
                total_price=total_price
            )
            
            # Optimized: Bulk create all order items at once
            order_items=[]
            for cart_item in cartitems: 
                
                
                order_item= OrderItem(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price_at_purchase=cart_item.product.price
                )
             
            
                order_items.append(order_item)
                    
            OrderItem.objects.bulk_create(order_items)
            
            # Optional: Clear the cart after order creation
            cartitems.delete()
        
        return Response(
            {"message": "Order created successfully", "order_id": order.id},
            status=status.HTTP_201_CREATED
        )
        
from django.utils import timezone
from datetime import timedelta
class CancelOrder(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status == Order.StatusChoices.PENDING:
    # Can cancel anytime
            order.status = Order.StatusChoices.CANCELED
        elif order.status == Order.StatusChoices.CONFIRMED:
    # Can cancel within 2 hours
            time_since_order = timezone.now() - order.created_at
            if time_since_order < timedelta(hours=6):
                order.status = Order.StatusChoices.CANCELED
            else:
                return Response({"error": "Too late to cancel"})
            order.save()
            
    

def watching_order_product(request):
    user =request.user
    if not user.is_authenticated:
        return Response({"error": "Not authenticated"}, status=401)

    if user.role not in ['vendor', 'admin']:
        return Response({"error": "Permission denied"}, status=403)
    order_items= OrderItem.objects.filter(product__vendor_user=user.id).select_related('product','order__user').annotate(subtotal=F("quantity") * F("product__price"))
    data = [
    {
        'id': item.id,
        'order_id': item.order.id,
        'product_name': item.product.name,
        'quantity': item.quantity,
        'subtotal': item.subtotal,   # use property
        'customer': item.order.user.username,
        'created_at': item.order.created_at,
        }
    for item in order_items
    ]

    return Response(data, status=200)    





class Track_Driver(APIView):
    permission_classes=[IsAuthenticated]
    def patch(self,request):
        if request.user.role=='driver':
            try:
                driver=request.user
                latitude = request.data.get('latitude')  # Note: 'latitude', not 'current_latitude'
                longitude = request.data.get('longitude')
                
                
                try:
                    lat_float = float(latitude)
                    lon_float = float(longitude)
                    
                    if not (-90 <= lat_float <= 90):
                        return Response(
                            {'error': 'Latitude must be between -90 and 90'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    if not (-180 <= lon_float <= 180):
                        return Response(
                            {'error': 'Longitude must be between -180 and 180'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    return Response(
                        {'error': 'Invalid coordinate format'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
                
                
                driver.current_latitude = lat_float
                driver.current_longitude = lon_float
                driver.last_location_update = timezone.now()
                driver.save()
                serializer = DriverLocationSerializer(driver)
                return Response(serializer.data,status=status.HTTP_200_OK)
            
            
            except Exception as e:
                return Response(
                    {'error': f'Something went wrong: {str(e)}'},  # ✅ Dictionary
                    status=status.HTTP_400_BAD_REQUEST)
                
                
        if request.user.role != 'driver':
            return Response(
                {'error': 'Only drivers can update location'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        


# payments/views.py





class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        
        return Payment.objects.filter(user=self.request.user)
    
    def list(self, request):
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        
        payment = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.get_serializer(payment)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='initiate')
    def initiate_payment(self, request):
        
        # Validate input data
        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            amount=serializer.validated_data['amount'],
            card_type=serializer.validated_data['card_type'],
            order_reference=serializer.validated_data.get('order_reference', ''),
            description=serializer.validated_data.get('description', ''),
            status='pending'
        )
        
        # Log the initiation
        PaymentLog.objects.create(
            payment=payment,
            status='pending',
            message='Payment initiated successfully'
        )
        
        # Return payment info
        return Response({
            'payment_id': payment.id,
            'status': payment.status,
            'amount': str(payment.amount),
            'card_type': payment.card_type,
            'order_reference': payment.order_reference,
            'payment_url': f'/payment/process/{payment.id}/',
            'message': 'Payment initiated. Redirect user to payment_url to enter card details.'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='process')
    def process_payment(self, request, pk=None):
        """
        Process payment with card details (Mock)
       
        """
        # Get payment
        payment = self.get_object()
        
        # Check if payment can be processed
        if payment.status != 'pending':
            return Response({
                'error': f'Payment cannot be processed. Current status: {payment.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate card details
        serializer = MockCardDetailsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        card_number = serializer.validated_data['card_number']
        
        # Update payment to processing
        payment.status = 'processing'
        payment.save()
        
        PaymentLog.objects.create(
            payment=payment,
            status='processing',
            message='Processing payment with provided card details'
        )
        
        # Mock payment gateway processing
        payment_result = self._mock_payment_gateway(card_number, payment)
        
        # Update payment with result
        payment.status = payment_result['status']
        payment.transaction_id = payment_result['transaction_id']
        payment.card_last_four = card_number[-4:]
        
        if payment_result['status'] == 'success':
            payment.completed_at = timezone.now()
        
        payment.save()
        
        # Log the result
        PaymentLog.objects.create(
            payment=payment,
            status=payment.status,
            message=payment_result['message']
        )
        
        return Response({
            'payment_id': str(payment.id),
            'status': payment.status,
            'transaction_id': payment.transaction_id,
            'message': payment_result['message'],
            'completed_at': payment.completed_at,
            'order_reference': payment.order_reference
        })
    
    @action(detail=True, methods=['get'], url_path='verify')
    def verify_payment(self, request, pk=None):
        
        payment = self.get_object()
        
        return Response({
            'payment_id': str(payment.id),
            'status': payment.status,
            'amount': str(payment.amount),
            'card_type': payment.card_type,
            'transaction_id': payment.transaction_id,
            'order_reference': payment.order_reference,
            'created_at': payment.created_at,
            'completed_at': payment.completed_at
        })
    
    @action(detail=True, methods=['get'], url_path='logs')
    def payment_logs(self, request, pk=None):
        """
        Get all logs for a payment
        """
        payment = self.get_object()
        logs = payment.logs.all()
        serializer = PaymentLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='history')
    def payment_history(self, request):
       
        queryset = self.get_queryset()
        
        # Optional filters
        status_filter = request.query_params.get('status', None)
        card_type_filter = request.query_params.get('card_type', None)
        order_ref_filter = request.query_params.get('order_reference', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if card_type_filter:
            queryset = queryset.filter(card_type=card_type_filter)
        if order_ref_filter:
            queryset = queryset.filter(order_reference=order_ref_filter)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def _mock_payment_gateway(self, card_number, payment):
        """
        Mock payment gateway simulation
        Simulates what SATIM or a real payment gateway would do
        
        Returns:
            dict: {
                'status': 'success' or 'failed',
                'transaction_id': 'TXN_XXXXX',
                'message': 'Success/failure message'
            }
        """
        # Generate mock transaction ID
        transaction_id = 'TXN_' + ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=12)
        )
        
        # Test card numbers with predefined outcomes
        test_cards = {
            '4111111111111111': ('success', 'Payment processed successfully'),
            '4000000000000002': ('failed', 'Insufficient funds'),
            '4000000000000119': ('failed', 'Card declined by issuer'),
            '4000000000000127': ('failed', 'Invalid card details'),
            '4000000000000259': ('failed', 'Card expired'),
        }
        
        # Check if it's a test card
        if card_number in test_cards:
            result_status, result_message = test_cards[card_number]
        else:
            # Random outcome for other cards (80% success rate)
            if random.random() < 0.8:
                result_status = 'success'
                result_message = 'Payment processed successfully'
            else:
                # Random failure
                failures = [
                    'Transaction declined by bank',
                    'Insufficient funds',
                    'Card expired',
                    'Invalid CVV',
                    'Card blocked'
                ]
                result_status = 'failed'
                result_message = random.choice(failures)
        
        return {
            'status': result_status,
            'transaction_id': transaction_id,
            'message': result_message
        }  
    
    
    
class Select_Driver_To_Delivery(APIView):
    def post(self,request,pk,pk1):
        
        if request.user.role!='admin':
            return Response({"error":"unauthorized"},status=status.HTTP_401_UNAUTHORIZED)
        order = get_object_or_404(Order, id=pk)
        
        if order.driver is not None:
            return Response({"error":"the order has already a driver"},status=status.HTTP_403_FORBIDDEN)
        driver=get_object_or_404(DriverProfile,id=pk1,availability_status='available')
        order.driver=driver
        order.save()
        return Response({
        "success": f"Driver {driver.id} assigned to order {order.id}",
        "order": {
            "id": order.id,
            "status": order.status,
                # add more fields
        },
        "driver": {
            "id": driver.id,
            "name": driver.user.get_full_name(),
            # add more fields
            }
        }, status=status.HTTP_200_OK)
