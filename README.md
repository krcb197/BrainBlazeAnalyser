# BrainBlazeAnalyser
Python Library for Analysing statistics from the [Brain Blaze YouTube Channel](https://youtube.com/channel/UCYY5GWf7MHFJ6DZeHreoXgw)

# Installing

In order to use this do the following:
* Install Python, I have tested this with 3.9.7
* Copy the files from this GitHub repository
* Install the required packages: 
  ```bash
  pip install -r requirements.txt
  ```
* Get a Google API key and store it in a file called ``.google_API_key``, if you are unfamilar with the process, look here: [YouTube Data API Overview](https://developers.google.com/youtube/v3/getting-started) 

# Running
Run the file 
```bash
python BlazeAnalyser.py
```
This will create a file call ``BrainBlazeAnalysis.png`` similar to the one below:
![Example Results](BrainBlazeAnalysis.png)

Alternatively
```bash
python BrainBlazeInfoGraphic.py
```
This will create the summary often I post to twitter: <img width="800" alt="image" src="https://user-images.githubusercontent.com/34693973/143104150-cbdea592-789d-45ac-a4ff-acc8d9eef2d8.png">


