# 🕵️‍♀️ Media Explorer
_Be prepared to see a lot of emojis! 😅_

A web-based media explorer with **user authentication, access control, and group management**.
The project consists of two main scripts:

* **`app.py`** – main web application (Flask + Waitress server)
* **`manage_users.py`** – command-line tool for managing users, groups, and folder access

---

## 📦 Requirements

All dependencies are listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

### 1. Initialize the database

On the first run, the SQLite database (`photobook.db`) will be automatically created.

### 2. Start the main application

Run the server with:

```bash
python app.py
```

By default, the app will start on **`http://localhost:5000`** (Waitress server).
You can log in with previously created users.

### 3. Manage users

Use the CLI tool to manage users and permissions:

```bash
python manage_users.py
```

#### Available options:

* **List users** – show all users and their access rights
* **Add user** – create a new user (with random password by default)
* **Delete user** – remove a user and their access
* **Change password** – update or generate a new password
* **Manage access** – grant or revoke access to private folders
* **Manage groups** – organize users into groups and manage group-level access
* **Link folder** – link existing directories into public or private media storage

---

## 📂 Directory structure

* **PUBLIC/** – media files available to all authenticated users
* **PRIVATE/** – user-specific or restricted media files (access controlled)
* **static/** – static files (CSS, background images, etc.)
* **templates/** – HTML templates for Flask
* **instance/** – user database

---

## 🔒 Authentication & Access

* Login is required for all pages.
* Users can belong to one or more groups.
* Access to private folders is granted individually or via groups.
* Thumbnails for images and videos are automatically generated.

---

## ⚙️ Notes

* By default, the app uses SQLite (`photobook.db`) but can be switched to another database by changing `SQLALCHEMY_DATABASE_URI` in `app.py`.
* Waitress is used as a production-ready WSGI server.
