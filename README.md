Hey everyone, 

I've been looking for an alternative to Readarr that would be easier for my users to use to grab audiobooks and haven't found anything too promising so I threw together a simple web app to download book from AudioBook Bay via qBitTorrent. 

The app displays search results from AudioBook Bay with the option to view details or download to the server. If a download is chosen the infohash is turned into a magnet link and sent to qBitTorrent. 
In my setup the /audiobooks folder in my qBitTorrent container is mapped to the root folder of my Audiobookshelf library. You can set your SAVE_PATH_BASE value anywhere you'd like, subfolders with the book title will be created automatically. This path is relevant to wherever you have qBitTorrent running. 
You can run app.py by itself or build the docker container. In the beginning of the app.py script there are values to change for your setup. 

This is very sloppy and just thrown together on a whim, down the line I'm going to clean this up and get rid of the bad practices but for now I wanted to share what I threw together this afternoon in case others were interested and collect feedback. 
