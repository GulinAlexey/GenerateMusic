import PySimpleGUI as sg
layout = [
    [sg.Text('File'), sg.InputText(), sg.FileBrowse()],
    [sg.Output(size=(57, 10))],
    [sg.Submit(), sg.Cancel()]
]
window = sg.Window('Generate Music', layout)
while True:                             # The Event Loop
    event, values = window.read()
    # print(event, values) #debug
    if event in (None, 'Exit', 'Cancel'):
        break