from django.shortcuts import render
import speech_recognition as sr
from pydub import AudioSegment
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from io import BytesIO
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import permissions 

# recognizer = sr.Recognizer()

# # 실험할 때 쓴 m4a 파일 wav파일로 변환하는 과정, 주석처리
# # audio_file = "hsmdc.m4a"
# # wav_file = "hsmdc.wav"
# # sound = AudioSegment.from_file(audio_file, format="m4a")
# # sound.export(wav_file, format="wav")

# # 음성파일 넣기
# with sr.AudioFile("hsmdc.wav") as source:
#     audio = recognizer.record(source)

# # Google Web Speech API를 사용하여 음성 인식
# try:
#     result = recognizer.recognize_google(audio, language="ko-KR") # 한국어로 번역 + 인식함
#     print("음성 인식 결과:", result)
# except sr.UnknownValueError:
#     print("음성 인식 실패: 알아들을 수 없는 음성")
# except sr.RequestError as e:
#     print(f"오류 발생: {e}")
@swagger_auto_schema(
    method='post',
    operation_id='음성을 텍스트로 변환',
    operation_description='사용자의 음성을 텍스트로 변환',
    tags=['음성'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT, 
        properties={
            'audio': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_BINARY,
            ),
        },
        required=['audio'],
    ),
)
@api_view(['POST'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([permissions.AllowAny])
def speech_recognition(request):
    recognizer = sr.Recognizer()

    # 음성 파일 받기 (request.FILES를 통해 업로드한 음성파일을 받음)
    audio_file = request.FILES.get('audio')

    # 업로드된 음성 파일을 wav 형식으로 변환
    audio_data = AudioSegment.from_file(audio_file, format="m4a")
    wav_stream = BytesIO()
    audio_data.export(wav_stream, format="wav")
    wav_stream.seek(0)

    # 음성파일로부터 음성 인식
    try:
        with sr.AudioFile(wav_stream) as source:
            audio = recognizer.record(source)

        result = recognizer.recognize_google(audio, language="ko-KR")  # 한국어로 번역 + 인식함
        return Response({"result": result}, status=status.HTTP_200_OK)
    except sr.UnknownValueError:
        return Response({"error": "음성 인식 실패: 알아들을 수 없는 음성"}, status=status.HTTP_400_BAD_REQUEST)