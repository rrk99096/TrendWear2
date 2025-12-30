from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        # 1. If username is None, try to get 'email' from kwargs
        if username is None:
            username = kwargs.get('email')
            
        try:
            # 2. Look for a user with this email (Case Insensitive)
            user = UserModel.objects.get(email__iexact=username)
        except UserModel.DoesNotExist:
            return None

        # 3. Check the password
        if user.check_password(password):
            return user
        return None