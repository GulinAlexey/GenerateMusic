import PySimpleGUI as sg
import mido
import os

midiFormat = '.mid'
format0FilenameEnd = '_format_0' + midiFormat
resultFilenameEnd = '_result' + midiFormat

def convertType1ToType0(midiType1FilePath):
    midiType1 = mido.MidiFile(midiType1FilePath)
    midiType0Tracks = mido.merge_tracks(midiType1.tracks)
    midiType0 = mido.MidiFile(type = 0, ticks_per_beat=midiType1.ticks_per_beat)
    midiType0.tracks.append(midiType0Tracks)
    filename = midiType1FilePath.removesuffix(midiFormat) + format0FilenameEnd
    #print(midiType0.tracks)
    midiType0.save(filename)
    return filename

def MidiGenerate(midiType0FilesPaths, newFileNamePath, newDurationSeconds):
    inputMidis = []
    for path in midiType0FilesPaths:
        inputMidis.append(mido.MidiFile(path))
    outputMidi = mido.MidiFile(type = 0, ticks_per_beat=inputMidis[0].ticks_per_beat)
    outputTrack = mido.MidiTrack()
    outputMidi.tracks.append(outputTrack)
    #############################
    outputMidi.save(newFileNamePath)

midiList = []

layout = [[sg.Text('Исходные MIDI-файлы:'), sg.Push(),
    sg.Column([[sg.FileBrowse('Добавить',key='InputFile',
    enable_events=True, file_types=(('MIDI files', '*.mid'),))]]),
    sg.Button('Удалить', key='DeleteFile'), sg.Button('Очистить', key='ClearFiles')],
    [sg.Listbox(midiList, size=(73,10), enable_events=True,  key='MidiListView')],
    [sg.Text('Имя генерируемого файла: '), sg.InputText(key = 'NewFilePath', size=(34,1)),
    sg.FileSaveAs('Сохранить как', file_types=(('MIDI files', '*.mid'),))],
    [sg.Text('Длительность нового трека:'), sg.InputText(key='Duration', size=(34,1), enable_events=True)],
    [sg.Checkbox('Открыть результат после генерации', key='OpenAfterGeneration', default=True)],
    #[sg.Text('Лог работы:')],
    #[sg.Output(size=(73, 10))],
    [sg.Push(), sg.Submit('Генерировать', key='Generate'),
    sg.Cancel('Отменить и выйти', key='Cancel'), sg.Push()]
]
window = sg.Window('Генерация музыки', layout, icon='app_icon.ico')
while True:                             # The Event Loop
    event, values = window.read()
    if event in (None, 'Exit', 'Cancel'):
        break
    if event == 'InputFile':
        midiList.append(values['InputFile'])
        window['MidiListView'].update(midiList)
    if event == 'DeleteFile' and values['MidiListView']:
        midiList.remove(values['MidiListView'][0])
        window['MidiListView'].update(midiList)
    if event == 'ClearFiles':
        midiList.clear()
        window['MidiListView'].update(midiList)
    if event == 'Duration' and values['Duration'] and values['Duration'][-1] not in ('0123456789:')\
            or values['Duration'].count(':') > 1:
        window['Duration'].update(values['Duration'][:-1])
    if event == 'Generate' and midiList and values['NewFilePath']:
        midiFilesType0Paths = []
        for midiElement in midiList:
            midiFilesType0Paths.append(convertType1ToType0(midiElement))
        partitionOfDuration = values['Duration'].partition(':')
        if(partitionOfDuration[1] == ''):
            duration = int(partitionOfDuration[0])
        else:
            duration = int(partitionOfDuration[0]) * 60 + int(partitionOfDuration[2])
        MidiGenerate(midiFilesType0Paths, values['NewFilePath'], duration)
        for midi0 in midiFilesType0Paths:
            os.remove(midi0)
        sg.popup('Успешно сгенерировано', keep_on_top=True, no_titlebar = True,
                 any_key_closes = True, grab_anywhere = True, button_justification= 'centered')
        if values['OpenAfterGeneration'] == True:
            os.system(values['NewFilePath'])