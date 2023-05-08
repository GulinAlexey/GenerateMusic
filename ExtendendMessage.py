class ExtendendMessage:
    'Сообщение с доп. параметрами'
    def __init__(self, msg, absolute=0, duration=0):
        self.msg = msg #сообщение
        self.absolute = absolute #абсолютное время для сообщения (кол-во тиков с начала)
        self.duration = duration #длительность звучания ноты
