# encoding: utf-8

from django.test import TestCase
from django.core import mail

from cc3.cyclos.tests.test_factories import UserFactory

from .models import MailMessage


class TestEmail(TestCase):
    def setUp(self):
        # Create a user that can be emailed.
        self.user = UserFactory.create()

    def test_email_generation(self):
        # Delete the auto-installed MailMessage, as type is unique.
        MailMessage.objects.all().delete()

        # Create a template that can be used to email the user.
        content = """
        Dear {{ user.email }}
        """.strip()
        expected_body = content.replace("{{ user.email }}", self.user.email)

        subject_template = "Test email to {{ user.email }}"
        expected_subject = subject_template.replace(
            "{{ user.email }}", self.user.email)

        # Used to load a template from the database, now Email model has the
        # template in the email as a text field.
        template = content
        email, _ = MailMessage.objects.get_or_create(
            subject=subject_template, type="newreg", body=template)
        context = {'user': self.user}
        message = email.get_msg(self.user.email, context=context)

        # Asserts:
        self.assertEqual(message.subject, expected_subject)
        self.assertEqual(message.body, expected_body)

        # Test manager

        msg = MailMessage.objects.get_msg('newreg')
        self.assertEqual(msg, email)

        # Test manager with invalid language

        msg = MailMessage.objects.get_msg('newreg', 'voodoo')
        self.assertEqual(msg, email)

        # Test sending an email

        self.assertEqual(len(mail.outbox), 0)
        msg.send(self.user.email, context=context)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, expected_subject)
        self.assertEqual(mail.outbox[0].body, expected_body)
