

from loguru import logger
import os, sys, time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
from pathlib import Path
import pyaudio
import requests, shutil
from io import BytesIO
from PIL import Image   #pillow package
import base64

load_dotenv()   # load environment variables from .env
logs_folder_path = Path(__file__).parent / "logs/ChatGPT_simple_log"

OPENAI_TEXT_API_KEY = os.environ.get("OPENAI_TEXT_API_KEY")
OPENAI_TEXT_MODEL = os.environ.get("OPENAI_TEXT_MODEL")
OPENAI_TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL")
OPENAI_TTS_VOICE = os.environ.get("OPENAI_TTS_VOICE")
OPENAI_AudioToText_MODEL = os.environ.get("OPENAI_AudioToText_MODEL")
OPENAI_IMAGE_MODEL=os.environ.get("OPENAI_IMAGE_MODEL")
OPENAI_IMAGEDESC_MODEL=os.environ.get("OPENAI_IMAGEDESC_MODEL")

temp_folder_path = Path(__file__).parent / "temp/"
images_folder_path = Path(__file__).parent / "ImageFiles/"
images_file_name="image.jpeg"   # image extension is important and DALLE will automtically detect which image type you want based on it. Also, using DALLE-2 as currently DALLE3 doesnt support edits
speech_folder_path = Path(__file__).parent / "SpeechFiles/"
speech_file_name="speech.mp3"

# Add a sink with rotation and retention policies
logger.add(os.path.join(logs_folder_path), rotation="10 KB", retention="24 hours")

api_key=os.environ['OPENAI_API_KEY']
if not api_key:
    logger.critical("ChatGPT API Key not found. Pls set API key in .env file.")
    os._exit(1)

print(api_key)
openAI_client = OpenAI(api_key=api_key)

def get_unique_file_path(folder_path, file_name):
    try:
        # Create the base file name with date and time
        base, ext = os.path.splitext(file_name)
        date_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_file_name = f"{base}_{date_time}{ext}"
        full_path = os.path.join(folder_path, unique_file_name)

        # Append number if the file with same name and date_time already exists
        count = 1
        while os.path.exists(full_path):
            unique_file_name = f"{base}_{date_time}_{count}{ext}"
            full_path = os.path.join(folder_path, unique_file_name)
            count += 1

        logger.info(f"Full File path: {full_path}")
        return full_path
    except Exception as e:
        logger.critical(f"Error generating unique file path at folder: {folder_path} with file name: {file_name} ::: {e}")
        return None

###########################################################################################################################
def generateImage(imageDesc):
    try:
        logger.info(f"Function: generateImage, model={OPENAI_IMAGE_MODEL}, prompt={imageDesc}, n=1, quality=standard, size=1024x1024")
        response = openAI_client.images.generate(
            model=OPENAI_IMAGE_MODEL,
            #prompt="A cute baby sea otter",
            prompt=imageDesc,
            n=1,
            quality="standard",
            size="1024x1024"
        )
                
        # send get request to the url
        getRequestResponse = requests.get(response.data[0].url, stream=True)
        logger.info(f"Function: generateImage, Image URL received: {response.data[0].url}")
        if getRequestResponse.status_code == 200:
            image_file_path = get_unique_file_path(images_folder_path, images_file_name)    
            with open(image_file_path, 'wb') as file:
                shutil.copyfileobj(getRequestResponse.raw, file)
            logger.success(f"Function: generateImage, Image successfully downloaded: {image_file_path}")
        else:
            logger.error(f"Function: generateImage, Failed to downlod image. Status Code: {getRequestResponse.status_code}")
 
    except Exception as e:
        #print(f"Error generating Image: {e}")
        logger.critical(f"Function: generateImage, Error generating Image: {e}")
        return None
###########################################################################################################################
'''
# Not what i wanted, thus an incomplete function for editing images. DALLE2 requires manual intervention to create a mask image, 
# # whereas i wanted a programmatic way to get the mask image or edit the origirnal image without having to have a manual step
# Unfortunately, there is no way i can accomplish this.
def editImage(originalImagePath, editDesc):
    try:
        
        logger.info(f"Function: editImage, model={OPENAI_IMAGE_MODEL}, Original Image={originalImagePath}, n=1, quality=standard, size=1024x1024, editDesc={editDesc}")
        ''''''
        #converting image to RGBA as it is required by DALLE
        originalImage = Image.open(originalImagePath)
        rgbaImage = originalImage.convert("RGBA")
        tempImagePath = rgbaImage.save(get_unique_file_path(temp_folder_path, "tempImg.png"))
        ''''''
        response = openAI_client.images.edit(
            model=OPENAI_IMAGE_MODEL,
            image=open(originalImagePath, "rb"),
            #mask=open("mask.jpeg", "rb"),
            prompt=editDesc,
            n=1,
            size="1024x1024"
        )
        logger.info("2")
        # send get request to the url
        getRequestResponse = requests.get(response.data[0].url, stream=True)
        logger.info(f"Function: editImage, Image URL received: {response.data[0].url}")
        if getRequestResponse.status_code == 200:
            image_file_path = get_unique_file_path(images_folder_path, images_file_name)    
            with open(image_file_path, 'wb') as file:
                shutil.copyfileobj(getRequestResponse.raw, file)
            logger.success(f"Function: editImage, Image successfully downloaded: {image_file_path}")
        else:
            logger.error(f"Function: editImage, Failed to downlod image. Status Code: {getRequestResponse.status_code}")

        # delete temo image created
        #if os.path.exists(tempImagePath): 
        #    os.remove(tempImagePath)

    except Exception as e:
        #print(f"Error generating Image: {e}")
        logger.critical(f"Function: editImage, Error generating Image: {e}")
        return None
'''
###########################################################################################################################
def generateImageDesc(imagePath):
    try:
        logger.info(f"Function: generateImageDesc, model={OPENAI_IMAGEDESC_MODEL}, Image Path={imagePath}, detail=low")
        
        with open(imagePath, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        response = openAI_client.chat.completions.create(
            model=OPENAI_IMAGEDESC_MODEL,
            messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image? Describe the image in 2-3 sentences."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low",    # to keep the num of tokens and thus cost low
                        },
                    },
                    ],
            }
            ],
            max_tokens=300,
            )
        print(response.choices[0])
    except Exception as e:
        logger.critical(f"Function: generateImageDesc, Error generating Image: {e}")
        return None
###########################################################################################################################
'''
def read_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            for page in range(len(reader.pages)):
                text += reader.pages[page].extract_text()
            return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None
'''

###########################################################################################################################
# this is not working due to pyaudio package version. PyAudio installed version is 0.2.11, but needed is 0.2.13 or greater where the issue is fixed. 
# But, Anaconda has not upgraded pyaudio version to 0.2.13 or 0.2.14 for Windows. It has only done it for linux
def stream_to_speakers(audioText) -> None:

    player_stream = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)

    start_time = time.time()

    with openAI_client.audio.speech.with_streaming_response.create(
        model=OPENAI_TTS_MODEL,
        voice=OPENAI_TTS_VOICE,
        response_format="pcm",  # similar to WAV, but without a header chunk at the start.
        input=audioText,
    ) as response:
        #print(f"Time to first byte: {int((time.time() - start_time) * 1000)}ms\n")
        logger.info(f"Function: stream_to_speakers, Time to first byte: {int((time.time() - start_time) * 1000)}ms\n")
        for chunk in response.iter_bytes(chunk_size=1024):
            player_stream.write(chunk)

    print(f"Done in {int((time.time() - start_time) * 1000)}ms.\n")
###########################################################################################################################    

# Converts text provided as input into a ,mp3 audio file and saves at speech_folder_path
def text_to_speech(text) -> None:
    try:
        #stream_to_speakers(text)
        speech_file_path = Path(get_unique_file_path(speech_folder_path, speech_file_name))
        logger.info(f"Function: text_to_speech, speech_file_path::{speech_file_path}")
        # Create text-to-speech audio file
        logger.info(f"Function: text_to_speech, model={OPENAI_TTS_MODEL}, voice={OPENAI_TTS_VOICE}, input={text}")
        with openAI_client.audio.speech.with_streaming_response.create(
            model=OPENAI_TTS_MODEL,
            voice=OPENAI_TTS_VOICE,
            input=text,
        ) as response:
            response.stream_to_file(speech_file_path)
        
        logger.success(f"Function: text_to_speech, speech_file_path: {speech_file_path}")

        # Create transcription from audio file
        transcription = openAI_client.audio.transcriptions.create(
            model=OPENAI_AudioToText_MODEL,
            file=speech_file_path,
        )
        logger.success(f"Function: text_to_speech, Transcription Text: {transcription.text}")
        # Create translation from audio file
        translation = openAI_client.audio.translations.create(
            model=OPENAI_AudioToText_MODEL,
            file=speech_file_path,
        )
        logger.success(f"Function: text_to_speech, Translation Text: {translation.text}")
    except Exception as e:
        logger.critical(f"Function: text_to_speech, Error: {e}")
        return None
###########################################################################################################################    
# provides overview with example of the topic provided    
def topicOverview(topicName):
    try:
        topic = "Provide a paragraph with 4 to 5 lines describing " + topicName + ". Also, provide a real world example on it. Also, if available, gather the most latest news on the topic and print a 2-3 line summary of the latest news and date it was published."
        logger.info(f"Function: topicOverview, Fetching information on the following topic: {topic}")
        logger.info(f"Function: topicOverview, Model: {OPENAI_TEXT_MODEL}, Role: User")
        completion = openAI_client.chat.completions.create(
            model=OPENAI_TEXT_MODEL,
            messages=[
            {
                "role": "user",
                "content": topic,
            },
            ],
        )
        
        print(f"Topic Overview: {completion.choices[0].message.content}")
        logger.success(f"Function: topicOverview, Topic Overview: {completion.choices[0].message.content}")
        
    except Exception as e:
        logger.critical(f"Function: topicOverview, Error gathering topic information: {e}")
        return None

###########################################################################################################################    
#   MAIN

if __name__== "__main__":
    
    logger.info("OpenAI ChatGPT Simple Examples...")
    #opicOverview("ChatGPT")
    #text_to_speech("Hello, How are you? My name is Neeraj. It's a beautiful day! We should plan something.")
    #generateImage("image of a man standing in front of taj mahal, but replace the face of the man with the face of an elephant")
    
    originalImagePath=Path(__file__).parent / "OriginalImagesForEdits\\tempImg_20250104_192240.png"
    #imagePathForDesc = "C:\\Users\njger\source\repos\OpenAI_ChatGPT_simple\OpenAI_ChatGPT_simple\OriginalImagesForEdits\tempImg_20250104_192240.png"
    #imagePathForDesc = "https://images.pexels.com/photos/7526055/pexels-photo-7526055.jpeg"
    imagePathForDesc = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
    
    editDesc="image of a man standing in front of taj mahal with a face of a lion. Keep the quality of the image same as original image"
    ##editImage(originalImagePath, editDesc)
    generateImageDesc(imagePathForDesc)

    logger.info("Good Bye...")
    sys.exit