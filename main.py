import praw
from dotenv import load_dotenv, find_dotenv
import os
from os import path
from imgfacerec import CelebAnalyzer
import webbrowser
from imgur_python import Imgur
import cv2


load_dotenv(find_dotenv())
password1 = os.environ.get("REDDITBOT_PWD")  
imgur_secret = os.environ.get("IMGUR_SECRET")
imgur_accesstoken = os.environ.get("IMGUR_ACCESSTOKEN")
imgur_refreshtoken = os.environ.get("IMGUR_REFRESHTOKEN")
reddit_secret = os.environ.get("REDDIT_SECRET")
def IMGUR_UPLOAD(img):
    imgur_client = Imgur({
                        "client_id": "05e6366a0ca9ca8",
                        "client_secret": imgur_secret,
                        "access_token": imgur_accesstoken,
                        "expires_in": "315360000",
                        "token_type": "bearer",
                        "refresh_token": imgur_refreshtoken,
                        "account_username": "FaceRecBot",
                        "account_id": '170923657'
                        })
    auth_url = imgur_client.authorize()
    webbrowser.open(auth_url)
    output_path = os.path.join(os.getcwd(), 'processed_image.jpg')
    cv2.imwrite(output_path, img)
    file = os.path.join(os.getcwd(), 'processed_image.jpg')
    title = 'Faces Recognized'
    description = 'Disclaimer! I am a bot, the faces I detect are not 100% accurate!'
    album = None
    disable_audio = 0
    response = imgur_client.image_upload(file, title, description, album, disable_audio)
    return response


def Find_and_Reply(subreddit_name):
    #Create A Reddit Instance
    reddit = praw.Reddit(
        client_id="qDuKIgPxnzMWQ2xbNYZjYg",
        client_secret=reddit_secret,
        user_agent="Facial Recognition Script",
        username='FaceRecognitionBot',
        password=password1,
        ratelimit_seconds=300
        )

    #Find Subreddit
    subreddit_submissions = reddit.subreddit(subreddit_name).hot(limit=5)

    #look through submissions
    for submission in subreddit_submissions:
        submission.comments.replace_more(limit=None) #replaces old comments if it comes across MoreComments object
    # submission = reddit.submission(url='https://www.reddit.com/r/test/comments/13p65nl/face_rec_test/')
        for comment in submission.comments:
            comment_lower = comment.body.lower()
            if '!facerec' in comment_lower:
                comment_id = comment
                img_url = submission.url
                keywords = comment_lower.split(' ')
                del keywords[0]
                analyzer = CelebAnalyzer(img_url, keywords)
                img, info = analyzer.celeb_analyze()
                if info == None:
                    comment.reply("Unable to retrieve image")
                    continue
                IMGUR_link = IMGUR_UPLOAD(img)['response']['data']['link']
                celeb_attributes = []
                for celebinfo in info:
                    for prof in celebinfo:
                        if prof == '_id':
                            continue
                        nest1 = celebinfo[prof]
                        for name in nest1:
                            stuff = [name]
                            nest2 = celebinfo[prof][name]
                            for attribute in nest2:
                                nest3 = nest2[attribute]
                                stuff.append(nest3)
                                if len(stuff) % 4 == 0:
                                    celeb_attributes.append(stuff)
                reply = '\n\n'.join(f'{celeb_attribute[0]}\n\nAstrosign: {celeb_attribute[1]}; Age: {celeb_attribute[2]}; Birthday: {celeb_attribute[3]}; Birthplace: {celeb_attribute[4]}'  for celeb_attribute in celeb_attributes)
                comment.reply(IMGUR_link + '\n\n' + reply)


    

success = Find_and_Reply('memes')

