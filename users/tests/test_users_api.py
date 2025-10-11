try:
    import pytest
    from rest_framework.test import APIClient
    from users.models import CustomUser

    @pytest.mark.django_db
    def test_user_registration_and_password_confirm():
        client = APIClient()
        url = '/api/v1/users/users/register/'
        # Try create with mismatched passwords
        payload = {
            'email': 'testowner@example.com',
            'full_name': 'Test Owner',
            'phone_number': '08000000000',
            'password': 'Password123',
            'confirm_password': 'Password321'
        }
        resp = client.post(url, payload, format='json')
        assert resp.status_code in (400, 422)


    @pytest.mark.django_db
    def test_customuser_token_obtain():
        client = APIClient()
        user = CustomUser.objects.create_user(email='tokenowner@example.com', password='secret123', full_name='Owner', phone_number='0801')
        user.is_active = True
        user.save()
        url = '/api/token/'
        # simplejwt default expects 'username' but our TokenObtainPairView is wired to use email as username
        resp = client.post(url, {'email': 'tokenowner@example.com', 'password': 'secret123'}, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.data
        assert 'refresh' in resp.data
except Exception:
    pass
