from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .models import *
User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    # enforce unique email at serializer level (DB unique already set)
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name", "role")
        
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True  # or hold for email verification if you implement it
        user.save()
        return user
    
    
    
class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Works with USERNAME_FIELD='email'. Adds role + names into token & response.
    """

    @classmethod
    def get_token(cls, user,):
        print("DEBUG user:", user)  # see what kind of object you’re getting
        print("DEBUG fields:", dir(user)) 
        token=super().get_token(user)
        token["role"]=user.role
        token["email"]=user.email
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        data.update=({
            "user": {
                "id": self.user.id,
                "email": self.user.email,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "role": self.user.role,
            }
        })
        return data
    
    
    
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    
    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except Exception:
            # Don’t leak specifics. If it fails, raise validation error.
            raise serializers.ValidationError("Invalid or expired refresh token.")
        
class CategorySerializer(serializers.Serializer):
    class Meta:
        model=Category
        fields="__all__"       

class ProductSerializer(serializers.Serializer):
    product_category=serializers.CharField(source='product.category')
    product_vendor=serializers.CharField(source='product.vendor')
    class Meta:
        model=Product
        fields=("name","price","description","stock","is_available","product_category","product_vendor")
    
    
    
class CartItemSerializer(serializers.Serializer):
    product_name=serializers.CharField(source='product.name',read_only=True)
    class Meta:
        model=CartItem
        fields=["id", "product", "product_name", "quantity", "price"]
        


class CartSerializer(serializers.Serializer):
    items=CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "created_at", "items"]
        
        
class OrderItemSerializer(serializers.Serializer):
    product_name=serializers.CharField(source='product.name',read_only=True)
    class Meta:
        model=OrderItem
        fields=["id","product_name","product","quantity","price"]        






class OrderSerializer(serializers.Serializer):
    items =OrderItemSerializer(many=True,read_only=True)
    class Meta:
        model=Order
        fields=["id","items","created_at","user","statue"]
        
        
        
class DriverLocationSerializer(serializers.Serializer):
    name=serializers.CharField(source="user.first_name", read_only=True)
    class Meta:
        model=DriverProfile
        fields=["id","name","current_longitude","current_latitude","last_location_update"]
        
        
        
        
        
        
# payments/serializers.py
from rest_framework import serializers
from .models import Payment, PaymentLog

class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for displaying payment details"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 
            'user', 
            'user_email',
            'amount', 
            'card_type', 
            'status',
            'card_last_four', 
            'transaction_id', 
            'order_reference',
            'description', 
            'created_at', 
            'updated_at', 
            'completed_at'
        ]
        read_only_fields = [
            'id', 
            'user', 
            'status', 
            'transaction_id', 
            'card_last_four',
            'created_at', 
            'updated_at', 
            'completed_at'
        ]


class PaymentInitiateSerializer(serializers.Serializer):
    """Serializer for initiating a payment"""
    amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=100,
        help_text="Amount in DZD (minimum 100)"
    )
    card_type = serializers.ChoiceField(
        choices=['dahabia', 'cib'],
        help_text="Card type: dahabia or cib"
    )
    order_reference = serializers.CharField(
        max_length=100, 
        required=False,
        help_text="Order number (e.g., ORD-20251004-12345)"
    )
    description = serializers.CharField(
        required=False, 
        allow_blank=True,
        max_length=500,
        help_text="Payment description"
    )
    
    def validate_amount(self, value):
        """Validate payment amount"""
        if value < 100:
            raise serializers.ValidationError("Minimum payment amount is 100 DZD")
        if value > 10000000:
            raise serializers.ValidationError("Maximum payment amount is 10,000,000 DZD")
        return value
    
    def validate_card_type(self, value):
        """Validate card type"""
        if value not in ['dahabia', 'cib']:
            raise serializers.ValidationError("Card type must be 'dahabia' or 'cib'")
        return value


class MockCardDetailsSerializer(serializers.Serializer):
    """Serializer for mock card details input"""
    card_number = serializers.CharField(
        max_length=16, 
        min_length=16,
        help_text="16-digit card number"
    )
    cardholder_name = serializers.CharField(
        max_length=100,
        help_text="Name on card"
    )
    expiry_month = serializers.CharField(
        max_length=2,
        help_text="Expiry month (01-12)"
    )
    expiry_year = serializers.CharField(
        max_length=2,
        help_text="Expiry year (25 for 2025)"
    )
    cvv = serializers.CharField(
        max_length=3, 
        min_length=3,
        help_text="3-digit CVV"
    )
    
    def validate_card_number(self, value):
        """Validate card number"""
        if not value.isdigit():
            raise serializers.ValidationError("Card number must contain only digits")
        
        if len(value) != 16:
            raise serializers.ValidationError("Card number must be exactly 16 digits")
        
        return value
    
    def validate_expiry_month(self, value):
        """Validate expiry month"""
        if not value.isdigit():
            raise serializers.ValidationError("Month must be numeric")
        
        month = int(value)
        if month < 1 or month > 12:
            raise serializers.ValidationError("Month must be between 01 and 12")
        
        return value
    
    def validate_expiry_year(self, value):
        """Validate expiry year"""
        if not value.isdigit():
            raise serializers.ValidationError("Year must be numeric")
        
        year = int(value)
        if year < 25:
            raise serializers.ValidationError("Card has expired")
        
        return value
    
    def validate_cvv(self, value):
        """Validate CVV"""
        if not value.isdigit():
            raise serializers.ValidationError("CVV must contain only digits")
        
        if len(value) != 3:
            raise serializers.ValidationError("CVV must be exactly 3 digits")
        
        return value
    
    def validate_cardholder_name(self, value):
        """Validate cardholder name"""
        if not value.strip():
            raise serializers.ValidationError("Cardholder name is required")
        
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Cardholder name too short")
        
        return value.strip()


class PaymentVerifySerializer(serializers.Serializer):
    """Serializer for verifying payment status"""
    payment_id = serializers.UUIDField(
        help_text="Payment UUID"
    )


class PaymentLogSerializer(serializers.ModelSerializer):
    """Serializer for payment logs"""
    class Meta:
        model = PaymentLog
        fields = ['status', 'message', 'timestamp']
        read_only_fields = ['status', 'message', 'timestamp']


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Simplified serializer for payment history listing"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    card_type_display = serializers.CharField(source='get_card_type_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'user_email',
            'amount',
            'card_type',
            'card_type_display',
            'status',
            'status_display',
            'order_reference',
            'transaction_id',
            'created_at',
            'completed_at'
        ]
        read_only_fields = fields