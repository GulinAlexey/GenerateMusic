import PySimpleGUI as sg
import mido

midiFormat = '.mid'
format0FilenameEnd = '_format0.mid'
resultFilenameEnd = '_result.mid'

def convertType1ToType0(midiType1FilePath):
    midiType1 = mido.MidiFile(midiType1FilePath)
    midiType0Tracks = mido.merge_tracks(midiType1.tracks)
    midiType0 = mido.MidiFile(type = 0, ticks_per_beat=midiType1.ticks_per_beat)
    midiType0.tracks.append(midiType0Tracks)
    filename = midiType1FilePath.removesuffix(midiFormat) + format0FilenameEnd
    midiType0.save(filename)
    return filename

layout = [
    [sg.Text('MIDI файл'), sg.InputText(),
     sg.FileBrowse('Выбрать',key="inputFile",file_types=(("MIDI files", "*.mid"),))],
    [sg.Output(size=(63, 10))],
    [sg.Submit('Генерировать'), sg.Cancel('Отмена')]
]
window = sg.Window('Генерация музыки', layout, icon='app_icon.ico')
while True:                             # The Event Loop
    event, values = window.read()
    if event in (None, 'Exit', 'Cancel'):
        break
    if event == 'Генерировать':
        midiFileType0Path = convertType1ToType0(values["inputFile"])