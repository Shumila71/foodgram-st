import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Load test users data'

    def handle(self, *args, **options):
        try:
            with open('data/users.json', 'r', encoding='utf-8') as file:
                users_data = json.load(file)

            for user_data in users_data:
                if not User.objects.filter(email=user_data['email']).exists():
                    User.objects.create_user(**user_data)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created user {user_data["username"]}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'User {user_data["username"]} already exists'
                        )
                    )

            self.stdout.write(
                self.style.SUCCESS('Successfully loaded all users')
            )

        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    'File data/users.json not found. '
                    'Please make sure the file exists in the data directory.'
                )
            )
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR(
                    'Invalid JSON format in data/users.json'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading users: {str(e)}')
            )
