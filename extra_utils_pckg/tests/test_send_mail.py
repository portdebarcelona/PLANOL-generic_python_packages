import unittest

from extra_utils.send_mail import enviar_mail, send_grid


class MyTestMails(unittest.TestCase):
    def setUp(self) -> None:
        self.mail = 'ernesto.arredondo@portdebarcelona.cat'

    def test_enviar_mail(self):
        codi = enviar_mail('Test', 'This is a test', [self.mail])
        self.assertEqual(codi, 0)

    def test_sendgrid(self):
        result = send_grid(subject='prova',
                           body='prova',
                           api_key='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',
                           user_mail_list=['afeliu@nexusgeographics.com'])
        self.assertIsTrue(result)


if __name__ == '__main__':
    unittest.main()
