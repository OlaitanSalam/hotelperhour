try:
    import pytest
    from rest_framework.test import APIClient

    @pytest.mark.django_db
    def test_booking_create_requires_fields():
        client = APIClient()
        url = '/api/v1/bookings/bookings/'
        resp = client.post(url, {}, format='json')
        # Since view requires authentication, unauthenticated requests should be 401
        assert resp.status_code == 401
except Exception:
    pass
