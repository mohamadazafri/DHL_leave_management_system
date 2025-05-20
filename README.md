# DHL Leave Management System

A modern and user-friendly leave management system built with Django and MongoDB, featuring a beautiful UI powered by Tailwind CSS.

## Features

- 🎨 Modern and responsive UI with Tailwind CSS
- 📊 Interactive dashboard with leave statistics
- 📅 Visual leave calendar
- 📱 Mobile-friendly design
- 🔐 Role-based access control (Admin, HR Manager, Employee)
- 📧 Email notifications
- 📁 Document attachments
- 📝 Audit logging
- 🔄 Real-time updates
- 📈 Leave balance tracking

## Prerequisites

- Python 3.8+
- MongoDB 4.0+
- Node.js and npm (for Tailwind CSS)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd dhl-leave-management
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root and add your configuration:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# MongoDB Settings
MONGODB_HOST=mongodb://localhost:27017
MONGODB_NAME=dhl_leave_management

# Email Settings
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
ADMIN_EMAIL=sivanesan.letchumanan@dhl.com
```

5. Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

6. Create a superuser:

```bash
python manage.py createsuperuser
```

7. Run the development server:

```bash
python manage.py runserver
```

## Usage

1. Access the admin interface at `http://localhost:8000/admin/` to:

   - Create leave types
   - Manage employees
   - Configure leave balances

2. Regular users can:

   - Apply for leave
   - View their leave history
   - Check leave balances
   - View the leave calendar

3. HR/Admin users can:
   - Approve/reject leave applications
   - View all employees' leaves
   - Generate reports
   - Manage leave types and policies

## Project Structure

```
dhl_leave_management/
├── core/                   # Project settings
├── leave_management/       # Main application
│   ├── models.py          # Database models
│   ├── views.py           # View logic
│   ├── forms.py           # Form definitions
│   ├── urls.py            # URL routing
│   └── admin.py           # Admin interface
├── templates/             # HTML templates
│   ├── base.html         # Base template
│   └── leave_management/  # App-specific templates
├── static/               # Static files
├── media/               # User-uploaded files
├── requirements.txt     # Python dependencies
└── manage.py           # Django management script
```

## API Endpoints

The system provides REST API endpoints for integration with UiPath:

- `POST /api/leaves/` - Create a new leave application
- `GET /api/leaves/` - List all leave applications
- `GET /api/leaves/<id>/` - Get leave application details
- `PATCH /api/leaves/<id>/` - Update leave application status

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Django](https://www.djangoproject.com/)
- [MongoDB](https://www.mongodb.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Font Awesome](https://fontawesome.com/)
- [FullCalendar](https://fullcalendar.io/)
