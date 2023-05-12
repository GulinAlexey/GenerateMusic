import PySimpleGUI as sg        #версия 4.61.0.173
import mido                     #версия 1.2.10
import os
import statistics

from ExtendendMessage import ExtendendMessage
from Chord import Chord
from UniqueChordAdding import appendUniqueChord
from ChordComparison import chordsAreEqual
from GrammarNode import GrammarNode
from ChordSequenceComparison import chordSequencesAreEqual

midiFormat = '.mid'
format0FilenameEnd = '_format_0' + midiFormat #конец имени промежуточного файла - конвертированного исходного в формат 0

def convertType1ToType0(midiType1FilePath): #Конвертация MIDI из формата 1 в формат 0 (объединить все треки)
    midiType1 = mido.MidiFile(midiType1FilePath)
    midiType0Tracks = mido.merge_tracks(midiType1.tracks)
    midiType0 = mido.MidiFile(type = 0, ticks_per_beat=midiType1.ticks_per_beat)
    midiType0.tracks.append(midiType0Tracks)
    filename = midiType1FilePath.removesuffix(midiFormat) + format0FilenameEnd
    midiType0.save(filename)
    return filename

def midiGenerate(midiType0FilesPaths, newFileNamePath, newDurationSeconds): #Генерация нового MIDI-файла
    inputMidis = []
    for path in midiType0FilesPaths:
        inputMidis.append(mido.MidiFile(path))
    grammar, newTicksPerBeat, listOfChords = buildGrammar(inputMidis)
    outputMidi = mido.MidiFile(type = 0, ticks_per_beat=newTicksPerBeat)
    outputTrack = mido.MidiTrack()
    outputMidi.tracks.append(outputTrack)
    outputMidi.save(newFileNamePath)

def buildGrammar(midis): #Построение контестно-зависимой грамматики по MIDI-файлам (формата 0)
    roots = [] #грамматика - возвращаемое значение
    newTicksPerBeat = statistics.mean([midi.ticks_per_beat for midi in midis]) #такт = среднеарифм. среди MIDI
    listOfChords = [] #список аккордов всех входных MIDI-файлов
    for midi in midis:
        messages = [ExtendendMessage(m) for m in midi.tracks[0] if (m.is_meta == False)
                    or (m.is_meta == True and m.type=='set_tempo')] #все сообщения трека (кроме мета- и изменения темпа)
        absoluteTime=0
        for m in messages:
            absoluteTime = absoluteTime + m.msg.time
            m.absolute = absoluteTime #получить абсолютное время для сообщения
            if m.msg.type == 'note_off': #найти сообщение начала звучания ноты и записать для неё длительность
                messagesBeforeThisMsg = list(reversed(messages[:(messages.index(m))]))
                for msgBefore in messagesBeforeThisMsg:
                    if msgBefore.msg.type == 'note_on' and msgBefore.msg.channel == m.msg.channel \
                            and msgBefore.msg.note == m.msg.note:
                        messages[messages.index(m)-(messagesBeforeThisMsg.index(msgBefore))-1].duration = \
                            m.absolute - msgBefore.absolute    #записать длительность звучания ноты
                        break
        # убрать сообщения выключения ноты, так как инфо о длительности звучания хранится у сообщ-ий включения ноты
        messages = [m for m in messages if m.msg.type!='note_off']
        msgGroups = {}
        for m in messages: #сгруппировать сообщения по абсолютному времени в словарь (ключ - абсолютное время)
            msgGroups.setdefault(m.absolute, []).append(m)
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
        listOfChords.append(chords) #добавить в список аккордов всех входных MIDI-файлов
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
    return roots, newTicksPerBeat, listOfChords

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
        pass
    else: #только один возможный вариант аккорда после последовательности,добавить его в словарь продукции, если его ещё нет
        #if followingChords[0] not in
        pass

midiList = [] #Список исходных MIDI-файлов для генерации

#интерфейс
layout = [[sg.Text('Исходные MIDI-файлы:'), sg.Push(),
    sg.Column([[sg.FileBrowse('Добавить',key='InputFile',
    enable_events=True, file_types=(('MIDI files', '*.mid'),))]]),
    sg.Button('Удалить', key='DeleteFile'), sg.Button('Очистить', key='ClearFiles')],
    [sg.Listbox(midiList, size=(73,10), enable_events=True,  key='MidiListView')],
    [sg.Text('Имя генерируемого файла: '), sg.InputText(key = 'NewFilePath', size=(34,1)),
    sg.FileSaveAs('Сохранить как', file_types=(('MIDI files', '*.mid'),))],
    [sg.Text('Длительность нового трека:'), sg.InputText(key='Duration', size=(34,1), enable_events=True)],
    [sg.Checkbox('Открыть результат после генерации', key='OpenAfterGeneration', default=True)],
    [sg.Text('Лог работы:')], ### TODO: убрать в итоговой версии
    [sg.Output(size=(73, 10))], ### TODO: убрать в итоговой версии
    [sg.Push(), sg.Submit('Генерировать', key='Generate'),
    sg.Cancel('Отменить и выйти', key='Cancel'), sg.Push()]
]
window = sg.Window('Генерация музыки', layout, icon='app_icon.ico') #Окно программы
while True:                             #The Event Loop
    event, values = window.read()
    if event in (None, 'Exit', 'Cancel'): #Выход из программы
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
    if event == 'Duration' and values['Duration'] and values['Duration'][-1] not in ('0123456789:')\
            or values['Duration'].count(':') > 1: #Защита ввода продолжительности, только цифры и одно ":"
        window['Duration'].update(values['Duration'][:-1])
    if event == 'Generate' and midiList and values['NewFilePath'] and values['Duration']: #Генерация файла
        midiFilesType0Paths = []
        for midiElement in midiList:
            midiFilesType0Paths.append(convertType1ToType0(midiElement))
        partitionOfDuration = values['Duration'].partition(':')
        if(partitionOfDuration[1] == ''): #Получить продолжительность нового трека в секундах
            duration = int(partitionOfDuration[0])
        else:
            duration = int(partitionOfDuration[0]) * 60 + int(partitionOfDuration[2])
        midiGenerate(midiFilesType0Paths, values['NewFilePath'], duration)
        for midi0 in midiFilesType0Paths: #Удалить промежуточные файлы
            if os.path.isfile(midi0): #защита от попытки удаления несуществующего файла
                os.remove(midi0)
        sg.popup('Успешно сгенерировано', keep_on_top=True, no_titlebar = True, background_color='#1a263c',
                 any_key_closes = True, grab_anywhere = True, button_justification= 'centered')
        if values['OpenAfterGeneration'] == True: #Открыть созданный файл, если отмечен checkbox
            os.system(values['NewFilePath'])
    if event == 'Generate' and not midiList:
        sg.popup('Список исходных MIDI-файлов пуст, проверьте входные данные',
                keep_on_top=True, no_titlebar=True, background_color='#1a263c',
                any_key_closes=True, grab_anywhere=True, button_justification='centered')
    if event == 'Generate' and not values['NewFilePath']:
        sg.popup('Не указан путь сохранения файла, проверьте входные данные',
                keep_on_top=True, no_titlebar=True, background_color='#1a263c',
                any_key_closes=True, grab_anywhere=True, button_justification='centered')
    if event == 'Generate' and not values['Duration']:
        sg.popup('Не указана продолжительность нового трека, проверьте входные данные',
                keep_on_top=True, no_titlebar=True, background_color='#1a263c',
                any_key_closes=True, grab_anywhere=True, button_justification='centered')