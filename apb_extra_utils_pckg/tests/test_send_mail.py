import unittest

from apb_extra_utils.send_mail import enviar_mail, send_grid
import os


class MyTestMails(unittest.TestCase):
    def setUp(self) -> None:
        self.mail = os.getenv('TEST_MAIL_TO', 'ernesto.arredondo@portdebarcelona.cat')
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.sender = os.getenv('SENDGRID_SENDER')

    def test_enviar_mail(self):
        codi = enviar_mail('Test', 'This is a test', [self.mail])
        self.assertEqual(codi, 0)

    def test_sendgrid(self):
        result = send_grid(subject='prova sendgrid', body='prova', user_mail_list=[self.mail], sender=self.sender,
                           api_key=self.api_key)
        self.assertEqual(result.get('status_code'), 202)


if __name__ == '__main__':
    unittest.main()
