from ChordComparison import ChordComparison

class UniqueChordAdding:
    @staticmethod
    def appendUniqueChord(newChord,
                          unicueChordList):  # добавить аккорд в список уникальных аккордов, если его там ещё нет
        chordsAreEqual = ChordComparison.chordsAreEqual # импорт статического метода в качестве функции
        flagChordInUniqueChords = False
        for uChord in unicueChordList:
            if chordsAreEqual(newChord, uChord):
                flagChordInUniqueChords = True
                break
        if flagChordInUniqueChords == False:
            unicueChordList.append(newChord)
            return True  # означает, что аккорд не найден в списке уникальных, и был добавлен в список
        else:
            return False  # означает, что аккорд найден в списке уникальных, и не был добавлен в список