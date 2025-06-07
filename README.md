Hotel per Hour
A Django web application that enables users to book hotels by the hour, offering flexibility for short stays. Hotel owners can register a single hotel, manage rooms, view bookings, and generate sales reports. The platform uses Mapbox for location-based features, Bootstrap for responsive design, and Paystack for secure payments.
Table of Contents

Technologies Used
Installation
Project Structure
Usage
Contributing
License
Acknowledgments

Technologies Used

Django: Web framework (version 4.0+ recommended).
Python: Programming language (version 3.9+ recommended).
SQLite3: Database for storing hotel, room, and booking data.
Mapbox: For interactive maps and geocoding.
Bootstrap: For responsive front-end styling.
Paystack: For payment processing.

Installation
To set up "Hotel per Hour" locally, follow these steps:

Clone the Repository:
git clone https://github.com/your-username/hotel-per-hour.git
cd hotel-per-hour


Create a Virtual Environment:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install Dependencies:
pip install -r requirements.txt

Ensure requirements.txt includes:
django>=4.0
psycopg2-binary
requests
geopy







Configure API Keys:

Mapbox: Obtain an API key from Mapbox and add to settings.py:MAPBOX_ACCESS_TOKEN = 'your_mapbox_api_key'


Paystack: Get a secret key from Paystack and add to settings.py:PAYSTACK_SECRET_KEY = 'your_paystack_secret_key'




Apply Migrations:
python manage.py migrate


Create a Superuser:
python manage.py createsuperuser


Run the Development Server:
python manage.py runserver

Access the app at http://localhost:8000.


Project Structure



Directory/File
Description



hotel_per_hour/
Main Django project directory


  settings.py
Project settings (database, static files, API keys)


  urls.py
URL configurations


  wsgi.py
WSGI configuration for deployment


hotels/
App for hotel-related functionality


  models.py
Hotel and Room models


  views.py
Views for hotel management (create, edit, delete, bookings, rooms, sales)


  templates/hotels/
Templates (e.g., hotel_dashboard.html, hotel_rooms.html)


  forms.py
Forms for hotel and room creation


  admin.py
Admin interface for hotels and rooms


bookings/
App for booking-related functionality


  models.py
Booking model


  views.py
Views for booking management (create, verify, cancel)


  templates/bookings/
Templates (e.g., book_room.html, confirmation.html)


  forms.py
Forms for booking creation


users/
App for user authentication (assumed)


static/
Static files (CSS, JavaScript, images)


media/
User-uploaded files (e.g., hotel/room images)


templates/
Base templates (e.g., base.html)


requirements.txt
Project dependencies


manage.py
Django management script


Usage
For Hotel Owners

Sign up and verify your email to become a hotel owner.
Log in and access the dashboard (/hotels/dashboard/).
Register one hotel with details (name, address, image, location via Mapbox).
Add rooms with type, price, description, capacity, and image.
View bookings, manage room availability, and generate sales reports for your hotel.
Toggle room availability for unpaid bookings directly from the rooms page.
Verify bookings using the booking reference on the verification page.

For Users

Search hotels by location or browse approved hotels (/hotels/).
Select a hotel, view available rooms, and book by choosing check-in/out times.
Pay via Paystack or opt for pay-later (if available).


For Admins

Log in as a superuser (/admin/).
Approve or decline hotel registrations with email notifications.
Manage hotels, rooms, and bookings via the admin interface.

Contributing
Contributions are welcome! To contribute:

Fork the repository.
Create a feature branch: git checkout -b feature/your-feature.
Commit changes: git commit -m "Add your feature".
Push to your fork: git push origin feature/your-feature.
Open a pull request against the main branch.

Before submitting:

Run tests: python manage.py test.
Check code style: flake8 ..
Update documentation if needed.



Django for the robust web framework.
Mapbox for interactive maps and geocoding.
Bootstrap for responsive styling.
Paystack for secure payment processing.

