import secrets
import string
import os
from app import app, db, User, FolderAccess, PRIVATE_DIRECTORY, PRIVATE_PATH, PUBLIC_DIRECTORY, PUBLIC_PATH
from collections import defaultdict

# Path to the folder with private files

def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def list_users():
    users = User.query.all()
    if not users:
        print("\nNo users found in the database.")
        return
    print("\n--- User List ---")
    for user in users:
        accesses = [acc.folder_name for acc in user.accesses]
        print(f"  ID: {user.id}, Username: {user.username}, Access: {', '.join(accesses) or 'none'}, Groups: {user.group.split(',')}")
    print("-----------------")

def add_user():
    print("\n--- Add New User ---")
    while True:
        username = input("Enter username: ").strip()
        if not username:
            print("Username cannot be empty."); continue
        if User.query.filter_by(username=username).first():
            print("User with this username already exists."); continue
        break

    group = input("Enter user groups (leave empty for none, separate multiple with commas): ").strip().replace(" ", "")
    
    password = generate_password()
    new_user = User(username=username, group=group)
    new_user.set_password(password)
    
    # Create personal folder and grant access
    personal_folder_path = os.path.join(PRIVATE_PATH, username)
    os.makedirs(personal_folder_path, exist_ok=True)
    access = FolderAccess(user=new_user, folder_name=username)
    
    db.session.add(new_user)
    db.session.add(access)
    db.session.commit()
    
    print("\nUser created successfully!")
    print(f"  Username 📝: {username}")
    print(f"  Password 🔑: {password}")
    print(f"  Folder '{personal_folder_path}' was created and access granted.")

def delete_user():
    username = input("\nEnter username to delete: ").strip()
    user = User.query.filter_by(username=username).first()
    if not user:
        print("User not found."); return
    
    if input(f"Are you sure you want to delete user '{username}'? (yes/no): ").lower() == 'yes':
        db.session.delete(user)
        db.session.commit()
        print(f"User '{username}' and their access rights were deleted.")
    else:
        print("Action canceled.")

def change_password():
    username = input("\nEnter username: ").strip()
    user = User.query.filter_by(username=username).first()
    if not user:
        print("User not found."); return
    
    new_password = input("Enter new password (leave empty for random password): ")
    if not new_password:
        new_password = generate_password()
    user.set_password(new_password)
    db.session.commit()
    print(f"Password for '{username}' was changed to: {new_password}")

def manage_access():
    username = input("\nEnter username to manage access (leave empty for all users): ").strip()
    if not username:
        users = User.query.all()
    else:
        users = [User.query.filter_by(username=username).first()]
    if not users or users[0] is None:
        print("User not found."); return

    while True:
        if len(users) == 1:
            print(f"\nManaging access for: {users[0].username}")
            print("Current access:", ", ".join([a.folder_name for a in users[0].accesses]) or "none")
        else:
            print("\nManaging access for all users")
        print("\n1. ✅ Grant access\n2. ❌ Revoke access\n3. ↩️ Back")
    
        choice = input("> ")
        match choice:
            case '1': grant_access(users)
            case '2': revoke_access(users)
            case '3': break
            case _: continue

def grant_access(users: list):
    print("\nAvailable private folders:")
    try:
        os.makedirs(PRIVATE_PATH, exist_ok=True)
        private_folders = [f for f in os.listdir(PRIVATE_PATH) if (os.path.isdir(os.path.join(PRIVATE_PATH, f)) or os.path.islink(os.path.join(PRIVATE_PATH, f)))]
        if not private_folders:
            print(f"No folders found in '{PRIVATE_DIRECTORY}'."); return
        for folder in private_folders: print(f"  - {folder}")
    except Exception as e:
        print(f"Error while reading folders: {e}"); return

    folder_name = input("Enter folder name to grant access: ").strip()
    if folder_name not in private_folders:
        print("Invalid folder name."); return
    for user in users:
        if FolderAccess.query.filter_by(user_id=user.id, folder_name=folder_name).first():
            print(f"User {user.username} already has access.")
        else:
            db.session.add(FolderAccess(user_id=user.id, folder_name=folder_name))

    db.session.commit()
    print(f"Access to folder '{folder_name}' was granted.")

def revoke_access(users: list):
    folder_name = input("\nEnter folder name to revoke access: ").strip()
    for user in users:
        access = FolderAccess.query.filter_by(user_id=user.id, folder_name=folder_name).first()
        if not access:
            print("User does not have access to this folder."); return
        
        db.session.delete(access)
    db.session.commit()
    print(f"Access to folder '{folder_name}' was revoked.")


def get_groups() -> dict[str, list[str]]:
    """
    Iterate through all users and return a dictionary where the key is the group name
    and the value is a list of users in that group.

    Returns:
        dict[str, list[str]]: Dictionary of groups and their members.
    """
    groups = defaultdict(list)
    all_users = User.query.all()

    for user in all_users:
        if not user.group:
            continue

        user_groups = user.group.split(',')

        for group_name in user_groups:
            # Clean group name and append the username under the group key
            cleaned_name = group_name.strip()
            if cleaned_name:
                groups[cleaned_name].append(user.username)

    return dict(groups)

def manage_groups():
    while True:
        print("\n--- Manage Groups ---")
        print("1. 📋 List groups\n2. ✏️ Change user groups\n3. ✅ Grant access\n4. ❌ Revoke access\n5. ↩️ Back")

        choice = input("> ").strip()
        match choice:
            case '1': # List groups
                groups = get_groups()
                if not groups:
                    print("\nNo groups found in the database.")
                else:
                    print("\n--- Group List ---")
                    for group in groups:
                        print(f"  {group} - {', '.join(groups[group])}")
                    print("-------------------")
            case '2': # Change user groups
                while True:
                    username = input("\nEnter username: ").strip()
                    user = User.query.filter_by(username=username).first()
                    if not user:
                        print("User not found.")
                        continue
                    else:
                        break
                new_group = input("Enter group names (separate multiple with commas): ").strip().replace(" ", "")
                user.set_group(new_group)
                db.session.commit()
                print(f"Groups for user {username} were changed to: {new_group.split(',')}.")
            case '3': # Grant access to a group
                groups = get_groups()
                while True:
                    group = input("Enter group name: ").strip()
                    if not group in groups:
                        print("\nGroup not found.")
                        continue
                    else: break
                grant_access([User.query.filter_by(username=u).first() for u in groups[group]])

            case '4': # Revoke access from a group
                groups = get_groups()
                while True:
                    group = input("Enter group name: ").strip()
                    if not group in groups:
                        print("\nGroup not found.")
                        continue
                    else: break
                revoke_access([User.query.filter_by(username=u).first() for u in groups[group]])
            case '5': break
            case _: continue

def link_folder():
    while True:
        path = input("\nEnter folder path to link: ").replace('"', '')
        if os.path.isdir(path): break
        else: print("The given path is not a folder!")
    
    publicity = input("Should the folder be [p]ublic or [r]estricted/private (default - private): ").lower().strip()[:1]
    match publicity:
        case "p":
            os.system(f'mklink /D "{os.path.join(PUBLIC_PATH, os.path.basename(path))}" "{path}"')
        case _:
            os.system(f'mklink /D "{os.path.join(PRIVATE_PATH, os.path.basename(path))}" "{path}"')
    print(f"Folder {path} has been linked.")

def main_menu():
    with app.app_context():
        db.create_all()

    while True:
        print("\n===== User Management =====")
        print("1. 📋 List users\n2. 👨 Add user\n3. 🗑️ Delete user\n4. ✏️ Change password\n5. 🔑 Manage access\n6. 👪 Manage groups\n7. 📁 Link folder (admin only)\n8. ❌ Exit")
        choice = input("> ").strip()

        with app.app_context():
            actions = {'1': list_users, '2': add_user, '3': delete_user, '4': change_password, '5': manage_access, '6': manage_groups, '7': link_folder}
            if choice in actions:
                actions[choice]()
            elif choice == '8':
                break
            else:
                print("Invalid choice.")

if __name__ == '__main__':
    try:
        main_menu()
    except KeyboardInterrupt:
        exit()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
