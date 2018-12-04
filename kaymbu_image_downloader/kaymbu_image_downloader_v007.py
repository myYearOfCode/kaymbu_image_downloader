'''
KAYMBU image downloader by myYearOfCode
https://github.com/myYearOfCode/kaymbu_image_downloader
Based off of "Reading GMAIL using Python" - Abhishek Chhibber

This script does the following:
- Go to Gmail inbox. I set up a specific address just for this. My main 
     email address forwards based on a filter.
- Find and read all the unread messages
- Filter based on subject search term
- Find images in email
- Download image urls (rate limit 1 req/s to be polite)
- Save images into dated folders based on email sent date
- Mark the messages as Read - so that they are not read again 
- downloads mp4s as well.

This script could do this in the future:
- allow filter tweaking without having to get deep into the code.

Before running this script, the user should get the authentication by following 
the link: https://developers.google.com/gmail/api/quickstart/python
Also, client_secret.json should be saved in the same directory as this file.
Lastly, the preferences.json file needs to be filled out with your 'search_term'
and 'save_dir' values
'''

# Importing required libraries
import urllib.request
from apiclient import discovery
from httplib2 import Http
from oauth2client import file, client, tools
import base64
import dateutil.parser as parser
import datetime
import sys
import os
import json
import time
from bs4 import BeautifulSoup

def does_file_exist(file):
    # checks for existence of a file
    return (os.path.exists(file))

def ensure_dir(file_path):
    '''
    see if dir exists. make it if it does not.
    '''
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def read_prefs():
    '''
    this reads prefs from a json file
    '''
    pathname = os.path.dirname(sys.argv[0])    
    with open(os.path.abspath(pathname)+'/config.json', 'r') as f:
        config = json.load(f)
    return (config['save_dir'],config['search_term'])


def soup_process_email(input):
    """
    this function is passed html
    it parses it with beautiful soup to find image links with a _display tag.
    it removes the _display tag. Then it returns the links as a string.
    if it finds a video it passes it to the soap_process_video function and is
    returned the source url.
    """
    soup = BeautifulSoup(input,'html.parser')
    return_list=[]
    # print (soup.prettify())
    for img in soup.find_all('img'):
        if '_display' in img.get('src'):
            trimmed_link=img.get('src').replace('_display','')
            # avoid duplicates
            if trimmed_link not in return_list and 'video_large' not in trimmed_link:
                return_list.append(trimmed_link)
        if 'video_large_display' in img.get('src'): 
            #process the video and append it to the list of urls to process
            return_list.append( (soup_process_video(img.parent.get('href'))))              
    return (return_list)        

def soup_process_video(input_url):
    """
    this function is passed in one url.
    follow the url and scrape the video src link
    return the video source url
    """
    # scrape the url
    fp = urllib.request.urlopen(input_url)
    #read bytes
    mybytes = fp.read()
    mystr = mybytes.decode("utf8")
    fp.close()
    soup = BeautifulSoup(mystr,'html.parser')
    return (soup.find("a", {'class': "download-btn"}).get('href'))

def main():
    """
    this is the main loop. This will do the scraping and coordination of 
    looking at mail, then coordinating the functions to scrape image and 
    video links, then finally download the images and place them in dated 
    folders.
    """    
    # Creating a storage.JSON file with authentication details
    # we are using modify and not readonly, as we will be marking the messages 
    # as Read    
    SCOPES = 'https://www.googleapis.com/auth/gmail.modify' 
    store = file.Storage('storage.json') 
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    GMAIL = discovery.build('gmail', 'v1', http=creds.authorize(Http()))
    
    messages_retrieved=0
    num_images=0
    save_dir,search_term = read_prefs() 
    
    # Getting all the unread messages from Inbox
    unread_msgs = GMAIL.users().messages().list(userId='me',
                    labelIds=['INBOX', 'UNREAD']).execute()
    
    # We get a dictonary. Now reading values for the key 'messages'
    try:
        mssg_list = unread_msgs['messages']
        print ("Total unread messages in inbox: ", str(len(mssg_list)))
    except KeyError: #handle the keyerror on no new messages by exiting
        print ('No new messages - exiting.')
        return 0   
    
    #loop through the new messages list
    for i,mssg in enumerate(mssg_list):
        temp_dict = { }
        print("processing message {} of {}".format(i+1,len(mssg_list)))
        m_id = mssg['id'] # get id of individual message
        # fetch the message using API
        message = GMAIL.users().messages().get(userId='me', id=m_id).execute() 
        payld = message['payload'] # get payload of the message 
        header = payld['headers'] # get header of the payload
    
        for field in header: # getting the Subject
            if field['name'] == 'Subject':
                msg_subject = field['value']
                temp_dict['Subject'] = msg_subject
            if field['name'] == 'Date':
                msg_date = field['value']
                date_parse = (parser.parse(msg_date))
                m_date = (date_parse.date())
                temp_dict['Date'] = str(m_date)
            else:
                pass
    
        try:

            # Fetching message body
            try: #if there is html/data only
                part_data  = payld['body']['data'] # fetching data
            except: #if there are multiple parts get the html part
                part_data = payld['parts'][0]['body']['data'] # fetching data from the body
            # decoding from Base64 to UTF-8
            clean_one = part_data.replace("-","+").replace("_","/")
            clean_two = base64.b64decode (bytes(clean_one, 'UTF-8')) 
            
            if search_term in temp_dict['Subject']:
                img_list= soup_process_email(clean_two.decode("utf8"))
                print ('{} images found.'.format(len(img_list)))
                
                for i in (img_list):
                    print ("downloading: " +i.split('/')[-1])
                    #adding the email date to filepath
                    write_dir=save_dir+temp_dict['Date']+'/'
                    #checking if path exists (and making it if not)
                    ensure_dir(write_dir) 
                    if ".jpg" in i:
                        # adding filename to write path
                        write_dir=write_dir+"/"+i.split('/')[-1] 
                    else:
                    # adding 'mp4' extension to movies and removing leading '?'
                        filename=str(i.split('/')[-1])
                        write_dir=write_dir+"/"+filename[1:]+".mp4" 
                    # check if file exists
                    if not does_file_exist(write_dir):
                        time.sleep(1)  #rate limiting
                        urllib.request.urlretrieve(i, write_dir) #downloading
                        # num_images+=len(img_list)
                        num_images+=1
                    else:
                        print ('file already downloaded')
                        
            else:
                pass 
            messages_retrieved+=1
        except Exception as e:
            print ("Unexpected error:", sys.exc_info()[0])
            print ("Unexpected error:", sys.exc_info()[1])
            print ("Unexpected error:", sys.exc_info()[2])
        except:
            pass    
    
        #### This will mark the messages as read. when testing is complete
        GMAIL.users().messages().modify(userId='me', 
            id=m_id,body={ 'removeLabelIds': ['UNREAD']}).execute() 
        
    
    print ("Total messages retrieved: ", messages_retrieved)
    print ("Total images retrieved: ", num_images)

if __name__ == "__main__":
    interval=60
    next_run=datetime.datetime.now()
    while True:
        if (datetime.datetime.now()>=next_run):
            # reset the timer
            next_run=datetime.datetime.now()+(datetime.timedelta(seconds=interval))
            # run the scraper
            try:
                main()
            except Exception as e:         
                print (e)
            # update the user
            print ('sleeping for {}s. Next run is at {}'.format(interval,next_run))

            