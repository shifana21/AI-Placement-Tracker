# 🤖 AI Placement Tracker

> An AI-powered placement preparation and career management platform designed to help college students prepare smarter, track their progress, and understand their placement readiness.

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.x-092E20?logo=django)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React.js-18%2B-61DAFB?logo=react)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql)](https://www.postgresql.org/)
[![AI](https://img.shields.io/badge/AI-Gemini-orange)](https://ai.google.dev/)
[![Git](https://img.shields.io/badge/Git-GitHub-F05032?logo=git)](https://git-scm.com/)

---

## 📌 Overview

**AI Placement Tracker** is a full-stack platform built to help students manage their complete placement preparation journey from a single application.

Instead of using separate tools for resumes, coding practice, aptitude preparation, company eligibility, applications, and interview preparation, the platform brings these activities together and provides AI-powered insights.

### 🎯 Goal

Help students answer three important questions:

* **Am I eligible for a company?**
* **How prepared am I for placements?**
* **What should I improve next?**

---

## ✨ Key Features

### 🔐 Authentication

* Student registration and login
* JWT-based authentication
* Role-based access
* Google OAuth support
* Secure user management

### 👤 Student Profile

* Academic information
* Skills
* CGPA
* Backlogs
* Graduation details
* Career preferences

### 🏢 Company Eligibility Checker

Students can check eligibility based on criteria such as:

* CGPA
* Backlogs
* Graduation year
* Required skills
* Other company-specific requirements

### 📄 AI Resume Analysis

Upload a resume and receive AI-powered analysis including:

* Resume quality insights
* Skill identification
* Missing skills
* Improvement suggestions
* Job-role alignment

### 💻 Coding Progress Tracker

Track:

* Problems solved
* Difficulty levels
* Programming topics
* Progress over time
* Coding consistency

### 🧠 Aptitude Practice

Practice placement-oriented questions across areas such as:

* Quantitative aptitude
* Logical reasoning
* Verbal ability

Performance can be analyzed to identify improvement areas.

### 🎤 AI Mock Interview

Students can practice interview questions and receive AI-assisted feedback on their responses.

### 📊 Placement Readiness Dashboard

A centralized dashboard for tracking:

* Coding progress
* Aptitude performance
* Resume readiness
* Interview preparation
* Application progress
* Overall placement preparation

### 📅 Personalized Study Planner

Generate a preparation plan based on:

* Current skills
* Weak areas
* Target roles
* Placement goals
* Available preparation time

### 📌 Application Tracker

Track job applications with information such as:

* Company
* Role
* Application status
* Applied date
* Interview stages
* Notes

---

## 🧠 AI Capabilities

The platform is designed to use AI for:

```text
Resume Analysis
      ↓
Skill Identification
      ↓
Gap Analysis
      ↓
Personalized Recommendations
      ↓
Study Planning
      ↓
Interview Preparation
```

AI features are intended to make placement preparation more personalized rather than providing the same preparation path to every student.

---

## 🏗️ System Architecture

```text
                 ┌──────────────────────┐
                 │      React.js        │
                 │   Frontend / UI      │
                 └──────────┬───────────┘
                            │
                            │ REST API
                            ▼
                 ┌──────────────────────┐
                 │       Django         │
                 │   Backend + DRF      │
                 └──────────┬───────────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
      ┌────────────┐ ┌────────────┐ ┌────────────┐
      │ PostgreSQL │ │ Gemini AI  │ │ Cloudinary │
      │  Database  │ │  Services  │ │   Files    │
      └────────────┘ └────────────┘ └────────────┘
```

---

## 🛠️ Tech Stack

### Frontend

* React.js
* Tailwind CSS
* Chart.js

### Backend

* Python
* Django
* Django REST Framework

### Database

* PostgreSQL

### Authentication

* JWT
* Google OAuth

### AI

* Gemini API

### Storage

* Cloudinary

### Development & Deployment

* Git
* GitHub
* Docker
* Render
* Vercel
* Neon PostgreSQL

---

## 📂 Project Structure

```text
AI-Placement-Tracker/
│
├── backend/
│   ├── apps/
│   │   └── accounts/
│   │
│   ├── config/
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── README.md
└── .gitignore
```

> Project structure may evolve as additional modules are developed.

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/shifana21/AI-Placement-Tracker.git
cd AI-Placement-Tracker
```

### 2. Create a Python virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file based on:

```text
.env.example
```

Configure the required database, authentication, AI, and storage credentials.

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Start the Django server

```bash
python manage.py runserver
```

The backend will be available at:

```text
http://127.0.0.1:8000/
```

### 7. Start the frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

---

## 📊 Development Roadmap

* [x] Django project setup
* [x] PostgreSQL configuration
* [x] Custom user model
* [x] Student registration
* [x] Authentication foundation
* [ ] Complete JWT authentication
* [ ] Student profile
* [ ] Company eligibility engine
* [ ] Resume upload
* [ ] AI resume analysis
* [ ] Coding tracker
* [ ] Aptitude module
* [ ] AI mock interview
* [ ] Career recommendation
* [ ] Personalized study planner
* [ ] Application tracker
* [ ] Placement readiness dashboard
* [ ] Notifications
* [ ] Production deployment

---

## 🔮 Future Enhancements

* 📱 Mobile application
* 🧠 Advanced skill-gap analysis
* 📈 Placement trend analytics
* 🏢 Company-specific preparation paths
* 🤝 Peer learning features
* 🔔 Smart placement notifications
* 📚 AI-generated learning resources
* 🎯 Personalized role recommendations

---

## 👩‍💻 Author

### Shifana Barveen S

Computer Science and Engineering Student
Interested in Software Engineering, AI/ML, and building practical technology solutions.

**BUILD • LEARN • INNOVATE**

---

## ⭐ Support

If you find this project interesting, consider giving the repository a ⭐ on GitHub.
