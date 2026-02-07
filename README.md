World Hotels — Hotel Booking Web Application

Project Overview

World Hotels is a full-stack hotel booking web application developed as an academic project.
The system allows users to browse hotels across multiple cities, view room details, compare peak and off-peak pricing, and manage bookings through a personal dashboard. An admin panel is included to manage reservations, users, rooms, and analytics.

This project demonstrates practical implementation of web development concepts including authentication, database integration, role-based access control, and responsive user interface design.

Key Features:

User Features:

User registration and login with secure password hashing

Browse hotels by city

View hotel and room details with pricing

Peak and off-peak season pricing logic

Room booking with date validation

User dashboard to:

View active bookings

View cancelled booking history

Cancel bookings

Currency conversion for booking totals

Cookie preference management (necessary, analytics, marketing)

Admin Features:

Admin authentication and role-based access

Admin dashboard with booking statistics

View all reservations

Cancel bookings as admin

Permanently delete bookings

Manage users, rooms, and analytics

Demo booking data fallback when no records exist

Technology Stack:

Frontend:

HTML5

CSS3

Bootstrap 5

Jinja2 Templates

Backend:

Python (Flask)

Flask Sessions

Password hashing (Werkzeug)

Database

MySQL:

Relational schema with foreign keys

Cookie preferences stored per user

Booking Rules & Business Logic

Users cannot select past dates

Check-out date must be after check-in

Peak season pricing applies during:

April – August

November – December

Off-peak pricing applies for other months

Booking totals are calculated dynamically

Cancelled bookings remain visible in booking history

Cookie Management:

Cookie consent is shown to new users upon first login

Preferences are stored in the database per user

Necessary cookies are always enabled

Users can update cookie preferences via the Cookies settings page

Cookie banner does not reappear once preferences are saved

Project Structure (High Level):

/templates — Jinja2 HTML templates

/static — CSS, images, and assets

app.py — Flask application routes and logic

README.md — Project documentation

Disclaimer:

This website is a demo academic project created for educational purposes only.

No real hotel bookings are processed

No real payments are collected

All data shown is either user-generated or sample/demo data

This project is not affiliated with any real hotel brand

Author:

Developed by Saina Singh

Academic Project — 2025 / 2026
