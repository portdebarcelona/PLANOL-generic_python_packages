import unittest

from extra_utils.send_mail import enviar_mail


class MyTestMails(unittest.TestCase):
    def setUp(self) -> None:
        self.mail = 'ernesto.arredondo@portdebarcelona.cat'

    def test_enviar_mail(self):
        codi = enviar_mail('Test', 'This is a test', [self.mail])
        self.assertEqual(codi, 0)


if __name__ == '__main__':
    unittest.main()
