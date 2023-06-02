import mido

class GettingOfChordSequenceDurationInSeconds:
    @staticmethod
    # получить продолжительность последовательности аккордов в секундах
    def getChordSequenceDurationInSeconds(chordSequence, ticksPerBeat):
        time = 0
        tempo = mido.midifiles.midifiles.DEFAULT_TEMPO
        for chord in chordSequence:
            for m in chord.msgs:
                if m.msg.type == 'set_tempo':
                    tempo = m.msg.tempo
            time = time + mido.tick2second(chord.delay, ticksPerBeat, tempo)
        return time