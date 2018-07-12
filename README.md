# kaymbu_image_downloader
This script grabs a url from a kaymbu image sharing email (from gmail), visits the image site, scrapes it for full res image links and then downloads them.


KAYMBU image downloader by myYearOfCode

Based off of "Reading GMAIL using Python" - Abhishek Chhibber
https://github.com/abhishekchhibber/Gmail-Api-through-Python


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


Before running this script, the user should get the authentication by following 
the link: https://developers.google.com/gmail/api/quickstart/python
Also, client_secret.json should be saved in the same directory as this file.
Lastly, the preferences.json file needs to be filled out with your 'search_term'
and 'save_dir' values

