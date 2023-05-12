from ChordComparison import chordsAreEqual

#проверка равенства двух последовательностей (списков) аккордов
#(абсолютное время сообщений в аккордах может отличаться)
def chordSequencesAreEqual(chordSequence1, chordSequence2):
    if len(chordSequence1) != len(chordSequence2):
        return False
    for chord1 in chordSequence1:
        if not chordsAreEqual(chord1, chordSequence2[chordSequence1.index(chord1)]):
            return False
    return True