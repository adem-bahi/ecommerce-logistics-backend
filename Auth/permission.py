from rest_framework.permissions import BasePermission,SAFE_METHODS

class is_VendorandOwner(BasePermission):
    def has_permission(self, request, view):
        if request.method=='POST':
            if request.user.is_authenticated and request.user.role == "vendor":
                return True
            return False
        return True
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.vendor==request.user
    
        
    