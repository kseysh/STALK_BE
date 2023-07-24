from django.shortcuts import render
import speech_recognition as sr
from pydub import AudioSegment

recognizer = sr.Recognizer()

# 실험할 때 쓴 m4a 파일 wav파일로 변환하는 과정, 주석처리
# audio_file = "hsmdc.m4a"
# wav_file = "hsmdc.wav"
# sound = AudioSegment.from_file(audio_file, format="m4a")
# sound.export(wav_file, format="wav")

# 음성파일 넣기
with sr.AudioFile("hsmdc.wav") as source:
    audio = recognizer.record(source)

# Google Web Speech API를 사용하여 음성 인식
try:
    result = recognizer.recognize_google(audio, language="ko-KR") # 한국어로 번역 + 인식함
    print("음성 인식 결과:", result)
except sr.UnknownValueError:
    print("음성 인식 실패: 알아들을 수 없는 음성")
except sr.RequestError as e:
    print(f"오류 발생: {e}")

