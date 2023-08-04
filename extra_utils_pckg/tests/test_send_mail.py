import unittest

from extra_utils.send_mail import enviar_mail, send_grid
import os


class MyTestMails(unittest.TestCase):
    def setUp(self) -> None:
        self.mail = 'ernesto.arredondo@portdebarcelona.cat'
        self.api_key = os.getenv('SEND_GRID_API_KEY')
        self.sender = os.getenv('SEND_GRID_SENDER')

    def test_enviar_mail(self):
        codi = enviar_mail('Test', 'This is a test', [self.mail])
        self.assertEqual(codi, 0)

    def test_sendgrid(self):
        result = send_grid(subject='prova',
                           body='prova',
                           user_mail_list=['afeliu@nexusgeographics.com'],
                           api_key=self.api_key,
                           sender=self.sender
                           )
        self.assertIsTrue(result)


if __name__ == '__main__':
    unittest.main()
