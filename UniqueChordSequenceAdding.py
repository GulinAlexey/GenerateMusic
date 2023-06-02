from ChordSequenceComparison import ChordSequenceComparison

class UniqueChordSequenceAdding:
    @staticmethod
    # добавить последовательность аккордов в список уникальных, если её там ещё нет
    def appendUniqueChordSequence(newChordSequence, unicueChordSequenceList):
        # импорт статического метода в качестве функции
        chordSequencesAreEqual = ChordSequenceComparison.chordSequencesAreEqual
        flagNewChordSequenceInUniqueChordSequences = False
        for uChordSequence in unicueChordSequenceList:
            if chordSequencesAreEqual(newChordSequence, uChordSequence):
                flagNewChordSequenceInUniqueChordSequences = True
                break
        if flagNewChordSequenceInUniqueChordSequences == False:
            unicueChordSequenceList.append(newChordSequence)
            return True  # означает, что последовательность аккордов не найдена в списке уникальных, и была добавлена в список
        else:
            return False  # означает, что последовательность аккордов найдена в списке уникальных, и не была добавлена в список