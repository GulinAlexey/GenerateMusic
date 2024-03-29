import random
from ChordComparison import ChordComparison
from ChordSequenceComparison import ChordSequenceComparison
from UniqueChordSequenceAdding import UniqueChordSequenceAdding

class GrammarNode:
    'Узел дерева грамматики'
    def __init__(self):
        self.value = [] #значение узла - левая часть правила (аккорды)
        self.nextNodes = {}  #словарь, ключ - возможная продукция (аккорд), значение - следующий узел, может быть пуст (None)

    # сгенерировать следующий аккорд для заданной последовательности (на основе правил данного дерева грамматики)
    def generateNextChord(self, baseSequence, listOfChordLists, minNearChordIndex, maxNearChordIndex, endRuleProbability):
        ### импорт статических методов в качестве функций
        chordsAreEqual = ChordComparison.chordsAreEqual
        chordSequencesAreEqual = ChordSequenceComparison.chordSequencesAreEqual
        appendUniqueChordSequence = UniqueChordSequenceAdding.appendUniqueChordSequence
        ###
        #если есть только один подузел, и у него нет потомков, вернуть единственный возможный сл. аккорд (продукцию)
        if len(self.nextNodes.values()) == 1 and list(self.nextNodes.values())[0] == None:
            return list(self.nextNodes.keys())[0]
        pathFromRootToEnd = [] #путь от корня дерева (self) до конечного правила (узлы)
        pathFromRootToEnd.append(self)
        # если данная последовательность состоит только из одного аккорда, то нельзя расширить контекст
        # (контекст расширяется только в пределах baseSequence), поэтому вернуть случайную продукцию корня
        if len(baseSequence) == 1:
            if len(self.nextNodes.keys()) != 0:
                return random.choice(list(self.nextNodes.keys()))
            #если продукций корня нет, вернуть аккорд, находящийся поблизости от текущего в исходном MIDI-файле
            else:
                chordListWithBaseLastChord = None
                indexOfChordInList = 0
                for chordList in listOfChordLists:
                    flagBreak = False
                    for chord in chordList:
                        if chordsAreEqual(chord, baseSequence[-1]):
                            chordListWithBaseLastChord = chordList
                            indexOfChordInList = chordList.index(chord)
                            flagBreak = True
                            break
                    if flagBreak == True:
                        break
                return chordListWithBaseLastChord[max(0, min(indexOfChordInList +
                       random.randint(minNearChordIndex, maxNearChordIndex), len(chordListWithBaseLastChord) - 1))]
        #расширить контекст
        extendedSequence = baseSequence[len(baseSequence)-2:] #два последних аккорда в последовательности
        #найти в подузлах правила для расширенного контекста
        nodesWithExtendedSequence = []
        for nodeKey, nodeValue in self.nextNodes.items():
            if nodeValue != None:
                if chordSequencesAreEqual(nodeValue.value, extendedSequence):
                    appendUniqueChordSequence(nodeValue, nodesWithExtendedSequence)
        #если правил для расширенного контекста не найдено, тогда вернуть случайную продукцию корня или ближайший аккорд
        if len(nodesWithExtendedSequence) == 0:
            if len(self.nextNodes.keys()) != 0:
                return random.choice(list(self.nextNodes.keys()))
            # если продукций корня нет, вернуть аккорд, находящийся поблизости от текущего в исходном MIDI-файле
            else:
                chordListWithBaseLastChord = None
                indexOfChordInList = 0
                for chordList in listOfChordLists:
                    flagBreak = False
                    for chord in chordList:
                        if chordsAreEqual(chord, baseSequence[-1]):
                            chordListWithBaseLastChord = chordList
                            indexOfChordInList = chordList.index(chord)
                            flagBreak = True
                            break
                    if flagBreak == True:
                        break
                return chordListWithBaseLastChord[max(0, min(indexOfChordInList +
                       random.randint(minNearChordIndex, maxNearChordIndex), len(chordListWithBaseLastChord) - 1))]
        #правила для расширенного контекста были найдены
        rule = nodesWithExtendedSequence[0] #правило для контекста
        rule.__generateNextChordDeeper(baseSequence, pathFromRootToEnd, 3) #найти более точное правило, увеличивая контекст
        if random.random() <= endRuleProbability: #с вероятностью endRuleProbability вернуть продукцию конечного правила
            return list(pathFromRootToEnd[-1].nextNodes.keys())[0]
        # с вероятностью (1 - endRuleProbability) вернуть случайную продукцию случайного узла ветви дерева,
        # которая идет от корня до конечного правила
        return random.choice(list((random.choice(pathFromRootToEnd)).nextNodes.keys()))

    #продолжить искать конечное правило для переданной последовательности
    def __generateNextChordDeeper(self, baseSequence, pathFromRootToEnd, contextLevel):
        ### импорт статических методов в качестве функций
        chordSequencesAreEqual = ChordSequenceComparison.chordSequencesAreEqual
        appendUniqueChordSequence = UniqueChordSequenceAdding.appendUniqueChordSequence
        ###
        pathFromRootToEnd.append(self) # добавить данный узел в рассматриваемую ветвь дерева грамматики
        #порядок действий схож с методом generateNextChord()
        if len(self.nextNodes) == 1 and list(self.nextNodes.values())[0] == None:
            return #контекст максимально возможно расширен
        if len(baseSequence) < contextLevel:
            return
        # расширить контекст до contextLevel аккордов в данной последовательности
        extendedSequence = baseSequence[len(baseSequence) - contextLevel:]
        # найти в подузлах правила для расширенного контекста
        nodesWithExtendedSequence = []
        for nodeKey, nodeValue in self.nextNodes.items():
            if nodeValue != None:
                if chordSequencesAreEqual(nodeValue.value, extendedSequence):
                    appendUniqueChordSequence(nodeValue, nodesWithExtendedSequence)
        # если правил для расширенного контекста не найдено, убрать данный узел из рассматриваемой ветви дерева грамматики
        if len(nodesWithExtendedSequence) == 0:
            pathFromRootToEnd.remove(self)
            return
        # правила для расширенного контекста были найдены
        rule = nodesWithExtendedSequence[0] #правило для контекста
        # найти более точное правило, увеличивая контекст
        rule.__generateNextChordDeeper(baseSequence, pathFromRootToEnd, contextLevel + 1)