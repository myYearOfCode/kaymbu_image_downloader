'''
KAYMBU image downloader by myYearOfCode
https://github.com/myYearOfCode/kaymbu_image_downloader
Based off of "Reading GMAIL using Python" - Abhishek Chhibber
'''

'''
This script does the following:
- Go to Gmail inbox. I set up a specific address just for this. My main 
     email address forwards based on a filter.
- Find and read all the unread messages
- Filter based on subject search term
- Find url of download page in email
- Visit url and grab image urls
- Download image urls (rate limit 1 req/s to be polite)
- Save images into dated folders based on email sent date
- Mark the messages as Read - so that they are not read again 

This script could do this in the future:
- build antifragility with beautifulSoup or something similar
- allow filter tweaking without having to get deep into the code.
- add mov/other format download options (currently crashes on these)
'''

'''
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
import sys
import os
import json
import time

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

def harvest_images(mystr):
    '''
    this searches through the page for the string "_thumb" indicating a 
    thumbnail size image. It trims the "_thumb" and adds it to a list. 
    Eventually it returns the list.
    '''

    images=[]
    offset=0
    link_thumb=0
    
    # how to deal with videos?
    while link_thumb!=-1:
        try:
            #find the next image thumbnail link
            link_thumb=mystr.find('_thumb',offset)
            # print (link_thumb)
            if link_thumb>0: #while the find() is still finding
                # reverse find to start at 'https'
                start_of_link=mystr.rfind('https',0,link_thumb)
                # build link and add extension
                image_link=(mystr[start_of_link:link_thumb]+".jpg")
                # add it to the images list
                images.append(image_link)
                # update offset for next search
                offset=link_thumb+6
        except:
            return images
    return images

def process_email(input):
    """ 
    this scans the email for the download link and passes it to the 
    harvest_images function. I have seen two formats of email come through. 
    I believe they are based on how they have been forwarded.
    Gmail native "filter" forwards come across as single part html/data while
    manual forwards come across as multipart.
    """
    # process as solo html mimetype
    #find the first download link
    dl_index=(input.find('class="download"')) 
    # find the opening quote
    open_bracket = (input[dl_index:].find('"')+20)
    # find the closing quote
    close_bracket = (input[dl_index+open_bracket:].find('"'))
    # build the url
    scraped_url = (input[open_bracket+dl_index:close_bracket+dl_index+open_bracket])        

    if scraped_url=="": #scrape error or the message is dual mimetype format
        print('trying multipart processing')
        #find the first download link
        dl_index=(input.find('Download this moment]'))
        # find the opening bracket
        open_bracket = (input[dl_index:].find('<')+1)
        # find the closing bracket
        close_bracket = (input[dl_index:].find('>'))
        # build the url
        scraped_url = (input[open_bracket+dl_index:close_bracket+dl_index])

        
    # scrape the url
    fp = urllib.request.urlopen(scraped_url)
    #read bytes
    mybytes = fp.read()
    mystr = mybytes.decode("utf8")
    fp.close()
    # pass it off to the image scraper function
    return (harvest_images(mystr)) 


def main():
        
    # Creating a storage.JSON file with authentication details
    # we are using modify and not readonly, as we will be marking the messages Read    
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
        sys.exit()    
    
    #main loop through the new messages list
    for i,mssg in enumerate(mssg_list):
        temp_dict = { }
        print("processing message {} of {}".format(i+1,len(mssg_list)))
        m_id = mssg['id'] # get id of individual message
        # fetch the message using API
        message = GMAIL.users().messages().get(userId='me', id=m_id).execute() 
        payld = message['payload'] # get payload of the message 
        header = payld['headers'] # get header of the payload
    
        for one in header: # getting the Subject
            if one['name'] == 'Subject':
                msg_subject = one['value']
                temp_dict['Subject'] = msg_subject
            else:
                pass
    
        for two in header: # getting the date
            if two['name'] == 'Date':
                msg_date = two['value']
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
                mssg_parts = payld['parts']
                part_one  = mssg_parts[0] # fetching first element of the part 
                part_body = part_one['body'] # fetching body of the message
                part_data = part_body['data'] # fetching data from the body
            
            # decoding from Base64 to UTF-8
            clean_one = part_data.replace("-","+") 
            clean_one = clean_one.replace("_","/")
            clean_two = base64.b64decode (bytes(clean_one, 'UTF-8')) 
            # /decoding from Base64 to UTF-8
            
            for one in header: # getting the Subject
                if one['name'] == 'Subject' and search_term in one['value']:
                    try:
                        img_list= (process_email(clean_two.decode("utf8"))) 
                        print ('{} images found.'.format(len(img_list)))
                        num_images+=len(img_list)
                        for i in (img_list):
                            print ("downloading: " +i.split('/')[-1])
                            #adding the email date to filepath
                            write_dir=save_dir+temp_dict['Date']+'/'
                            #checking if path exists (and making it if not)
                            ensure_dir(write_dir) 
                            # adding filename to write path
                            write_dir=write_dir+"/"+i.split('/')[-1] 
                            # check if file has already been downloaded
                            if not does_file_exist(write_dir):
                                #rate limiting
                                time.sleep(1)
                                #downloading image
                                urllib.request.urlretrieve(i, write_dir) 
                            else:
                                print ('file already downloaded')
                    except Exception as e:
                        print ("Unexpected error:", sys.exc_info()[0])
                        print ("Unexpected error:", sys.exc_info()[1])
                        print ("Unexpected error:", sys.exc_info()[2])
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        print(exc_type, fname, exc_tb.tb_lineno)                                
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
    main()
