import PySimpleGUI as sg        #версия 4.61.0.173
import mido                     #версия 1.2.10
import os
import statistics
import copy
from itertools import groupby
from datetime import datetime
import time

from ExtendendMessage import ExtendendMessage
from Chord import Chord
from UniqueChordAdding import UniqueChordAdding
from ChordComparison import ChordComparison
from GrammarNode import GrammarNode
from ChordSequenceComparison import ChordSequenceComparison
from GettingOfChordSequenceDurationInSeconds import GettingOfChordSequenceDurationInSeconds

class GenerateMusic:
    def __init__(self):
        self.__midiFormat = '.mid'
        # конец имени промежуточного файла - конвертированного исходного в формат 0
        self.__format0FilenameEnd = '_format_0' + self.__midiFormat
        self.__popupBackgroundColor = '#1a263c'
        self.__icon_name = 'app_icon.ico'
        self.__pleaseWaitText = 'Запущен процесс генерации. Ожидайте завершения процесса...\n' \
                         '                            Время начала = '
        # значения по умолчанию:
        self.__defaultMinNearChordIndex = -10  # мин. индекс соседнего аккорда, если нужно взять случайный ближайший
        self.__defaultMaxNearChordIndex = 10  # макс. индекс соседнего аккорда, если нужно взять случайный ближайший
        self.__defaultEndRuleProbability = 0.6     # вероятность вернуть продукцию конечного правила
                                            # вместо случайной продукции случайного узла ветви дерева,
                                            # которая идет от корня до конечного правила
        self.__defaultLimitNotesCheckbox = False       # ограничить количество нот во входном файле
                                                # (помогает при зависании программы на объёмных файлах)
        self.__defaultLimitNotes = 500  # ограничение количества нот во входном файле, если отмечен checkbox
        self.__defaultEnableGenerateLooping = False # флаг включение зацикливания генерации нового файла
                                            # (если достигнут конец входного файла, продолжить
                                            # достраивать последовательность с первого аккорда входного файла)
        self.__defaultIgnoreNoteOff = False    # игнорировать события выкл. ноты, может улучшить генерацию
                                        # мелодий с инструментами, не зависящими от note_off (например, пианино)
        # текущие значения:
        # мин. индекс соседнего аккорда, если нужно взять случайный ближайший
        self.__currentMinNearChordIndex = self.__defaultMinNearChordIndex
        # макс. индекс соседнего аккорда, если нужно взять случайный ближайший
        self.__currentMaxNearChordIndex = self.__defaultMaxNearChordIndex
        self.__currentEndRuleProbability = self.__defaultEndRuleProbability # вероятность вернуть продукцию конечного правила
                                                                        # вместо случайной продукции случайного узла
                                                                        # ветви дерева, которая идет от корня до конечного
                                                                        # правила
        self.__currentLimitNotesCheckbox = self.__defaultLimitNotesCheckbox     # ограничить количество нот во входном файле
                                                                            # (помогает при зависании программы
                                                                            # на объёмных файлах)
        self.__currentLimitNotes = self.__defaultLimitNotes     # ограничение количества нот во входном файле,
                                                            # если отмечен checkbox
        # флаг включение зацикливания генерации нового файла
        self.__currentEnableGenerateLooping = self.__defaultEnableGenerateLooping
                                                    # (если достигнут конец входного файла, продолжить
                                                    # достраивать последовательность с первого аккорда входного файла)
        self.__currentIgnoreNoteOff = self.__defaultIgnoreNoteOff   # игнорировать события выкл. ноты, может улучшить генерацию
                                                                # мелодий с инструментами, не зависящими от note_off
                                                                #  (например, пианино)
        ###
        self.__midiList = []  # Список исходных MIDI-файлов для генерации
        self.__midiFilesType0Paths = []  # Список MIDI-файлов формата 0
        self.__startTime = None
        ###
        # интерфейс
        self.__layout = [[sg.Text('Исходные MIDI-файлы:'), sg.Push(),
                   sg.Column([[sg.FileBrowse('Добавить', key='InputFile',
                                             enable_events=True, file_types=(('MIDI files', '*.mid'),))]]),
                   sg.Button('Удалить', key='DeleteFile'), sg.Button('Очистить', key='ClearFiles')],
                  [sg.Listbox(self.__midiList, size=(73, 10), enable_events=True, key='MidiListView')],
                  [sg.Text('Имя генерируемого файла: '), sg.InputText(key='NewFilePath', disabled=True,
                                                                      disabled_readonly_background_color='#b7b7b7',
                                                                      size=(34, 1)),
                   sg.FileSaveAs('Сохранить как', key='SaveAsButton', file_types=(('MIDI files', '*.mid'),))],
                  [sg.Text('Длительность нового трека:'),
                   sg.InputText(key='Duration', disabled_readonly_background_color='#b7b7b7',
                                size=(34, 1), enable_events=True)],
                  [sg.Checkbox('Открыть результат после генерации', key='OpenAfterGeneration', default=True)],
                  [sg.Button('Доп. настройки', key='SettingsButton')],
                  [sg.Push(), sg.Text(self.__pleaseWaitText, font='Helvetica 13', visible=False, key='pleaseWait'), sg.Push()],
                  [sg.Push(), sg.Submit('Генерировать', key='Generate'),
                   sg.Cancel('Отменить и выйти', key='Cancel'), sg.Push()]
                  ]
        self.__window = sg.Window('Генерация музыки', self.__layout, icon=self.__icon_name)  # Окно программы

    def __convertType1ToType0(self, midiType1FilePath):  # Конвертация MIDI из формата 1 в формат 0 (объединить все треки)
        midiType1 = mido.MidiFile(midiType1FilePath)  # считать файл в переменную
        midiType0Tracks = mido.merge_tracks(midiType1.tracks)  # объединить все треки в файле в один
        midiType0 = mido.MidiFile(type=0, ticks_per_beat=midiType1.ticks_per_beat)
        midiType0.tracks.append(midiType0Tracks)
        filename = midiType1FilePath.removesuffix(self.__midiFormat) + self.__format0FilenameEnd
        midiType0.save(filename)  # сохранить файл
        return filename

    # Генерация нового MIDI-файла (в отдельном потоке)
    def __midiGenerate(self, midiType0FilesPaths, newFileNamePath, newDurationSeconds, minNearChordIndex, maxNearChordIndex,
                     endRuleProbability, limitNotesCheckbox, limitNotes, enableGenerateLooping, ignoreNoteOff, window):
        inputMidis = []
        for path in midiType0FilesPaths:
            inputMidis.append(mido.MidiFile(path))  # прочитать все входные MIDI-файлы в список
        # построить КЗ-грамматику
        grammar, newTicksPerBeat, listOfChordLists = self.__buildGrammar(inputMidis,
                                                                  limitNotesCheckbox, limitNotes, ignoreNoteOff)
        # начальная последовательность состоит из первых аккордов входных файлов
        # создать новую последовательность аккордов
        generatedChordSequence = self.__produceNewMidi([chordList[0] for chordList in listOfChordLists],
                                                grammar, newDurationSeconds, newTicksPerBeat, listOfChordLists,
                                                minNearChordIndex, maxNearChordIndex, endRuleProbability,
                                                enableGenerateLooping)
        outputMidi = mido.MidiFile(type=0, ticks_per_beat=newTicksPerBeat)
        outputTrack = mido.MidiTrack()
        outputMidi.tracks.append(outputTrack)
        # перенести сообщения из последовательности аккордов в трек генерируемого MIDI-файла
        self.__moveMsgsFromChordsToTrack(generatedChordSequence, outputTrack)
        # убрать лишние аккорды, пока длительность не станет меньше или равна требуемой
        while outputMidi.length > newDurationSeconds:
            outputTrack.pop()
        outputMidi.save(newFileNamePath)  # сохранить файл
        window.write_event_value(('threadMidiGenerate', 'Complete'),
                                 'Success')  # сообщение в очередь GUI о конце работы потока

    # Построение контекстно-зависимой грамматики по MIDI-файлам (формата 0)
    def __buildGrammar(self, midis, limitNotesCheckbox, limitNotes, ignoreNoteOff):
        ### импорт статических методов в качестве функций
        appendUniqueChord = UniqueChordAdding.appendUniqueChord
        chordsAreEqual = ChordComparison.chordsAreEqual
        ###
        roots = []  # грамматика - возвращаемое значение
        newTicksPerBeat = statistics.mean([midi.ticks_per_beat for midi in midis])  # такт = среднеарифм. среди MIDI
        listOfChordLists = []  # список аккордов всех входных MIDI-файлов (для каждого файла свой список)
        for midi in midis:
            messages = [ExtendendMessage(m) for m in midi.tracks[0] if (m.is_meta == False)
                        or (        # все сообщения трека (кроме мета-, но с изменением темпа)
                                    m.is_meta == True and m.type == 'set_tempo')]
            if limitNotesCheckbox:
                messages = messages[:limitNotes + 1]
            absoluteTime = 0
            i = 0
            for m in messages:
                absoluteTime = absoluteTime + m.msg.time
                m.absolute = absoluteTime  # получить абсолютное время для сообщения
                # найти сообщение начала звучания ноты и записать для неё длительность
                if m.msg.type == 'note_off' and not ignoreNoteOff:
                    messagesBeforeThisMsg = list(reversed(messages[:i]))
                    for msgBefore in messagesBeforeThisMsg:
                        if msgBefore.msg.type == 'note_on' and msgBefore.msg.channel == m.msg.channel \
                                and msgBefore.msg.note == m.msg.note and msgBefore.duration == 0:
                            msgBefore.duration = m.absolute - msgBefore.absolute  # записать длительность звучания ноты
                            break
                i = i + 1
            # убрать сообщения выключения ноты, так как инфо о длительности звучания хранится у сообщ-ий включения ноты
            messages = [m for m in messages if m.msg.type != 'note_off']
            # сгруппировать сообщения по абсолютному времени в словарь (ключ - абсолютное время)
            msgGroups = {}
            for absol, msgs in groupby(messages, lambda m: m.absolute):
                msgGroups[absol] = list(msgs)
            del messages
            chords = []  # список аккордов для данного MIDI-файла
            flagFirstChordIsInList = False  # флаг о том, что первый аккорд добавлен в список
            previousChordAbsolute = 0  # абсолютное время предыдущего аккорда
            for msgGroupKey, msgGroupValue in msgGroups.items():  # получить список аккордов (групп одновременных сообщений)
                chord = Chord()
                chord.msgs.extend(msgGroupValue)  # записать в аккорд список одновременных сообщений из группы
                if flagFirstChordIsInList == False:  # для первого аккорда
                    chord.delay = msgGroupKey
                    flagFirstChordIsInList = True
                else:
                    chord.delay = msgGroupKey - previousChordAbsolute  # задержка = разница между абсолютным временем аккордов
                chords.append(chord)
                previousChordAbsolute = msgGroupKey
            listOfChordLists.append(chords)  # добавить в список аккордов всех входных MIDI-файлов
            uniqueChords = []  # список уникальных аккордов
            for chord in chords:  # получить список уникальных аккордов (без учёта абсолютного времени сообщений)
                appendUniqueChord(chord, uniqueChords)  # добавить аккорд в список уникальных, если его там ещё нет
            for uniqueChord in uniqueChords:  # построить грамматику
                flagThisChordIsInRootsAlready = False
                root = None
                for r in roots:
                    if len(r.value) > 0:
                        if chordsAreEqual(r.value[0],
                                          uniqueChord):  # если такой корень-аккорд уже есть (из другого MIDI-файла)
                            root = r
                            flagThisChordIsInRootsAlready = True
                            break
                if flagThisChordIsInRootsAlready == False:  # новое дерево, корнем служит уникальный аккорд
                    root = GrammarNode()
                    roots.append(root)
                    root.value.append(uniqueChord)
                self.__buildGrammarNode(root, chords)  # построить правила грамматики
        return roots, newTicksPerBeat, listOfChordLists

    def __getPreviousChords(self, chordSequence, allChords):  # возможные аккорды перед данной последовательностью аккордов
        ### импорт статических методов в качестве функций
        chordSequencesAreEqual = ChordSequenceComparison.chordSequencesAreEqual
        appendUniqueChord = UniqueChordAdding.appendUniqueChord
        ###
        previousChords = []
        for chord in allChords[:len(allChords) - len(chordSequence)]:
            if chordSequencesAreEqual(chordSequence, allChords[
                                      allChords.index(chord) + 1:allChords.index(chord) + 1 + len(chordSequence)]):
                appendUniqueChord(chord, previousChords)  # доб. аккорд в список, если его там ещё нет
        return previousChords

    def __getFollowingChords(self, chordSequence, allChords):  # возможные аккорды после данной последовательности аккордов
        ### импорт статических методов в качестве функций
        chordSequencesAreEqual = ChordSequenceComparison.chordSequencesAreEqual
        appendUniqueChord = UniqueChordAdding.appendUniqueChord
        ###
        followingChords = []
        for chord in allChords:
            indexOfFollowingChord = allChords.index(chord) + len(chordSequence)
            if indexOfFollowingChord >= len(allChords):
                break
            if chordSequencesAreEqual(chordSequence, allChords[allChords.index(chord):indexOfFollowingChord]):
                # доб. аккорд в список, если его там ещё нет
                appendUniqueChord(allChords[indexOfFollowingChord], followingChords)
        return followingChords

    def __buildGrammarNode(self, root,
                         chords):  # Построить правила для КЗ-грамматики для аккордов данной последовательности (root)
        chordSequencesAreEqual = ChordSequenceComparison.chordSequencesAreEqual  # импорт статического метода в качестве функции
        # получить список, показывающий, какой аккорд может быть после данной последовательности
        followingChords = self.__getFollowingChords(root.value, chords)
        if len(followingChords) == 0:  # достигнут конец списка всех аккордов, все правила построены
            return
        if len(followingChords) > 1:  # несколько возможных вариантов аккордов (продукции) после данной последовательности
            # получить список, показывающий, какой аккорд может быть перед данной последовательностью
            previousChords = self.__getPreviousChords(root.value, chords)
            newNodes = []  # новые узлы
            for previousChord in previousChords:    # создать новые узлы со значением = предшествующая
                                                    # + текущая последовательность
                newSequence = []
                newSequence.append(previousChord)  # расширение контекста на 1 аккорд
                newSequence.extend(root.value)
                newFollowingChords = self.__getFollowingChords(newSequence,
                                                        chords)  # получить продукции для новой последовательности
                # найти, есть ли уже узел с такой последовательностью (newSequence) далее в дереве
                nodesWithThisSequenceValue = [node for node in root.nextNodes.values() if node != None and
                                              chordSequencesAreEqual(node.value, newSequence)]
                if len(nodesWithThisSequenceValue) == 0:  # если узла с такой последовательностью ещё нет, создать
                    nodeWithSequence = GrammarNode()
                    nodeWithSequence.value = newSequence
                else:  # если узел с такой последовательностью уже есть, выбрать его
                    nodeWithSequence = nodesWithThisSequenceValue[0]
                for newFollowingChord in newFollowingChords:  # добавить только новые продукции
                    if newFollowingChord not in root.nextNodes.keys():
                        root.nextNodes[newFollowingChord] = nodeWithSequence
                        newNodes.append(nodeWithSequence)
            for node in list(set(newNodes)):  # продолжить строить правила для каждого нового узла
                self.__buildGrammarNode(node, chords)
        else:   # только один возможный вариант аккорда после последовательности,
                # добавить его в словарь продукции, если его ещё нет
            if followingChords[0] not in root.nextNodes.keys():
                # следующий узел пуст, так как при единственной продукции расширение контекста не требуется
                root.nextNodes[followingChords[0]] = None

    # создать новую последовательность аккордов из MIDI-сообщений
    def __produceNewMidi(self, initialChordSequence, grammar, durationSeconds, ticksPerBeat, listOfChordLists,
                       minNearChordIndex, maxNearChordIndex, endRuleProbability, enableGenerateLooping):
        ### импорт статических методов в качестве функций
        getChordSequenceDurationInSeconds = GettingOfChordSequenceDurationInSeconds.getChordSequenceDurationInSeconds
        chordsAreEqual = ChordComparison.chordsAreEqual
        ###
        resultedGeneratedChordSequence = []
        generatedChordSequence = initialChordSequence  # текущая последовательность равна начальной
        # пока длительность меньше заданной, добавлять продуцированные сообщения
        indexMidiFile = 0
        while getChordSequenceDurationInSeconds(resultedGeneratedChordSequence + generatedChordSequence,
                                                ticksPerBeat) <= durationSeconds:
            lastChord = generatedChordSequence[-1]
            # если достигнут последний аккорд файла, перейти к первому аккорду следующего файла
            if lastChord == listOfChordLists[indexMidiFile][-1] and enableGenerateLooping:
                indexMidiFile = indexMidiFile + 1
                # если достигнут последний аккорд последнего файла, перейти к первому аккорду первого файла
                if indexMidiFile >= len(listOfChordLists):
                    indexMidiFile = 0
                lastChord = listOfChordLists[indexMidiFile][0]
                resultedGeneratedChordSequence.extend(generatedChordSequence)
                generatedChordSequence = [lastChord]
            # найти дерево грамматики для последнего аккорда в последовательности
            grammarRules = [node for node in grammar if chordsAreEqual(node.value[0], lastChord)]
            rule = grammarRules[0]
            # добавить к текущей последовательности сгенерированный аккорд
            generatedChordSequence.append(rule.generateNextChord(generatedChordSequence, listOfChordLists,
                                                                 minNearChordIndex, maxNearChordIndex,
                                                                 endRuleProbability))
        resultedGeneratedChordSequence.extend(generatedChordSequence)
        return resultedGeneratedChordSequence

    # перенести сообщения из последовательности аккордов в трек
    def __moveMsgsFromChordsToTrack(self, chordSequence, midiTrack):
        absoluteTime = 0  # время с начала трека
        trackWithExtendedMsgs = []  # список сообщений для трека (объекты класса ExtendedMessage, с абсолютным временем)
        for chord in chordSequence:  # перебрать все аккорды
            absoluteTime = absoluteTime + chord.delay  # увеличить абс. время на задержку перед данным аккордом
            for msg in chord.msgs:  # перебрать сообщения в аккорде
                AddingMsg = copy.copy(msg)  # скопировать сообщение
                msg.absolute = absoluteTime
                trackWithExtendedMsgs.append(AddingMsg)  # добавить сообщение в список
                if AddingMsg.msg.type == 'note_on' and AddingMsg.duration != 0:  # если данное сообщение - включение ноты
                    msgNoteOff = mido.Message('note_off', channel=AddingMsg.msg.channel,
                                              note=AddingMsg.msg.note, velocity=0, time=0)
                    # доб. сообщение выключения ноты в список, абс.время = абс. время вкл. ноты + её длительность
                    trackWithExtendedMsgs.append(
                        ExtendendMessage(msg=msgNoteOff, absolute=absoluteTime + AddingMsg.duration))
        # отсортировать сообщения по возрастанию абсолютного времени
        # (требуется, так как сообщения note_off расположены сразу после note_on)
        trackWithExtendedMsgs.sort(key=lambda msg: msg.absolute)
        # перенести сообщения из trackWithExtendedMsgs в итоговый трек с относительным временем вместо абсолютного
        i = 0
        for extendedMsg in trackWithExtendedMsgs:
            newMsg = copy.copy(extendedMsg.msg)
            if (i == 0):
                newMsg.time = extendedMsg.absolute
            else:
                newMsg.time = extendedMsg.absolute - trackWithExtendedMsgs[i - 1].absolute
            midiTrack.append(newMsg)
            i = i + 1

    # изменить состояние элементов интерфейса: недоступны (True) или доступны (False)
    def __updateWindowElementsDisabled(self, state):
        self.__window['InputFile'].update(disabled=state)
        self.__window['DeleteFile'].update(disabled=state)
        self.__window['ClearFiles'].update(disabled=state)
        self.__window['MidiListView'].update(disabled=state)
        self.__window['SaveAsButton'].update(disabled=state)
        self.__window['SettingsButton'].update(disabled=state)
        self.__window['Duration'].update(disabled=state)
        self.__window['Generate'].update(disabled=state)

    def eventLoop(self):
        while True:  # The Event Loop
            event, values = self.__window.read()
            if event in (None, 'Exit', 'Cancel'):  # Выход из программы
                for midi0 in self.__midiFilesType0Paths:  # Удалить промежуточные файлы
                    if os.path.isfile(midi0):  # защита от попытки удаления несуществующего файла
                        os.remove(midi0)
                break
            if event == 'InputFile':  # Добавить MIDI-файл в список исходных файлов для генерации
                self.__midiList.append(values['InputFile'])
                self.__window['MidiListView'].update(self.__midiList)
            if event == 'DeleteFile' and values['MidiListView']:  # Удалить файл из списка исходных файлов для генерации
                self.__midiList.remove(values['MidiListView'][0])
                self.__window['MidiListView'].update(self.__midiList)
            if event == 'ClearFiles':  # Очистить список исходных файлов для генерации
                self.__midiList.clear()
                self.__window['MidiListView'].update(self.__midiList)
            if event == 'Duration':
                colonCount = 0
                str = values['Duration']
                for character in str:  # Защита ввода продолжительности, только цифры и одно ":"
                    if character not in ('0123456789:'):
                        str = str.replace(character, '')
                        self.__window['Duration'].update(str)
                    if character == ':':
                        colonCount = colonCount + 1
                        if colonCount > 1:
                            str = ''.join(str.rsplit(':', 1))
                            self.__window['Duration'].update(str)
                            colonCount = colonCount - 1
            if event == 'Generate' and self.__midiList and values['NewFilePath'] \
                    and values['Duration'] and values['Duration'][0] != ':':  # Генерация файла
                self.__startTime = datetime.now()
                self.__midiFilesType0Paths = []
                for midiElement in self.__midiList:
                    self.__midiFilesType0Paths.append(self.__convertType1ToType0(midiElement))
                partitionOfDuration = values['Duration'].partition(':')
                if (partitionOfDuration[1] == ''):  # Получить продолжительность нового трека в секундах
                    duration = int(partitionOfDuration[0])
                else:
                    duration = int(partitionOfDuration[0]) * 60 + int(partitionOfDuration[2])
                self.__updateWindowElementsDisabled(True)  # сделать элементы интерфейса неактивными
                self.__window['pleaseWait'].update(self.__pleaseWaitText + self.__startTime.strftime("%H:%M:%S"))
                self.__window['pleaseWait'].update(visible=True)
                # запуск генерации в отдельном потоке, чтобы избежать состояния "программа не отвечает"
                self.__window.start_thread(lambda: self.__midiGenerate(self.__midiFilesType0Paths, values['NewFilePath'],
                                                         duration, self.__currentMinNearChordIndex,
                                                         self.__currentMaxNearChordIndex, self.__currentEndRuleProbability,
                                                         self.__currentLimitNotesCheckbox, self.__currentLimitNotes,
                                                         self.__currentEnableGenerateLooping, self.__currentIgnoreNoteOff,
                                                         self.__window),
                                    ('threadMidiGenerate', 'threadMidiGenerateEnded'))
            if event[0] == 'threadMidiGenerate':
                if event[1] == 'Complete':
                    for midi0 in self.__midiFilesType0Paths:  # Удалить промежуточные файлы
                        if os.path.isfile(midi0):  # защита от попытки удаления несуществующего файла
                            os.remove(midi0)
                    self.__window['pleaseWait'].update(visible=False)
                    self.__updateWindowElementsDisabled(False)  # сделать элементы интерфейса активными
                    endTime = datetime.now()
                    deltaTime = endTime - self.__startTime
                    sg.popup('         Успешно сгенерировано\n\nВремя начала = ' + self.__startTime.strftime("%H:%M:%S") +
                             '\nВремя завершения = ' + endTime.strftime("%H:%M:%S") +
                             '\nБыло потрачено времени = ' + time.strftime("%H:%M:%S",
                                                                           time.gmtime(deltaTime.total_seconds())),
                             keep_on_top=True, no_titlebar=True, background_color=self.__popupBackgroundColor,
                             any_key_closes=True, grab_anywhere=True, button_justification='centered')
                    if values['OpenAfterGeneration'] == True:  # Открыть созданный файл, если отмечен checkbox
                        os.system('"' + values['NewFilePath'] + '"')
            if event == 'Generate' and not self.__midiList:
                sg.popup('Список исходных MIDI-файлов пуст, проверьте входные данные',
                         keep_on_top=True, no_titlebar=True, background_color=self.__popupBackgroundColor,
                         any_key_closes=True, grab_anywhere=True, button_justification='centered')
            if event == 'Generate' and not values['NewFilePath']:
                sg.popup('Не указан путь сохранения файла, проверьте входные данные',
                         keep_on_top=True, no_titlebar=True, background_color=self.__popupBackgroundColor,
                         any_key_closes=True, grab_anywhere=True, button_justification='centered')
            if event == 'Generate' and (not values['Duration'] or values['Duration'][0] == ':' or
                                        values['Duration'][len(values['Duration']) - 1] == ':'):
                sg.popup('Не указана продолжительность нового трека, проверьте входные данные',
                         keep_on_top=True, no_titlebar=True, background_color=self.__popupBackgroundColor,
                         any_key_closes=True, grab_anywhere=True, button_justification='centered')
            if event == 'SettingsButton':  # открыть окно доп. настроек
                layoutSettingsWindow = [[sg.Text('Мин. индекс случайного соседнего аккорда: '), sg.Push(),
                                         sg.InputText(key='MinIndex', default_text=self.__currentMinNearChordIndex,
                                                      enable_events=True,
                                                      size=(14, 1))],
                                        [sg.Text('Макс. индекс случайного соседнего аккорда: '), sg.Push(),
                                         sg.InputText(key='MaxIndex', default_text=self.__currentMaxNearChordIndex,
                                                      enable_events=True,
                                                      size=(14, 1))],
                                        [sg.Text('Вероятность конечной продукции вместо промежуточной: '), sg.Push(),
                                         sg.InputText(key='Probability', default_text=self.__currentEndRuleProbability,
                                                      enable_events=True,
                                                      size=(14, 1))],
                                        [sg.Frame('', size=(500, 63), layout=
                                        [[sg.Checkbox('Ограничить кол-во нот во входном файле', enable_events=True,
                                                      key='LimitNotesCheckbox', default=self.__currentLimitNotesCheckbox)],
                                         [sg.Text('Кол-во нот во входном файле: '), sg.Push(),
                                          sg.InputText(key='LimitNotes', disabled_readonly_background_color='#b7b7b7',
                                                       default_text=self.__currentLimitNotes,
                                                       disabled=not self.__currentLimitNotesCheckbox,
                                                       enable_events=True, size=(13, 1))]])],
                                        [sg.Checkbox('Зациклить процесс генерации при достижении конца входных файлов',
                                                     key='GenerateLooping', default=self.__currentEnableGenerateLooping)],
                                        [sg.Checkbox('Не учитывать события note_off (выкл. ноты)',
                                                     key='IgnoreNoteOff', default=self.__currentIgnoreNoteOff)],
                                        [sg.Push(), sg.Button('Восст. по умолчанию', key='restoreByDefault')],
                                        [sg.Push(), sg.OK(key='OkSettings', size=(7, 1)), sg.Push()]]
                settingsWindow = sg.Window('Доп. настройки генерации', layoutSettingsWindow, icon=self.__icon_name,
                                           disable_minimize=True, modal=True)
                while True:
                    event, values = settingsWindow.read()
                    if event == sg.WIN_CLOSED or event == 'Exit':
                        break
                    if event == 'OkSettings':  # сохранить настройки генерации
                        if values['MinIndex'] != '' and values['MaxIndex'] != '' and int(values['MinIndex']) > int(
                                values['MaxIndex']):
                            sg.popup('Мин. значение индекса не может быть больше максимального',
                                     keep_on_top=True, no_titlebar=True, background_color=self.__popupBackgroundColor,
                                     any_key_closes=True, grab_anywhere=True, button_justification='centered')
                            continue
                        if values['Probability'] != '' and float(values['Probability']) > 1:
                            sg.popup('Вероятность не может быть больше 1',
                                     keep_on_top=True, no_titlebar=True, background_color=self.__popupBackgroundColor,
                                     any_key_closes=True, grab_anywhere=True, button_justification='centered')
                            continue
                        if values['MinIndex'] == '':
                            self.__currentMinNearChordIndex = self.__defaultMinNearChordIndex
                        else:
                            self.__currentMinNearChordIndex = int(values['MinIndex'])
                        if values['MaxIndex'] == '':
                            self.__currentMaxNearChordIndex = self.__defaultMaxNearChordIndex
                        else:
                            self.__currentMaxNearChordIndex = int(values['MaxIndex'])
                        if values['Probability'] == '':
                            self.__currentEndRuleProbability = self.__defaultEndRuleProbability
                        else:
                            self.__currentEndRuleProbability = float(values['Probability'])
                        self.__currentLimitNotesCheckbox = values['LimitNotesCheckbox']
                        if values['LimitNotes'] == '':
                            self.__currentLimitNotes = self.__defaultLimitNotes
                        else:
                            self.__currentLimitNotes = int(values['LimitNotes'])
                        self.__currentEnableGenerateLooping = values['GenerateLooping']
                        self.__currentIgnoreNoteOff = values['IgnoreNoteOff']
                        break
                    if event == 'restoreByDefault':  # восстановить значения по умолчанию
                        self.__currentMinNearChordIndex = self.__defaultMinNearChordIndex
                        self.__currentMaxNearChordIndex = self.__defaultMaxNearChordIndex
                        self.__currentEndRuleProbability = self.__defaultEndRuleProbability
                        settingsWindow['MinIndex'].update(self.__currentMinNearChordIndex)
                        settingsWindow['MaxIndex'].update(self.__currentMaxNearChordIndex)
                        settingsWindow['Probability'].update(self.__currentEndRuleProbability)
                        settingsWindow['LimitNotesCheckbox'].update(self.__defaultLimitNotesCheckbox)
                        settingsWindow['LimitNotes'].update(self.__defaultLimitNotes)
                        settingsWindow['GenerateLooping'].update(self.__defaultEnableGenerateLooping)
                        settingsWindow['IgnoreNoteOff'].update(self.__defaultIgnoreNoteOff)
                        settingsWindow['LimitNotes'].update(disabled=True)
                    if event == 'MinIndex':
                        str = values['MinIndex']
                        i = 0
                        for character in str:  # Защита ввода продолжительности, только цифры и "-"
                            if i == 0 and character == '-':
                                i = i + 1
                                continue
                            if character not in ('0123456789'):
                                str = str[:i] + str[i + 1:]
                                settingsWindow['MinIndex'].update(str)
                                i = -1
                            i = i + 1
                    if event == 'MaxIndex':
                        str = values['MaxIndex']
                        i = 0
                        for character in str:  # Защита ввода продолжительности, только цифры и "-"
                            if i == 0 and character == '-':
                                i = i + 1
                                continue
                            if character not in ('0123456789'):
                                str = str[:i] + str[i + 1:]
                                settingsWindow['MaxIndex'].update(str)
                                i = -1
                            i = i + 1
                    if event == 'Probability':
                        dotCount = 0
                        str = values['Probability']
                        for character in str:  # Защита ввода продолжительности, только цифры и одна "."
                            if character not in ('0123456789.'):
                                str = str.replace(character, '')
                                settingsWindow['Probability'].update(str)
                            if character == '.':
                                dotCount = dotCount + 1
                                if dotCount > 1:
                                    str = ''.join(str.rsplit('.', 1))
                                    settingsWindow['Probability'].update(str)
                                    dotCount = dotCount - 1
                            if character == '.' and str.index(character) == 0:
                                str = ''.join(str.rsplit('.', 1))
                                settingsWindow['Probability'].update(str)
                                dotCount = dotCount - 1
                    if event == 'LimitNotesCheckbox':
                        settingsWindow['LimitNotes'].update(disabled=not values['LimitNotesCheckbox'])
                    if event == 'LimitNotes':
                        str = values['LimitNotes']
                        i = 0
                        for character in str:  # Защита ввода продолжительности, только цифры
                            if character not in ('0123456789') or (i == 0 and character == '0'):
                                str = str[:i] + str[i + 1:]
                                settingsWindow['LimitNotes'].update(str)
                                i = -1
                            i = i + 1
                settingsWindow.close()

generateTheMusic = GenerateMusic() #создать объект класса GenerateMusic
generateTheMusic.eventLoop() #цикл работы программы с интерфейсом
