from django.shortcuts import render
import numpy as np
import sounddevice as sd
import wave #pydub대용임
from scipy.io import wavfile

def generate_sine_wave(duration, frequency, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    data = 0.5 * np.sin(2 * np.pi * frequency * t)
    scaled_data = (data * 32767).astype(np.int16)
    return scaled_data

def play_sound(data, sample_rate=44100):
    sd.play(data, samplerate=sample_rate)
    sd.wait()

def save_to_wav(data, filename, sample_rate=44100):
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)          
        wf.setsampwidth(4)          # 4바이트(32비트) 샘플 폭
        wf.setframerate(sample_rate)
        wf.writeframes(data)

lista = [900,1000,1100,1200]
duration = 1.0
frequency = 2000

result = generate_sine_wave(0.1, 0) # 사인파들을 numpy.ndarray 형태로 받아올 빈 numpy.ndarray
for i in lista:  # 실험용 , 주가데이터를 알맞게 변환해서 넣어야 함
    data = generate_sine_wave(duration, i) # 사인파로 만들고
    result = np.concatenate((result,data)) # 만든 것들을 result에 합침

    play_sound(data) # 일단 들려줌

print(result)
wavfile.write("Sine.wav",44100,result) # wav파일로 변환
