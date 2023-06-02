class ChordComparison:
    @staticmethod
    def chordsAreEqual(chord1,
                       chord2):  # проверка равенства двух аккордов (абсолютное время сообщений может отличаться)
        if chord1.delay != chord2.delay:
            return False
        if len(chord1.msgs) != len(chord2.msgs):
            return False
        for m1 in chord1.msgs:
            flagM1InChord2 = False
            for m2 in chord2.msgs:
                if m1.msg == m2.msg and m1.duration == m2.duration:
                    flagM1InChord2 = True
                    break
            if flagM1InChord2 == False:
                return False
        for m2 in chord2.msgs:
            flagM2InChord1 = False
            for m1 in chord1.msgs:
                if m2.msg == m1.msg and m2.duration == m1.duration:
                    flagM2InChord1 = True
                    break
            if flagM2InChord1 == False:
                return False
        return True