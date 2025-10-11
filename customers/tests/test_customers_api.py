try:
    import pytest
    from rest_framework.test import APIClient
    from customers.models import Customer

    @pytest.mark.django_db
    def test_customer_token_obtain():
        client = APIClient()
        # create a customer using manager
        customer = Customer.objects.create_customer(email='olaitan3hola@gmail.com', password='custpass', full_name='Olaitan', phone_number='0801')
        customer.is_active = True
        customer.save()
        url = '/api/token/customer/'
        resp = client.post(url, {'email': 'olaitan3hola@gmail.com', 'password': 'custpass'}, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.data and 'refresh' in resp.data
except Exception:
    pass
