import PySimpleGUI as sg
import mido

format0FilenameEnd = '_format0.mid'

def convert_type1_to_type0(midi_type1_file):
    midi_type_1 = mido.MidiFile(midi_type1_file)
    if midi_type_1.type != 0:
        mido.merge_tracks(midi_type_1.tracks)
    midi_type_1.save(midi_type_1.filename + format0FilenameEnd)

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
        convert_type1_to_type0(values["inputFile"])