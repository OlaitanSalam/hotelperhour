# HotelPerHour

![HotelPerHour Logo](static/img/illustrations/hotellogo2.jpg)

HotelPerHour is a Django-based web platform that allows users to book hotel rooms by the hour, providing flexible, affordable, and discreet stays. It caters to business travelers, couples, and anyone needing short-term accommodations without paying for full-day rates. The platform includes user authentication for customers and hotel owners, loyalty rewards, real-time availability checks, secure payments via Paystack, SMS/email notifications, and customizable admin interfaces.

## Features

### For Customers
- **Hourly Bookings**: Book rooms for 3, 6, or 9 hours with real-time availability checks.
- **Loyalty Program**: Earn 10 points per hour booked; redeem points for discounts (10% per 1000 points, customizable via admin).
- **Discount Application**: Use all available points for maximum discount (capped at 100%), with immediate deduction upon booking.
- **Extra Services**: Add optional services like breakfast or spa during booking.
- **Payment Integration**: Secure payments via Paystack, with discounted amounts reflected.
- **Booking Verification**: Check reservation details using reference and email (for authenticated and non-authenticated users).
- **Dashboard**: View reservations, loyalty points, and used points; update profile (name, phone number).
- **Notifications**: Receive SMS/email confirmations and cancellations via API.

### For Hotel Owners
- **Hotel Management**: Register, edit, and delete hotels; add rooms and extra services.
- **Dashboard**: View hotels, bookings, rooms, and sales reports (with date filtering and commissions).
- **Booking Verification**: Verify bookings by reference.
- **Room Availability Toggle**: Mark rooms as available/unavailable.
- **Sales Reports**: Daily sales, commissions (5%), and payouts.
- **Notifications**: Receive SMS/email for new bookings.

### General Features
- **Search and Filtering**: Search hotels by name/address; filter rooms by capacity, price, availability.
- **Geolocation**: Nearby hotel search using Mapbox.
- **Responsive Design**: Mobile-friendly with offcanvas menu, responsive tables, and hamburger navigation.
- **UI Enhancements**: AOS animations, Bootstrap 5, Font Awesome icons.
- **Security**: User type checks for dashboards; restricted access.
- **Admin Customizations**: Custom admin panel with "HotelPerHour Admin" branding; loyalty rules configurable.

## Prerequisites

- Python 3.8+
- Django 4.2+
- PostgreSQL (or SQLite for development)
- Paystack account (for payments)
- Yournotify account (for SMS)
- Brevo account (for email)
- Mapbox account (for geolocation)

## Installation

1. **Clone the Repository**:
   ```
   git clone https://github.com/OlaitanSalami/hotelperhour.git
   cd hotelperhour
   ```

2. **Create a Virtual Environment**:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**:
   Create a `.env` file in the project root:
   ```
   SECRET_KEY=your_secret_key
   DEBUG=True
   DATABASE_URL=postgres://user:password@localhost/dbname
   PAYSTACK_SECRET_KEY=your_paystack_key
   YOURNOTIFY_API_KEY=your_yournotify_key
   YOURNOTIFY_SENDER_ID=your_sender_id
   MAPBOX_ACCESS_TOKEN=your_mapbox_token
   ```

5. **Apply Migrations**:
   ```
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create Superuser**:
   ```
   python manage.py createsuperuser
   ```

7. **Run the Server**:
   ```
   python manage.py runserver
   ```
   Access at `http://127.0.0.1:8000/`.

## Usage

### Customer Flow
1. Register/Login as a customer.
2. Search and book hotels/rooms by hour.
3. Apply loyalty points for discounts (deducted immediately).
4. Pay via Paystack.
5. Receive SMS/email confirmations.
6. View bookings and profile in dashboard.

### Hotel Owner Flow
1. Register/Login as a hotel owner.
2. Add/edit hotels, rooms, and services.
3. Manage availability, view bookings/sales.
4. Verify bookings by reference.

### Admin
Access `/admin/` to manage users, hotels, loyalty rules, bookings, etc. Customize loyalty settings like points per percent, max discount, min points.

## Configuration

- **Loyalty Rules**: Admin-configurable; points per percent discount, max discount (%), min points to use.
- **Payments**: Configure Paystack keys in `.env`; discounts applied to total amount.
- **Notifications**: Set Yournotify API key and sender ID for SMS; email via Django settings.
- **Geolocation**: Mapbox token for hotel location mapping.
- **UI**: Bootstrap 5, AOS animations, Font Awesome; responsive for mobile.

## Development

- **Run Tests**: `python manage.py test`
- **Static Files**: `python manage.py collectstatic`
- **Custom Filters**: Used `humanize` for formatting (thousand separators).

## License
MIT License. See [LICENSE](LICENSE) for details.

## Contact
For support, contact [https://wa.link/n9n2o4].