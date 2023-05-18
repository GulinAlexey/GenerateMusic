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
from UniqueChordAdding import appendUniqueChord
from ChordComparison import chordsAreEqual
from GrammarNode import GrammarNode
from ChordSequenceComparison import chordSequencesAreEqual
from GettingOfChordSequenceDurationInSeconds import getChordSequenceDurationInSeconds

midiFormat = '.mid'
format0FilenameEnd = '_format_0' + midiFormat #конец имени промежуточного файла - конвертированного исходного в формат 0
popupBackgroundColor = '#1a263c'
icon_name = 'app_icon.ico'
pleaseWaitText = 'Запущен процесс генерации. Ожидайте завершения процесса...\n' \
                 '                            Время начала = '

#значения по умолчанию:
defaultMinNearChordIndex = -10 #мин. индекс соседнего аккорда, если нужно взять случайный ближайший
defaultMaxNearChordIndex = 10 #макс. индекс соседнего аккорда, если нужно взять случайный ближайший
defaultEndRuleProbability = 0.6     #вероятность вернуть продукцию конечного правила
                                    # вместо случайной продукции случайного узла ветви дерева,
                                    # которая идет от корня до конечного правила

def convertType1ToType0(midiType1FilePath): #Конвертация MIDI из формата 1 в формат 0 (объединить все треки)
    midiType1 = mido.MidiFile(midiType1FilePath) #считать файл в переменную
    midiType0Tracks = mido.merge_tracks(midiType1.tracks) #объединить все треки в файле в один
    midiType0 = mido.MidiFile(type = 0, ticks_per_beat=midiType1.ticks_per_beat)
    midiType0.tracks.append(midiType0Tracks)
    filename = midiType1FilePath.removesuffix(midiFormat) + format0FilenameEnd
    midiType0.save(filename) #сохранить файл
    return filename

#Генерация нового MIDI-файла (в отдельном потоке)
def midiGenerate(midiType0FilesPaths, newFileNamePath, newDurationSeconds, minNearChordIndex, maxNearChordIndex,
                 endRuleProbability, window):
    inputMidis = []
    for path in midiType0FilesPaths:
        inputMidis.append(mido.MidiFile(path)) #прочитать все входные MIDI-файлы в список
    grammar, newTicksPerBeat, listOfChordLists = buildGrammar(inputMidis) #построить КЗ-грамматику
    # начальная последовательность состоит из первых аккордов входных файлов
    #создать новую последовательность аккордов
    generatedChordSequence = produceNewMidi([chordList[0] for chordList in listOfChordLists],
                                            grammar, newDurationSeconds, newTicksPerBeat, listOfChordLists,
                                            minNearChordIndex, maxNearChordIndex, endRuleProbability)
    outputMidi = mido.MidiFile(type = 0, ticks_per_beat=newTicksPerBeat)
    outputTrack = mido.MidiTrack()
    outputMidi.tracks.append(outputTrack)
    # перенести сообщения из последовательности аккордов в трек генерируемого MIDI-файла
    moveMsgsFromChordsToTrack(generatedChordSequence, outputTrack)
    # убрать лишние аккорды, пока длительность не станет меньше или равна требуемой
    while outputMidi.length > newDurationSeconds:
        outputTrack.pop()
    outputMidi.save(newFileNamePath) #сохранить файл
    window.write_event_value(('threadMidiGenerate', 'Complete'), 'Success') #сообщение в очередь GUI о конце работы потока

def buildGrammar(midis): #Построение контекстно-зависимой грамматики по MIDI-файлам (формата 0)
    roots = [] #грамматика - возвращаемое значение
    newTicksPerBeat = statistics.mean([midi.ticks_per_beat for midi in midis]) #такт = среднеарифм. среди MIDI
    listOfChordLists = [] #список аккордов всех входных MIDI-файлов (для каждого файла свой список)
    for midi in midis:
        messages = [ExtendendMessage(m) for m in midi.tracks[0] if (m.is_meta == False)
                    or (m.is_meta == True and m.type=='set_tempo')] #все сообщения трека (кроме мета-, но с изменением темпа)
        absoluteTime=0
        i = 0
        for m in messages:
            absoluteTime = absoluteTime + m.msg.time
            m.absolute = absoluteTime #получить абсолютное время для сообщения
            if m.msg.type == 'note_off': #найти сообщение начала звучания ноты и записать для неё длительность
                messagesBeforeThisMsg = list(reversed(messages[:i]))
                for msgBefore in messagesBeforeThisMsg:
                    if msgBefore.msg.type == 'note_on' and msgBefore.msg.channel == m.msg.channel \
                            and msgBefore.msg.note == m.msg.note and msgBefore.duration==0:
                        msgBefore.duration = m.absolute - msgBefore.absolute    #записать длительность звучания ноты
                        break
            i = i + 1
        # убрать сообщения выключения ноты, так как инфо о длительности звучания хранится у сообщ-ий включения ноты
        messages = [m for m in messages if m.msg.type!='note_off']
        # сгруппировать сообщения по абсолютному времени в словарь (ключ - абсолютное время)
        msgGroups = {}
        for abs, msgs in groupby(messages, lambda m: m.absolute):
            msgGroups[abs] = list(msgs)
        del messages
        chords = [] #список аккордов для данного MIDI-файла
        flagFirstChordIsInList = False #флаг о том, что первый аккорд добавлен в список
        previousChordAbsolute = 0 #абсолютное время предыдущего аккорда
        for msgGroupKey, msgGroupValue in msgGroups.items(): #получить список аккордов (групп одновременных сообщений)
            chord = Chord()
            chord.msgs.extend(msgGroupValue) #записать в аккорд список одновременных сообщений из группы
            if flagFirstChordIsInList == False: #для первого аккорда
                chord.delay = msgGroupKey
                flagFirstChordIsInList = True
            else:
                chord.delay = msgGroupKey - previousChordAbsolute #задержка = разница между абсолютным временем аккордов
            chords.append(chord)
            previousChordAbsolute = msgGroupKey
        listOfChordLists.append(chords) #добавить в список аккордов всех входных MIDI-файлов
        uniqueChords = []  # список уникальных аккордов
        for chord in chords: #получить список уникальных аккордов (без учёта абсолютного времени сообщений)
            appendUniqueChord(chord, uniqueChords) #добавить аккорд в список уникальных, если его там ещё нет
        for uniqueChord in uniqueChords: #построить грамматику
            flagThisChordIsInRootsAlready = False
            root = None
            for r in roots:
                if len(r.value)>0:
                    if chordsAreEqual(r.value[0], uniqueChord): #если такой корень-аккорд уже есть (из другого MIDI-файла)
                        root = r
                        flagThisChordIsInRootsAlready = True
                        break
            if flagThisChordIsInRootsAlready == False: #новое дерево, корнем служит уникальный аккорд
                root = GrammarNode()
                roots.append(root)
                root.value.append(uniqueChord)
            buildGrammarNode(root, chords) #построить правила грамматики
    return roots, newTicksPerBeat, listOfChordLists

def getPreviousChords(chordSequence, allChords): #возможные аккорды перед данной последовательностью аккордов
    previousChords = []
    for chord in allChords[:len(allChords)-len(chordSequence)]:
        if chordSequencesAreEqual(chordSequence,
                allChords[allChords.index(chord)+1:allChords.index(chord)+1+len(chordSequence)]):
            appendUniqueChord(chord, previousChords) #доб. аккорд в список, если его там ещё нет
    return previousChords

def getFollowingChords(chordSequence, allChords): #возможные аккорды после данной последовательности аккордов
    followingChords = []
    for chord in allChords:
        indexOfFollowingChord = allChords.index(chord)+len(chordSequence)
        if indexOfFollowingChord >= len(allChords):
            break
        if  chordSequencesAreEqual(chordSequence, allChords[allChords.index(chord):indexOfFollowingChord]):
            # доб. аккорд в список, если его там ещё нет
            appendUniqueChord(allChords[indexOfFollowingChord], followingChords)
    return followingChords

def buildGrammarNode(root, chords): #Построить правила для КЗ-грамматики для аккордов данной последовательности (root)
    #получить список, показывающий, какой аккорд может быть после данной последовательности
    followingChords = getFollowingChords(root.value, chords)
    if len(followingChords) == 0: #достигнут конец списка всех аккордов, все правила построены
        return
    if len(followingChords) > 1: #несколько возможных вариантов аккордов (продукции) после данной последовательности
        # получить список, показывающий, какой аккорд может быть перед данной последовательностью
        previousChords = getPreviousChords(root.value, chords)
        newNodes = [] #новые узлы
        for previousChord in previousChords: #создать новые узлы со значением предшествующ. + текущая последовательность
            newSequence = []
            newSequence.append(previousChord) #расширение контекста на 1 аккорд
            newSequence.extend(root.value)
            newFollowingChords = getFollowingChords(newSequence, chords) #получить продукции для новой последовательности
            #найти, есть ли уже узел с такой последовательностью (newSequence) далее в дереве
            nodesWithThisSequenceValue = [node for node in root.nextNodes.values() if node != None and
                chordSequencesAreEqual(node.value, newSequence)]
            if len(nodesWithThisSequenceValue) == 0: #если узла с такой последовательностью ещё нет, создать
                nodeWithSequence = GrammarNode()
                nodeWithSequence.value = newSequence
            else: #если узел с такой последовательностью уже есть, выбрать его
                nodeWithSequence = nodesWithThisSequenceValue[0]
            for newFollowingChord in newFollowingChords: #добавить только новые продукции
                if newFollowingChord not in root.nextNodes.keys():
                    root.nextNodes[newFollowingChord] = nodeWithSequence
                    newNodes.append(nodeWithSequence)
        for node in list(set(newNodes)): #продолжить строить правила для каждого нового узла
            buildGrammarNode(node, chords)
    else: #только один возможный вариант аккорда после последовательности, добавить его в словарь продукции, если его ещё нет
        if followingChords[0] not in root.nextNodes.keys():
            #следующий узел пуст, так как при единственной продукции расширение контекста не требуется
            root.nextNodes[followingChords[0]] = None

#создать новую последовательность аккордов из MIDI-сообщений
def produceNewMidi(initialChordSequence, grammar, durationSeconds, ticksPerBeat, listOfChordLists,
                   minNearChordIndex, maxNearChordIndex, endRuleProbability):
    generatedChordSequence = initialChordSequence #текущая последовательность равна начальной
    # пока длительность меньше заданной, добавлять продуцированные сообщения
    while getChordSequenceDurationInSeconds(generatedChordSequence, ticksPerBeat) <= durationSeconds:
        lastChord = generatedChordSequence[-1]
        #найти дерево грамматики для последнего аккорда в последовательности
        grammarRules = [node for node in grammar if chordsAreEqual(node.value[0], lastChord)]
        rule = grammarRules[0]
        # добавить к текущей последовательности сгенерированный аккорд
        generatedChordSequence.append(rule.generateNextChord(generatedChordSequence, listOfChordLists,
                                                             minNearChordIndex, maxNearChordIndex, endRuleProbability))
    return generatedChordSequence

# перенести сообщения из последовательности аккордов в трек
def moveMsgsFromChordsToTrack(chordSequence, midiTrack):
    absoluteTime = 0 #время с начала трека
    trackWithExtendedMsgs = [] #список сообщений для трека (объекты класса ExtendedMessage, с абсолютным временем)
    for chord in chordSequence: #перебрать все аккорды
        absoluteTime = absoluteTime + chord.delay #увеличить абс. время на задержку перед данным аккордом
        for msg in chord.msgs: #перебрать сообщения в аккорде
            AddingMsg = copy.copy(msg) #скопировать сообщение
            msg.absolute = absoluteTime
            trackWithExtendedMsgs.append(AddingMsg) #добавить сообщение в список
            if AddingMsg.msg.type == 'note_on' and AddingMsg.duration !=0: #если данное сообщение - включение ноты
                msgNoteOff = mido.Message('note_off', channel=AddingMsg.msg.channel,
                                          note=AddingMsg.msg.note, velocity=0, time=0)
                # доб. сообщение выключения ноты в список, абс.время = абс. время вкл. ноты + её длительность
                trackWithExtendedMsgs.append(ExtendendMessage(msg=msgNoteOff, absolute=absoluteTime+AddingMsg.duration))
    # отсортировать сообщения по возрастанию абсолютного времени
    # (требуется, так как сообщения note_off расположены сразу после note_on)
    trackWithExtendedMsgs.sort(key=lambda msg: msg.absolute)
    #перенести сообщения из trackWithExtendedMsgs в итоговый трек с относительным временем вместо абсолютного
    i = 0
    for extendedMsg in trackWithExtendedMsgs:
        newMsg = copy.copy(extendedMsg.msg)
        if(i==0):
            newMsg.time = extendedMsg.absolute
        else:
            newMsg.time = extendedMsg.absolute - trackWithExtendedMsgs[i-1].absolute
        midiTrack.append(newMsg)
        i = i + 1

midiList = [] #Список исходных MIDI-файлов для генерации
midiFilesType0Paths = [] #Список MIDI-файлов формата 0
startTime = None

#текущие значения:
currentMinNearChordIndex = defaultMinNearChordIndex #мин. индекс соседнего аккорда, если нужно взять случайный ближайший
currentMaxNearChordIndex = defaultMaxNearChordIndex #макс. индекс соседнего аккорда, если нужно взять случайный ближайший
currentEndRuleProbability = defaultEndRuleProbability       #вероятность вернуть продукцию конечного правила
                                                            # вместо случайной продукции случайного узла ветви дерева,
                                                            # которая идет от корня до конечного правила

#интерфейс
layout = [[sg.Text('Исходные MIDI-файлы:'), sg.Push(),
    sg.Column([[sg.FileBrowse('Добавить',key='InputFile',
    enable_events=True, file_types=(('MIDI files', '*.mid'),))]]),
    sg.Button('Удалить', key='DeleteFile'), sg.Button('Очистить', key='ClearFiles')],
    [sg.Listbox(midiList, size=(73,10), enable_events=True,  key='MidiListView')],
    [sg.Text('Имя генерируемого файла: '), sg.InputText(key = 'NewFilePath', disabled=True,
                                                        disabled_readonly_background_color='#b7b7b7', size=(34,1)),
    sg.FileSaveAs('Сохранить как', key='SaveAsButton', file_types=(('MIDI files', '*.mid'),))],
    [sg.Text('Длительность нового трека:'), sg.InputText(key='Duration', disabled_readonly_background_color='#b7b7b7',
                                                         size=(34,1), enable_events=True)],
    [sg.Checkbox('Открыть результат после генерации', key='OpenAfterGeneration', default=True)],
    [sg.Button('Доп. настройки', key='SettingsButton')],
    [sg.Push(), sg.Text(pleaseWaitText, font = 'Helvetica 13', visible = False, key='pleaseWait'), sg.Push()],
    [sg.Push(), sg.Submit('Генерировать', key='Generate'),
    sg.Cancel('Отменить и выйти', key='Cancel'), sg.Push()]
]

window = sg.Window('Генерация музыки', layout, icon=icon_name) #Окно программы

def updateWindowElementsDisabled(state): #изменить состояние элементов интерфейса: недоступны (True) или доступны (False)
    window['InputFile'].update(disabled=state)
    window['DeleteFile'].update(disabled=state)
    window['ClearFiles'].update(disabled=state)
    window['MidiListView'].update(disabled=state)
    window['SaveAsButton'].update(disabled=state)
    window['SettingsButton'].update(disabled=state)
    window['Duration'].update(disabled=state)
    window['Generate'].update(disabled=state)

while True:                             #The Event Loop
    event, values = window.read()
    if event in (None, 'Exit', 'Cancel'): #Выход из программы
        for midi0 in midiFilesType0Paths:  # Удалить промежуточные файлы
            if os.path.isfile(midi0):  # защита от попытки удаления несуществующего файла
                os.remove(midi0)
        break
    if event == 'InputFile': #Добавить MIDI-файл в список исходных файлов для генерации
        midiList.append(values['InputFile'])
        window['MidiListView'].update(midiList)
    if event == 'DeleteFile' and values['MidiListView']: #Удалить файл из списка исходных файлов для генерации
        midiList.remove(values['MidiListView'][0])
        window['MidiListView'].update(midiList)
    if event == 'ClearFiles': #Очистить список исходных файлов для генерации
        midiList.clear()
        window['MidiListView'].update(midiList)
    if event == 'Duration':
        colonCount = 0
        str = values['Duration']
        for character in str: #Защита ввода продолжительности, только цифры и одно ":"
            if character not in ('0123456789:'):
                str = str.replace(character, '')
                window['Duration'].update(str)
            if character == ':':
                colonCount = colonCount + 1
                if colonCount > 1:
                    str = ''.join(str.rsplit(':', 1))
                    window['Duration'].update(str)
                    colonCount = colonCount - 1
    if event == 'Generate' and midiList and values['NewFilePath'] \
            and values['Duration'] and values['Duration'][0]!=':': #Генерация файла
        startTime = datetime.now()
        midiFilesType0Paths = []
        for midiElement in midiList:
            midiFilesType0Paths.append(convertType1ToType0(midiElement))
        partitionOfDuration = values['Duration'].partition(':')
        if(partitionOfDuration[1] == ''): #Получить продолжительность нового трека в секундах
            duration = int(partitionOfDuration[0])
        else:
            duration = int(partitionOfDuration[0]) * 60 + int(partitionOfDuration[2])
        updateWindowElementsDisabled(True) #сделать элементы интерфейса неактивными
        window['pleaseWait'].update(pleaseWaitText + startTime.strftime("%H:%M:%S"))
        window['pleaseWait'].update(visible=True)
        #запуск генерации в отдельном потоке, чтобы избежать состояния "программа не отвечает"
        window.start_thread(lambda: midiGenerate(midiFilesType0Paths, values['NewFilePath'],
            duration, currentMinNearChordIndex, currentMaxNearChordIndex, currentEndRuleProbability, window),
            ('threadMidiGenerate', 'threadMidiGenerateEnded'))
    if event[0] == 'threadMidiGenerate':
        if event[1] == 'Complete':
            for midi0 in midiFilesType0Paths:  # Удалить промежуточные файлы
                if os.path.isfile(midi0):  # защита от попытки удаления несуществующего файла
                    os.remove(midi0)
            window['pleaseWait'].update(visible=False)
            updateWindowElementsDisabled(False)  # сделать элементы интерфейса активными
            endTime = datetime.now()
            deltaTime = endTime - startTime
            sg.popup('         Успешно сгенерировано\n\nВремя начала = ' + startTime.strftime("%H:%M:%S") +
                     '\nВремя завершения = ' + endTime.strftime("%H:%M:%S") +
                     '\nБыло потрачено времени = ' + time.strftime("%H:%M:%S", time.gmtime(deltaTime.total_seconds())),
            keep_on_top=True, no_titlebar=True, background_color=popupBackgroundColor,
                     any_key_closes=True, grab_anywhere=True, button_justification='centered')
            if values['OpenAfterGeneration'] == True:  # Открыть созданный файл, если отмечен checkbox
                os.system('"'+values['NewFilePath']+'"')
    if event == 'Generate' and not midiList:
        sg.popup('Список исходных MIDI-файлов пуст, проверьте входные данные',
                keep_on_top=True, no_titlebar=True, background_color=popupBackgroundColor,
                any_key_closes=True, grab_anywhere=True, button_justification='centered')
    if event == 'Generate' and not values['NewFilePath']:
        sg.popup('Не указан путь сохранения файла, проверьте входные данные',
                keep_on_top=True, no_titlebar=True, background_color=popupBackgroundColor,
                any_key_closes=True, grab_anywhere=True, button_justification='centered')
    if event == 'Generate' and (not values['Duration'] or values['Duration'][0]==':'):
        sg.popup('Не указана продолжительность нового трека, проверьте входные данные',
                keep_on_top=True, no_titlebar=True, background_color=popupBackgroundColor,
                any_key_closes=True, grab_anywhere=True, button_justification='centered')
    if event == 'SettingsButton': #открыть окно доп. настроек
        layoutSettingsWindow = [[sg.Text('Мин. индекс случайного соседнего аккорда: '), sg.Push(),
                                 sg.InputText(key='MinIndex', default_text=currentMinNearChordIndex, enable_events=True,
                                              size=(14, 1))],
                                [sg.Text('Макс. индекс случайного соседнего аккорда: '), sg.Push(),
                                 sg.InputText(key='MaxIndex', default_text=currentMaxNearChordIndex, enable_events=True,
                                              size=(14, 1))],
                                [sg.Text('Вероятность конечной продукции вместо промежуточной: '), sg.Push(),
                                 sg.InputText(key='Probability', default_text=currentEndRuleProbability, enable_events=True,
                                              size=(14, 1))],
                                [sg.Push(), sg.Button('Восст. по умолчанию',key='restoreByDefault')],
                                [sg.Push(), sg.OK(key='OkSettings', size=(7,1)), sg.Push()]]
        settingsWindow = sg.Window('Доп. настройки генерации', layoutSettingsWindow, icon=icon_name,
                                   disable_minimize=True, modal=True)
        while True:
            event, values = settingsWindow.read()
            if event == sg.WIN_CLOSED or event == 'Exit':
                break
            if event == 'OkSettings': #сохранить настройки генерации
                if(int(values['MinIndex'])> int(values['MaxIndex'])):
                    sg.popup('Мин. значение индекса не может быть больше максимального',
                             keep_on_top=True, no_titlebar=True, background_color=popupBackgroundColor,
                             any_key_closes=True, grab_anywhere=True, button_justification='centered')
                    continue
                if(float(values['Probability'])>1):
                    sg.popup('Вероятность не может быть больше 1',
                             keep_on_top=True, no_titlebar=True, background_color=popupBackgroundColor,
                             any_key_closes=True, grab_anywhere=True, button_justification='centered')
                    continue
                currentMinNearChordIndex = int(values['MinIndex'])
                currentMaxNearChordIndex = int(values['MaxIndex'])
                currentEndRuleProbability = float(values['Probability'])
                break
            if event == 'restoreByDefault': #восстановить значения по умолчанию
                currentMinNearChordIndex = defaultMinNearChordIndex
                currentMaxNearChordIndex = defaultMaxNearChordIndex
                currentEndRuleProbability = defaultEndRuleProbability
                settingsWindow['MinIndex'].update(currentMinNearChordIndex)
                settingsWindow['MaxIndex'].update(currentMaxNearChordIndex)
                settingsWindow['Probability'].update(currentEndRuleProbability)
            if event == 'MinIndex':
                str = values['MinIndex']
                i = 0
                for character in str:  # Защита ввода продолжительности, только цифры
                    if i == 0 and character == '-':
                        i = i + 1
                        continue
                    if character not in ('0123456789'):
                        str = str[:i] + str[i+1:]
                        settingsWindow['MinIndex'].update(str)
                        i = -1
                    i = i + 1
            if event == 'MaxIndex':
                str = values['MaxIndex']
                i = 0
                for character in str:  # Защита ввода продолжительности, только цифры
                    if i == 0 and character == '-':
                        i = i + 1
                        continue
                    if character not in ('0123456789'):
                        str = str[:i] + str[i+1:]
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
        settingsWindow.close()