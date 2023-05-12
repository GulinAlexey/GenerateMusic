class Chord:
    'Аккорд - несколько нот (сообщений) одновременно'
    def __init__(self, delay=0):
        self.delay = delay #задержка после предыдущего аккорда
        self.msgs = [] #сообщения (события) аккорда (объекты класса ExtendedMessage)
