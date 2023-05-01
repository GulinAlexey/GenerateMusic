import PySimpleGUI as sg
import mido

format0FilenameEnd = '_format0.mid'

def convertType1ToType0(midiType1File):
    midiType1 = mido.MidiFile(midiType1File)
    midiType0Tracks = mido.merge_tracks(midiType1.tracks)
    midiType0 = mido.MidiFile(type = 0, ticks_per_beat=midiType1.ticks_per_beat)
    midiType0.tracks.append(midiType0Tracks)
    midiType0.save(midiType1.filename + format0FilenameEnd)

layout = [
    [sg.Text('MIDI файл'), sg.InputText(),
     sg.FileBrowse('Выбрать',key="inputFile",file_types=(("MIDI files", "*.mid"),))],
    [sg.Output(size=(63, 10))],
    [sg.Submit('Генерировать'), sg.Cancel('Отмена')]
]
window = sg.Window('Generate Music', layout)
while True:                             # The Event Loop
    event, values = window.read()
    if event in (None, 'Exit', 'Cancel'):
        break
    if event == 'Генерировать':
        convertType1ToType0(values["inputFile"])
