# API - Documentation

# Real-Debrid API Documentation

## Implementation details

- Methods are grouped by namespaces (e.g. "unrestrict", "user").
- Supported HTTP verbs are GET, POST, PUT, and DELETE. If your client does not support all HTTP verbs you can overide the verb with X-HTTP-Verb HTTP header.
- Unless specified otherwise in the method's documentation, all successful API calls return HTTP code 200 with a JSON object.
- Errors are returned with HTTP code 4XX or 5XX, a JSON object with properties "error" (an error message) and "error_code" (optional, an integer).
- Every string passed to and from the API needs to be UTF-8 encoded. For maximum compatibility, normalize to Unicode Normalization Form C (NFC) before UTF-8 encoding.
- The API sends ETag headers and supports the If-None-Match header.
- Dates are formatted according to the Javascript method date.toJSON .
- Unless specified otherwise, all API methods require authentication.
- The API is limited to 250 requests per minute , all refused requests will return HTTP 429 error and will count in the limit (bruteforcing will leave you blocked for undefined amount of time)
## API methods

The Base URL of the Rest API is:

```json
https://api.real-debrid.com/rest/1.0/
```

#### GET /disable_access_token

Disable current access token, returns 204 HTTP code

##### Return value:

None

##### Possible HTTP error codes:

#### GET /time

Get server time, raw data returned. This request is not requiring authentication.

##### Return value:

Y-m-d H:i:s

#### GET /time/iso

Get server time in ISO, raw data returned. This request is not requiring authentication.

##### Return value:

Y-m-dTH:i:sO

### /user

#### GET /user

Returns some informations on the current user.

##### Return value:

User show schema

##### Possible HTTP error codes:

### /unrestrict

#### POST /unrestrict/check

Check if a file is downloadable on the concerned hoster. This request is not requiring authentication.

##### Parameters:

##### Return value:

show schema

##### Possible HTTP error codes:

#### POST /unrestrict/link

Unrestrict a hoster link and get a new unrestricted link

##### Parameters:

##### Return value for a unique generated link:

show schema

##### Return value for multiple generated links (ex Youtube):

show schema

##### Possible HTTP error codes:

#### POST /unrestrict/folder

Unrestrict a hoster folder link and get individual links, returns an empty array if no links found.

##### Parameters:

##### Return value:

show schema

##### Possible HTTP error codes:

#### PUT /unrestrict/containerFile

##### Return value:

show schema

##### Possible HTTP error codes:

#### POST /unrestrict/containerLink

##### Parameters:

##### Return value:

show schema

##### Possible HTTP error codes:

### /traffic

#### GET /traffic

Get traffic informations for limited hosters (limits, current usage, extra packages)

##### Return value:

show schema

##### Possible HTTP error codes:

#### GET /traffic/details

Get traffic details on each hoster used during a defined period

##### Parameters:

Warning: The period can not exceed 31 days.

##### Return value:

show schema

##### Possible HTTP error codes:

### /streaming

#### GET /streaming/transcode/{id}

Get transcoding links for given file, {id} from /downloads or /unrestrict/link

##### Return value:

show schema

##### Possible HTTP error codes:

#### GET /streaming/mediaInfos/{id}

Get detailled media informations for given file, {id} from /downloads or /unrestrict/link

##### Return value:

show schema

##### Possible HTTP error codes:

### /downloads

#### GET /downloads

Get user downloads list

##### Parameters:

Warning: You can not use both offset and page at the same time, page is prioritzed in case it happens.

##### Return value:

show schema

##### Possible HTTP error codes:

#### DELETE /downloads/delete/{id}

Delete a link from downloads list, returns 204 HTTP code

##### Return value:

None

##### Possible HTTP error codes:

### /torrents

#### GET /torrents

Get user torrents list

##### Parameters:

Warning: You can not use both offset and page at the same time, page is prioritzed in case it happens.

##### Return value:

show schema

##### Possible HTTP error codes:

#### GET /torrents/info/{id}

Get all informations on the asked torrent

##### Return value:

show schema

##### Possible HTTP error codes:

#### GET /torrents/activeCount

Get currently active torrents number and the current maximum limit

##### Return value:

show schema

##### Possible HTTP error codes:

#### GET /torrents/availableHosts

Get available hosts to upload the torrent to.

##### Return value:

show schema

##### Possible HTTP error codes:

#### PUT /torrents/addTorrent

##### Parameters:

##### Return value:

show schema

```json
{
    
"id"
: 
"string"
,
    
"uri"
: 
"string" 
// URL of the created ressource

}
```

##### Possible HTTP error codes:

#### POST /torrents/addMagnet

##### Parameters:

##### Return value:

show schema

##### Possible HTTP error codes:

#### POST /torrents/selectFiles/{id}

##### Parameters:

Warning: To get file IDs, use /torrents/info/{id}

##### Return value:

None

##### Possible HTTP error codes:

#### DELETE /torrents/delete/{id}

Delete a torrent from torrents list, returns 204 HTTP code

##### Return value:

None

##### Possible HTTP error codes:

### /hosts

#### GET /hosts

Get supported hosts. This request is not requiring authentication.

##### Return value:

show schema

#### GET /hosts/status

Get status of supported hosters or not and their status on competitors.

##### Return value:

show schema

#### GET /hosts/regex

Get all supported links Regex, useful to find supported links inside a document. This request is not requiring authentication.

##### Return value:

show schema

#### GET /hosts/regexFolder

Get all supported folder Regex, useful to find supported links inside a document. This request is not requiring authentication.

##### Return value:

show schema

#### GET /hosts/domains

Get all hoster domains supported on the service. This request is not requiring authentication.

##### Return value:

show schema

### /settings

#### GET /settings

Get current user settings with possible values to update.

##### Return value:

show schema

##### Possible HTTP error codes:

#### POST /settings/update

##### Parameters:

##### Return value:

None

##### Possible HTTP error codes:

#### POST /settings/convertPoints

##### Return value:

None

##### Possible HTTP error codes:

#### POST /settings/changePassword

##### Return value:

None

##### Possible HTTP error codes:

#### PUT /settings/avatarFile

##### Return value:

None

##### Possible HTTP error codes:

#### DELETE /settings/avatarDelete

Reset user avatar image to default, returns 204 HTTP code

##### Return value:

None

##### Possible HTTP error codes:

### /support

```json
{
    
"id"
: 
int
,
    
"username"
: 
"string"
,
    
"email"
: 
"string"
,
    
"points"
: 
int
, 
// Fidelity points
    
"locale"
: 
"string"
, 
// User language
    
"avatar"
: 
"string"
, 
// URL
    
"type"
: 
"string"
, 
// "premium" or "free"
    
"premium"
: 
int
, 
// seconds left as a Premium user
    
"expiration"
: 
"string" 
// jsonDate

}
```

```json
{
    
"id"
: 
"string"
,
    
"filename"
: 
"string"
,
    
"mimeType"
: 
"string"
, 
// Mime Type of the file, guessed by the file extension
    
"filesize"
: 
int
, 
// Filesize in bytes, 0 if unknown
    
"link"
: 
"string"
, 
// Original link
    
"host"
: 
"string"
, 
// Host main domain
    
"chunks"
: 
int
, 
// Max Chunks allowed
    
"crc"
: 
int
, 
// Disable / enable CRC check 
    
"download"
: 
"string"
, 
// Generated link
    
"streamable"
: 
int 
// Is the file streamable on website

}
```

```json
{
    
"id"
: 
"string"
,
    
"filename"
: 
"string"
,
    
"filesize"
: 
int
, 
// Filesize in bytes, 0 if unknown
    
"link"
: 
"string"
, 
// Original link
    
"host"
: 
"string"
, 
// Host main domain
    
"chunks"
: 
int
, 
// Max Chunks allowed
    
"crc"
: 
int
, 
// Disable / enable CRC check 
    
"download"
: 
"string"
, 
// Generated link
    
"streamable"
: 
int
, 
// Is the file streamable on website
    
"type"
: 
"string"
, 
// Type of the file (in general, its quality)
    
"alternative"
: [
        {
            
"id"
: 
"string"
,
            
"filename"
: 
"string"
,
            
"download"
: 
"string"
,
            
"type"
: 
"string"
        
},
        {
            
"id"
: 
"string"
,
            
"filename"
: 
"string"
,
            
"download"
: 
"string"
,
            
"type"
: 
"string"
        
}
    ]
}
```

```json
[
    {
        
"id"
: 
"string"
,
        
"filename"
: 
"string"
,
        
"mimeType"
: 
"string"
, 
// Mime Type of the file, guessed by the file extension
        
"filesize"
: 
int
, 
// bytes, 0 if unknown
        
"link"
: 
"string"
, 
// Original link
        
"host"
: 
"string"
, 
// Host main domain
        
"chunks"
: 
int
, 
// Max Chunks allowed
        
"download"
: 
"string"
, 
// Generated link
        
"generated"
: 
"string" 
// jsonDate
    
},
    {
        
"id"
: 
"string"
,
        
"filename"
: 
"string"
,
        
"mimeType"
: 
"string"
,
        
"filesize"
: 
int
,
        
"link"
: 
"string"
,
        
"host"
: 
"string"
,
        
"chunks"
: 
int
,
        
"download"
: 
"string"
,
        
"generated"
: 
"string"
,
        
"type"
: 
"string" 
// Type of the file (in general, its quality)
    
}
]
```

```json
{
    
"string"
: { 
// Host main domain
        
"left"
: 
int
, 
// Available bytes / links to use
        
"bytes"
: 
int
, 
// Bytes downloaded
        
"links"
: 
int
, 
// Links unrestricted
        
"limit"
: 
int
,
        
"type"
: 
"string"
, 
// "links", "gigabytes", "bytes"
        
"extra"
: 
int
, 
// Additional traffic / links the user may have buy
        
"reset"
: 
"string" 
// "daily", "weekly" or "monthly"
    
},
    
"string"
: {
        
"left"
: 
int
,
        
"bytes"
: 
int
,
        
"links"
: 
int
,
        
"limit"
: 
int
,
        
"type"
: 
"string"
,
        
"extra"
: 
int
,
        
"reset"
: 
"string"
    
}
}
```

```json
{
    
"YYYY-MM-DD"
: {
        
"host"
: { 
// By Host main domain
            
"string"
: 
int
, 
// bytes downloaded on concerned host
            
"string"
: 
int
,
            
"string"
: 
int
,
            
"string"
: 
int
,
            
"string"
: 
int
,
            
"string"
: 
int
        
},
        
"bytes"
: 
int 
// Total downloaded (in bytes) this day
    
},
    
"YYYY-MM-DD"
: {
        
"host"
: {
            
"string"
: 
int
,
            
"string"
: 
int
,
            
"string"
: 
int
,
            
"string"
: 
int
,
            
"string"
: 
int
,
        },
        
"bytes"
: 
int
    
}
}
```

```json
[
    {
        
"id"
: 
"string"
,
        
"filename"
: 
"string"
,
        
"hash"
: 
"string"
, 
// SHA1 Hash of the torrent
        
"bytes"
: 
int
, 
// Size of selected files only
        
"host"
: 
"string"
, 
// Host main domain
        
"split"
: 
int
, 
// Split size of links
        
"progress"
: 
int
, 
// Possible values: 0 to 100
        
"status"
: 
"downloaded"
, 
// Current status of the torrent: magnet_error, magnet_conversion, waiting_files_selection, queued, downloading, downloaded, error, virus, compressing, uploading, dead
        
"added"
: 
"string"
, 
// jsonDate
        
"links"
: [
            
"string" 
// Host URL
        
],
        
"ended"
: 
"string"
, 
// !! Only present when finished, jsonDate
        
"speed"
: 
int
, 
// !! Only present in "downloading", "compressing", "uploading" status
        
"seeders"
: 
int 
// !! Only present in "downloading", "magnet_conversion" status
    
},
    {
        
"id"
: 
"string"
,
        
"filename"
: 
"string"
,
        
"hash"
: 
"string"
,
        
"bytes"
: 
int
,
        
"host"
: 
"string"
,
        
"split"
: 
int
,
        
"progress"
: 
int
,
        
"status"
: 
"downloaded"
,
        
"added"
: 
"string"
,
        
"links"
: [
            
"string"
,
            
"string"
        
],
        
"ended"
: 
"string"
    
},
]
```

```json
[
    {
        
"id"
: 
"string"
,
        
"filename"
: 
"string"
,
        
"original_filename"
: 
"string"
, 
// Original name of the torrent
        
"hash"
: 
"string"
, 
// SHA1 Hash of the torrent
        
"bytes"
: 
int
, 
// Size of selected files only
        
"original_bytes"
: 
int
, 
// Total size of the torrent
        
"host"
: 
"string"
, 
// Host main domain
        
"split"
: 
int
, 
// Split size of links
        
"progress"
: 
int
, 
// Possible values: 0 to 100
        
"status"
: 
"downloaded"
, 
// Current status of the torrent: magnet_error, magnet_conversion, waiting_files_selection, queued, downloading, downloaded, error, virus, compressing, uploading, dead
        
"added"
: 
"string"
, 
// jsonDate
        
"files"
: [
            {
                
"id"
: 
int
,
                
"path"
: 
"string"
, 
// Path to the file inside the torrent, starting with "/"
                
"bytes"
: 
int
,
                
"selected"
: 
int 
// 0 or 1
            
},
            {
                
"id"
: 
int
,
                
"path"
: 
"string"
, 
// Path to the file inside the torrent, starting with "/"
                
"bytes"
: 
int
,
                
"selected"
: 
int 
// 0 or 1
            
}
        ],
        
"links"
: [
            
"string" 
// Host URL
        
],
        
"ended"
: 
"string"
, 
// !! Only present when finished, jsonDate
        
"speed"
: 
int
, 
// !! Only present in "downloading", "compressing", "uploading" status
        
"seeders"
: 
int 
// !! Only present in "downloading", "magnet_conversion" status
    
}
]
```

```json
{
    
"id"
: 
"string"
,
    
"uri"
: 
"string" 
// URL of the created ressource

}
```

```json
{
    
"id"
: 
"string"
,
    
"uri"
: 
"string" 
// URL of the created ressource

}
```

```json
[
    {
        
"host"
: 
"string"
, 
// Host main domain
        
"max_file_size"
: 
int 
// Max split size possible
    
},
    {
        
"host"
: 
"string"
, 
// Host main domain
        
"max_file_size"
: 
int 
// Max split size possible
    
}
]
```

```json
{
    
"string"
: { 
// First hash
        
"string"
: [ 
// hoster, ex: "rd"
            // All file IDs variants
            
{
                
"int"
: { 
// file ID, you must ask all file IDs from this array on /selectFiles to get instant downloading
                    
"filename"
: 
"string"
,
                    
"filesize"
: 
int
                
},
                
"int"
: { 
// file ID
                    
"filename"
: 
"string"
,
                    
"filesize"
: 
int
                
}
            },
            {
                
"int"
: { 
// file ID
                    
"filename"
: 
"string"
,
                    
"filesize"
: 
int
                
}
            }
        ]
    },
    
"string"
: { 
// Second hash
        
"string"
: [ 
// hoster, ex: "rd"
            // All file IDs variants
            
{
                
"int"
: { 
// file ID, you must ask all file IDs from this array on /selectFiles to get instant downloading
                    
"filename"
: 
"string"
,
                    
"filesize"
: 
int
                
},
                
"int"
: { 
// file ID
                    
"filename"
: 
"string"
,
                    
"filesize"
: 
int
                
}
            },
            {
                
"int"
: { 
// file ID
                    
"filename"
: 
"string"
,
                    
"filesize"
: 
int
                
}
            }
        ]
    }
}
```

```json
{
    
"nb"
: 
int
, 
// Number of currently active torrents
    
"limit"
: 
int 
// Maximum number of active torrents you can have

}
```

```json
[
    
"string"
, 
// URL
    
"string"
,
    
"string"

]
```

```json
[
    
"string"
, 
// URL
    
"string"
,
    
"string"

]
```

```json
[
    
"string"
, 
// Domain
    
"string"
,
    
"string"

]
```

```json
[
    
"string"
, 
// RegExp
    
"string"
,
    
"string"

]
```

```json
{
    
"string"
: { 
// Host main domain
        
"id"
: 
"string"
,
        
"name"
: 
"string"
,
        
"image"
: 
"string" 
// URL
    
},
    
"string"
: {
        
"id"
: 
"string"
,
        
"name"
: 
"string"
,
        
"image"
: 
"string"
    
}
}
```

```json
{
    
"string"
: { 
// Host main domain
        
"id"
: 
"string"
,
        
"name"
: 
"string"
,
        
"image"
: 
"string"
, 
// URL
        
"supported"
: 
int
, 
// 0 or 1
        
"status"
: 
"string"
, 
// "up" / "down" / "unsupported"
        
"check_time"
: 
"string"
, 
// jsonDate
        
"competitors_status"
: {
            
"string"
: { 
// Competitor domain
                
"status"
: 
"string"
, 
// "up" / "down" / "unsupported"
                
"check_time"
: 
"string" 
// jsonDate
            
},
            
"string"
: {
                
"status"
: 
"string"
,
                
"check_time"
: 
"string"
            
},
            
"string"
: {
                
"status"
: 
"string"
,
                
"check_time"
: 
"string"
            
}
        }
    },
    
"string"
: {
        
"id"
: 
"string"
,
        
"name"
: 
"string"
,
        
"image"
: 
"string"
,
        
"supported"
: 
int
,
        
"status"
: 
"string"
,
        
"check_time"
: 
"string"
,
        
"competitors_status"
: {
            
"string"
: {
                
"status"
: 
"string"
,
                
"check_time"
: 
"string"
            
},
            
"string"
: {
                
"status"
: 
"string"
,
                
"check_time"
: 
"string"
            
},
            
"string"
: {
                
"status"
: 
"string"
,
                
"check_time"
: 
"string"
            
}
        }
    }
}
```

```json
{
    
"string"
: [ 
// Category name
        
{
            
"id"
: 
int
, 
// Forum ID
            
"name"
: 
"string"
, 
// Forum name
            
"description"
: 
"string"
, 
// Forum description
            
"topics"
: 
int
, 
// Number of topics inside the concerned forum
            
"posts"
: 
int
, 
// Number of posts inside the concerned forum
            
"unread_content"
: 
int
, 
// 0 or 1
            
"last_post"
: { 
// Last post details
                
"id"
: 
int
,
                
"topic_id"
: 
int
,
                
"user_id"
: 
int
,
                
"user_name"
: 
"string"
,
                
"user_level"
: 
"string"
, 
// "user", "banned", "moderator", "administrator"
                
"date"
: 
"string" 
// jsonDate
            
}
        },
        {
            
"id"
: 
int
,
            
"name"
: 
"string"
,
            
"description"
: 
"string"
,
            
"topics"
: 
int
,
            
"posts"
: 
int
,
            
"unread_content"
: 
int
,
            
"last_post"
: {
                
"id"
: 
int
,
                
"topic_id"
: 
int
,
                
"user_id"
: 
int
,
                
"user_name"
: 
"string"
,
                
"user_level"
: 
"string"
,
                
"date"
: 
"string"
            
}
        }
    ],
    
"string"
: [
        {
            
"id"
: 
int
,
            
"name"
: 
"string"
,
            
"description"
: 
"string"
,
            
"topics"
: 
int
,
            
"posts"
: 
int
,
            
"unread_content"
: 
int
,
            
"last_post"
: {
                
"id"
: 
int
,
                
"topic_id"
: 
int
,
                
"user_id"
: 
int
,
                
"user_name"
: 
"string"
,
                
"user_level"
: 
"string"
,
                
"date"
: 
"string"
            
}
        },
        {
            
"id"
: 
int
,
            
"name"
: 
"string"
,
            
"description"
: 
"string"
,
            
"topics"
: 
int
,
            
"posts"
: 
int
,
            
"unread_content"
: 
int
,
            
"last_post"
: {
                
"id"
: 
int
,
                
"topic_id"
: 
int
,
                
"user_id"
: 
int
,
                
"user_name"
: 
"string"
,
                
"user_level"
: 
"string"
,
                
"date"
: 
"string"
            
}
        }
    ]
}
```

```json
{
    
"host"
: 
"string"
, 
// Host main domain
    
"link"
: 
"string"
,
    
"filename"
: 
"string"
,
    
"filesize"
: 
int
,
    
"supported"
: 
int

}
```

```json
{
    
"apple"
: { 
// M3U8 Live Streaming format
        
"quality"
: 
"string"
,
        
"quality"
: 
"string"
    
},
    
"dash"
: { 
// MPD Live Streaming format
        
"quality"
: 
"string"
,
        
"quality"
: 
"string"
    
},
    
"liveMP4"
: { 
// Live MP4
        
"quality"
: 
"string"
,
        
"quality"
: 
"string"
    
},
    
"h264WebM"
: { 
// Live H264 WebM
        
"quality"
: 
"string"
,
        
"quality"
: 
"string"
    
}
}
```

```json
{
    
"filename"
: 
"string"
, 
// Cleaned filename
    
"hoster"
: 
"string"
, 
// File hosted on
    
"link"
: 
"string"
, 
// Original content link
    
"type"
: 
"string"
, 
// "movie" / "show" / "audio"
    
"season"
: 
"string"
, 
// if found, else null
    
"episode"
: 
"string"
, 
// if found, else null
    
"year"
: 
"string"
, 
// if found, else null
    
"duration"
: 
float
, 
// media duration in seconds
    
"bitrate"
: 
int
, 
// birate of the media file
    
"size"
: 
int
, 
// original filesize in bytes
    
"details"
: {
        
"video"
: {
            
"und1"
: { 
// if available, lang in iso_639 followed by a number ID
                
"stream"
: 
"string"
,
                
"lang"
: 
"string"
, 
// Language in plain text (ex "English", "French")
                
"lang_iso"
: 
"string"
, 
// Language in iso_639 (ex fre, eng)
                
"codec"
: 
"string"
, 
// Codec of the video (ex "h264", "divx")
                
"colorspace"
: 
"string"
, 
// Colorspace of the video (ex "yuv420p")
                
"width"
: 
int
, 
// Width of the video (ex 1980)
                
"height"
: 
int 
// Height of the video (ex 1080)
            
}
        },
        
"audio"
: {
            
"und1"
: { 
// if available, lang in iso_639 followed by a number ID
                
"stream"
: 
"string"
,
                
"lang"
: 
"string"
, 
// Language in plain text (ex "English", "French")
                
"lang_iso"
: 
"string"
, 
// Language in iso_639 (ex fre, eng)
                
"codec"
: 
"string"
, 
// Codec of the audio (ex "aac", "mp3")
                
"sampling"
: 
int
, 
// Audio sampling rate
                
"channels"
: 
float 
// Number of channels (ex 2, 5.1, 7.1)
            
}
        },
        
"subtitles"
: [
            
"und1"
: { 
// if available, lang in iso_639 followed by a number ID
                
"stream"
: 
"string"
,
                
"lang"
: 
"string"
, 
// Language in plain text (ex English, French)
                
"lang_iso"
: 
"string"
, 
// Language in iso_639 (ex fre, eng)
                
"type"
: 
"string" 
// Format of subtitles (ex "ASS" / "SRT")
            
}
        ]
    },
    
"poster_path"
: 
"string"
, 
// URL of the poster image if found / available
    
"audio_image"
: 
"string"
, 
// URL of the music image in HD if found / available
    
"backdrop_path"
: 
"string" 
// URL of the backdrop image if found / available

}
```

```json
{
    
"download_ports"
: [ 
// Possible "download_port" value to update settings
        
"string"
,
        
"string"
    
],
    
"download_port"
: 
"string"
, 
// Current user download port
    
"locales"
: { 
// Possible "locale" value to update settings
        
"string"
: 
"string"
,
        
"string"
: 
"string"
    
},
    
"locale"
: 
"string"
, 
// Current user locale
    
"streaming_qualities"
: [ 
// Possible "streaming_quality" value to update settings
        
"string"
,
        
"string"
,
        
"string"
,
        
"string"
    
],
    
"streaming_quality"
: 
"string"
, 
// Current user streaming quality
    
"mobile_streaming_quality"
: 
"string"
, 
// Current user streaming quality on mobile devices
    
"streaming_languages"
: { 
// Possible "streaming_language_preference" value to update settings
        
"string"
: 
"string"
,
        
"string"
: 
"string"
    
},
    
"streaming_language_preference"
: 
"string"
, 
// Current user streaming language preference
    
"streaming_cast_audio"
: [ 
// Possible "streaming_cast_audio_preference" value to update settings
        
"string"
,
        
"string"
    
],
    
"streaming_cast_audio_preference"
: 
"string" 
// Current user audio preference on Google Cast devices

}
```

```json
{
    
"meta"
: {
        
"id"
: 
int
,
        
"name"
: 
"string"
,
        
"description"
: 
"string"
,
        
"topics"
: 
int
,
        
"autorisation_topic"
: 
int
, 
// User allowed to make a new topic: 0 or 1
        
"autorisation_post"
: 
int
, 
// User allowed to post in a topic: 0 or 1
        
"autorisation_stick"
: 
int
, 
// User allowed to stick a topic: 0 or 1
        
"autorisation_moderation"
: 
int
, 
// User allowed to use moderation tools: 0 or 1
    
},
    
"topics"
: {
        
"string"
: [ 
// "normal" or "sticky"
            
{
                
"id"
: 
int
,
                
"title"
: 
"string"
,
                
"author"
: {
                    
"user_id"
: 
int
,
                    
"username"
: 
"string"
,
                    
"level"
: 
"string"
                
},
                
"posts"
: 
int
,
                
"views"
: 
int
,
                
"unread_content"
: 
int
,
                
"last_post"
: {
                    
"id"
: 
int
,
                    
"user_id"
: 
int
,
                    
"user_name"
: 
"string"
,
                    
"user_level"
: 
"string"
,
                    
"date"
: 
"string"
                
}
            },
            {
                
"id"
: 
int
,
                
"title"
: 
"string"
,
                
"author_user_id"
: 
int
,
                
"author_user_name"
: 
"string"
,
                
"posts"
: 
int
,
                
"views"
: 
int
,
                
"unread_content"
: 
int
,
                
"last_post"
: {
                    
"id"
: 
int
,
                    
"user_id"
: 
int
,
                    
"user_name"
: 
"string"
,
                    
"user_level"
: 
"string"
,
                    
"date"
: 
"string"
                
}
            }
        ]
    }
}
```

## Example calls

Here are some example calls, using cURL :

#### Getting user informations:

Show/hide example

```json
curl -X GET \
     -H "Authorization: Bearer your_api_token" \
     "https://api.real-debrid.com/rest/1.0/
user
"
```

```json
HTTP/1.1 200 OK
Content-Type: application/json
etag: fd6e5a758cf66fe4e92bc2bc7061d9f32dc542af
date: Fri, 12 Jul 2013 12:12:12 GMT


{
    
"id"
: 
42
,
    
"username"
: 
"administrator"
,
    
"email"
: 
"support@real-debrid.com"
,
    
"points"
: 
12347428
,
    
"avatar"
: 
"https:\/\/s.real-debrid.com\/images\/avatars\/42424242424.png"
,
    
"type"
: 
"premium"
,
    
"premium"
: 
666666
,
    
"expiration"
: 
"2032-06-06T04:42:42.000Z"

}
```

## Authentication

Calls that require authentication expect an HTTP header Authorization bearing a token, using the following format:

```json
Authorization: Bearer 
your_api_token
```

If you can not send an Authorization HTTP header you can also send your token as a parameter in REST API URLs, the parameter is called auth_token :

```json
/rest/1.0/method?auth_token=
your_api_token
```

This token can either be your private API token , or a token obtained using OAuth2's three-legged authentication.

Warning: Never ever use your private API token for public applications, it is insecure and gives access to all methods.

## Authentication for applications

First, you must create an app in your control panel.

Once you have created an app, you are provided a client_id and client_secret that you will use for the authentication process.

## Opensource Apps

You can use this client ID on opensource apps if you don't need custom scopes or name:

```json
X245A4XAIBGVM
```

This app is allowed on following scopes: unrestrict, torrents, downloads, user

This client ID can have stricter limits than service limits due to poorly designed apps using it.

### Which authentication process should you use?

- If your application is a website: three-legged OAuth2 .
- If your application is a mobile app: OAuth2 for devices .
- If your application is an opensource app or a script: OAuth2 for opensource apps .
The Base URL of the OAuth2 API is:

```json
https://api.real-debrid.com/oauth/v2/
```

### Workflow for websites or client applications

This authentication process uses three-legged OAuth2.

The following URLs are used in this process:

- authorize endpoint: /auth
- token endpoint: /token
Note: if your application is not a website, you will have to make the user do these steps in a web view (e.g. UIWebView on iOS, WebView on Android…).

#### Full workflow

- Your application redirects the user to Online.net's authorize endpoint, with the following query string parameters: client_id : your app's client_id redirect_uri : one of your application's redirect URLs (must be url encoded ) response_type : use the value "code" state : an arbitrary string that will be returned to your application, to help you check against CSRF Example URL for authorization: https://api.real-debrid.com/oauth/v2/auth? client_id =ABCDEFGHIJKLM& redirect_uri =https%3A%2F%2Fexample.com& response_type =code& state =iloverd
Your application redirects the user to Online.net's authorize endpoint, with the following query string parameters:

- client_id : your app's client_id
- redirect_uri : one of your application's redirect URLs (must be url encoded )
- response_type : use the value "code"
- state : an arbitrary string that will be returned to your application, to help you check against CSRF
##### Example URL for authorization:

```json
https://api.real-debrid.com/oauth/v2/auth?
client_id
=ABCDEFGHIJKLM&
redirect_uri
=https%3A%2F%2Fexample.com&
response_type
=code&
state
=iloverd
```

- The user chooses to authorize your application.
The user chooses to authorize your application.

- The user gets redirected to the URL you specified using the parameter redirect_uri , with the following query string parameters: code : the code that you will use to get a token state : the same value that you sent earlier
The user gets redirected to the URL you specified using the parameter redirect_uri , with the following query string parameters:

- code : the code that you will use to get a token
- state : the same value that you sent earlier
- Using the value of code , your application makes a direct POST request (not in the user's browser) to the token endpoint, with the following parameters: client_id client_secret code : the value that you received earlier redirect_uri : one of your application's redirect URLs grant_type : use the value "authorization_code" Example cURL call to obtain an access token: curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d " client_id =ABCDEFGHIJKLM& client_secret =abcdefghsecret0123456789& code =ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789& redirect_uri =https://your-app.tld/realdebrid_api& grant_type =authorization_code"
Using the value of code , your application makes a direct POST request (not in the user's browser) to the token endpoint, with the following parameters:

- client_id
- client_secret
- code : the value that you received earlier
- redirect_uri : one of your application's redirect URLs
- grant_type : use the value "authorization_code"
##### Example cURL call to obtain an access token:

```json
curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "
client_id
=ABCDEFGHIJKLM&
client_secret
=abcdefghsecret0123456789&
code
=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&
redirect_uri
=https://your-app.tld/realdebrid_api&
grant_type
=authorization_code"
```

- If everything is correct, the access token is returned as a JSON object with the following properties: access_token expires_in : token validity period, in seconds token_type : "Bearer" refresh_token : token that only expires when your application rights are revoked by user
If everything is correct, the access token is returned as a JSON object with the following properties:

- access_token
- expires_in : token validity period, in seconds
- token_type : "Bearer"
- refresh_token : token that only expires when your application rights are revoked by user
- Your application stores the access token and uses it for the user's subsequent visits. Your application must also stores the refresh token that will be used to get new access tokens once their validity period is expired.
Your application stores the access token and uses it for the user's subsequent visits.

Your application must also stores the refresh token that will be used to get new access tokens once their validity period is expired.

### Workflow for mobile apps

This authentication process uses a variant of OAuth2, tailored for mobile devices.

The following URLs are used in this process:

- device endpoint: /device/code
- token endpoint: /token
Note: you may have to make the user do some steps in a web view (e.g. UIWebView on iOS, WebView on Android…) if you want to do all these steps from the mobile app.

#### Full workflow

- Your application makes a direct request to the device endpoint, with the query string parameter client_id , and obtains a JSON object with authentication data that will be used for the rest of the process. Example URL to obtain authentication data: https://api.real-debrid.com/oauth/v2/device/code? client_id =ABCDEFGHIJKLM Example authentication data: { "device_code" : "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" , "user_code" : "ABCDEF0123456" , "interval" : 5 , "expires_in" : 1800 , "verification_url" : "https:\/\/real-debrid.com\/device" }
Your application makes a direct request to the device endpoint, with the query string parameter client_id , and obtains a JSON object with authentication data that will be used for the rest of the process.

##### Example URL to obtain authentication data:

```json
https://api.real-debrid.com/oauth/v2/device/code?
client_id
=ABCDEFGHIJKLM
```

##### Example authentication data:

```json
{
    
"device_code"
: 
"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
,
    
"user_code"
: 
"ABCDEF0123456"
,
    
"interval"
: 
5
,
    
"expires_in"
: 
1800
,
    
"verification_url"
: 
"https:\/\/real-debrid.com\/device"

}
```

- Your application asks the user to go to the verification endpoint (provided by verification_url ) and to type the code provided by user_code .
Your application asks the user to go to the verification endpoint (provided by verification_url ) and to type the code provided by user_code .

- Using the value of device_code , every 5 seconds your application starts making direct POST requests to the token endpoint, with the following parameters: client_id client_secret code : the value of device_code grant_type : use the value "http://oauth.net/grant_type/device/1.0"" Example cURL call to obtain an access token: curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d " client_id =ABCDEFGHIJKLM& client_secret =abcdefghsecret0123456789& code =ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789& grant_type =http://oauth.net/grant_type/device/1.0" Your application will receive an error message until the user has entered the code and authorized the application.
Using the value of device_code , every 5 seconds your application starts making direct POST requests to the token endpoint, with the following parameters:

- client_id
- client_secret
- code : the value of device_code
- grant_type : use the value "http://oauth.net/grant_type/device/1.0""
##### Example cURL call to obtain an access token:

```json
curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "
client_id
=ABCDEFGHIJKLM&
client_secret
=abcdefghsecret0123456789&
code
=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&
grant_type
=http://oauth.net/grant_type/device/1.0"
```

Your application will receive an error message until the user has entered the code and authorized the application.

- The user enters the code, and then logs in if they aren't logged in yet.
The user enters the code, and then logs in if they aren't logged in yet.

- The user chooses to authorize your application, and can then close the browser window.
The user chooses to authorize your application, and can then close the browser window.

- Your application's call to the token endpoint now returns the access token as a JSON object with the following properties: access_token expires_in : token validity period, in seconds token_type : "Bearer" refresh_token : token that only expires when your application rights are revoked by user
Your application's call to the token endpoint now returns the access token as a JSON object with the following properties:

- access_token
- expires_in : token validity period, in seconds
- token_type : "Bearer"
- refresh_token : token that only expires when your application rights are revoked by user
- Your application stores the access token and uses it for the user's subsequent visits. Your application must also stores the refresh token that will be used to get new access tokens once their validity period is expired.
Your application stores the access token and uses it for the user's subsequent visits.

Your application must also stores the refresh token that will be used to get new access tokens once their validity period is expired.

### Workflow for opensource apps

This authentication process is similar to OAuth2 for mobile devices, with the difference that opensource apps or scripts can not be shipped with a client_secret (since it's meant to remain secret).

The principle here is to get a new set of client_id and client_secret that are bound to the user. You may reuse these credentials by using OAuth2 for mobile devices .

Warning: You should not redistribute the credentials. Usage with another account will display the UID of the user who obtained the credentials. E.g. instead of displaying "The most fabulous app" it will display "The most fabulous app (UID: 000)".

The following URLs are used in this process:

- device endpoint: /device/code
- credentials endpoint: /device/credentials
- token endpoint: /token
#### Full workflow

- Your application makes a direct request to the device endpoint, with the query string parameters client_id and new_credentials =yes, and obtains a JSON object with authentication data that will be used for the rest of the process. Example URL to obtain authentication data: https://api.real-debrid.com/oauth/v2/device/code? client_id =ABCDEFGHIJKLM& new_credentials =yes Example authentication data: { "device_code" : "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" , "user_code" : "ABCDEF0123456" , "interval" : 5 , "expires_in" : 1800 , "verification_url" : "https:\/\/real-debrid.com\/device" }
Your application makes a direct request to the device endpoint, with the query string parameters client_id and new_credentials =yes, and obtains a JSON object with authentication data that will be used for the rest of the process.

##### Example URL to obtain authentication data:

```json
https://api.real-debrid.com/oauth/v2/device/code?
client_id
=ABCDEFGHIJKLM&
new_credentials
=yes
```

##### Example authentication data:

```json
{
    
"device_code"
: 
"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
,
    
"user_code"
: 
"ABCDEF0123456"
,
    
"interval"
: 
5
,
    
"expires_in"
: 
1800
,
    
"verification_url"
: 
"https:\/\/real-debrid.com\/device"

}
```

- Your application asks the user to go to the verification endpoint (provided by verification_url ) and to type the code provided by user_code .
Your application asks the user to go to the verification endpoint (provided by verification_url ) and to type the code provided by user_code .

- Using the value of device_code , every 5 seconds your application starts making direct requests to the credentials endpoint, with the following query string parameters: client_id code : the value of device_code Your application will receive an error message until the user has entered the code and authorized the application.
Using the value of device_code , every 5 seconds your application starts making direct requests to the credentials endpoint, with the following query string parameters:

- client_id
- code : the value of device_code
Your application will receive an error message until the user has entered the code and authorized the application.

- The user enters the code, and then logs in if they aren't logged in yet.
The user enters the code, and then logs in if they aren't logged in yet.

- The user chooses to authorize your application, and can then close the browser window.
The user chooses to authorize your application, and can then close the browser window.

- Your application's call to the credentials endpoint now returns a JSON object with the following properties: client_id : a new client_id that is bound to the user client_secret Your application stores these values and will use them for later requests.
Your application's call to the credentials endpoint now returns a JSON object with the following properties:

- client_id : a new client_id that is bound to the user
- client_secret
Your application stores these values and will use them for later requests.

- Using the value of device_code , your application makes a direct POST request to the token endpoint, with the following parameters: client_id : the value of client_id provided by the call to the credentials endpoint client_secret : the value of client_secret provided by the call to the credentials endpoint code : the value of device_code grant_type : use the value "http://oauth.net/grant_type/device/1.0" The answer will be a JSON object with the following properties: access_token expires_in : token validity period, in seconds token_type : "Bearer" refresh_token : token that only expires when your application rights are revoked by user Example cURL call to obtain an access token: curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d " client_id =ABCDEFGHIJKLM& client_secret =abcdefghsecret0123456789& code =ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789& grant_type =http://oauth.net/grant_type/device/1.0"
Using the value of device_code , your application makes a direct POST request to the token endpoint, with the following parameters:

- client_id : the value of client_id provided by the call to the credentials endpoint
- client_secret : the value of client_secret provided by the call to the credentials endpoint
- code : the value of device_code
- grant_type : use the value "http://oauth.net/grant_type/device/1.0"
The answer will be a JSON object with the following properties:

- access_token
- expires_in : token validity period, in seconds
- token_type : "Bearer"
- refresh_token : token that only expires when your application rights are revoked by user
##### Example cURL call to obtain an access token:

```json
curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "
client_id
=ABCDEFGHIJKLM&
client_secret
=abcdefghsecret0123456789&
code
=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&
grant_type
=http://oauth.net/grant_type/device/1.0"
```

- Your application stores the access token and uses it for the user's subsequent visits. Your application must also stores the refresh token that will be used to get new access tokens once their validity period is expired.
Your application stores the access token and uses it for the user's subsequent visits.

Your application must also stores the refresh token that will be used to get new access tokens once their validity period is expired.

### Workflow for old apps

Warning: This workflow requires a special authorization on your client_id from the webmaster.

The following URLs are used in this process:

- token endpoint: /token
#### Full workflow

- Your application makes a direct POST request to the token endpoint, with the following parameters: client_id username : User login password : User password grant_type : use the value "password" Testing Two-Factor Process For testing purposes only, you can force the server to give you the two factor error by sending: force_twofactor : true This will return the two factor validation URL: verification_url : The URL you should redirect the user to. twofactor_code error : "twofactor_auth_needed" error_code : 11 Workflow if you use a WebView / Popup Open a WebView / Popup with the value of verification_url Using the value of twofactor_code , your application makes a direct POST request (not in the user's browser) to the token endpoint, with the following parameters: client_id code : the value that you received earlier grant_type : use the value "twofactor" Example cURL call to obtain an access token: curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d " client_id =ABCDEFGHIJKLM& code =ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789& grant_type =twofactor" You will get a 403 HTTP code until the user inputs the correct security code on verification_url . Workflow if you want to handle the security code validation process The SMS or email is not sent until you make a request to the token endpoint, with the following parameters: client_id code : the value that you received earlier grant_type : use the value "twofactor" send : true On success, you will get a 204 HTTP code, if the limit is reached then it will be a 403 HTTP code. To validate the security code the user gives you, make a request to the token endpoint, with the following parameters: client_id code : the value that you received earlier grant_type : use the value "twofactor" response : use the value the user inputs On error, you will get a 400 HTTP code, if the number of attempts is reached then you will get a 403 HTTP code. On success, the answer will be a JSON object with the following properties: access_token expires_in : token validity period, in seconds token_type : "Bearer" refresh_token Important: You must NOT save any login details, only keep refresh_token as the « password ». Example cURL call to obtain an access token: curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d " client_id =ABCDEFGHIJKLM& username =abcdefghsecret0123456789& password =abcdefghsecret0123456789& grant_type =password"
Your application makes a direct POST request to the token endpoint, with the following parameters:

- client_id
- username : User login
- password : User password
- grant_type : use the value "password"
#### Testing Two-Factor Process

For testing purposes only, you can force the server to give you the two factor error by sending:

- force_twofactor : true
This will return the two factor validation URL:

- verification_url : The URL you should redirect the user to.
- twofactor_code
- error : "twofactor_auth_needed"
- error_code : 11
#### Workflow if you use a WebView / Popup

Open a WebView / Popup with the value of verification_url

Using the value of twofactor_code , your application makes a direct POST request (not in the user's browser) to the token endpoint, with the following parameters:

- client_id
- code : the value that you received earlier
- grant_type : use the value "twofactor"
##### Example cURL call to obtain an access token:

```json
curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "
client_id
=ABCDEFGHIJKLM&
code
=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&
grant_type
=twofactor"
```

You will get a 403 HTTP code until the user inputs the correct security code on verification_url .

#### Workflow if you want to handle the security code validation process

The SMS or email is not sent until you make a request to the token endpoint, with the following parameters:

- client_id
- code : the value that you received earlier
- grant_type : use the value "twofactor"
- send : true
On success, you will get a 204 HTTP code, if the limit is reached then it will be a 403 HTTP code.

To validate the security code the user gives you, make a request to the token endpoint, with the following parameters:

- client_id
- code : the value that you received earlier
- grant_type : use the value "twofactor"
- response : use the value the user inputs
On error, you will get a 400 HTTP code, if the number of attempts is reached then you will get a 403 HTTP code.

On success, the answer will be a JSON object with the following properties:

- access_token
- expires_in : token validity period, in seconds
- token_type : "Bearer"
- refresh_token
Important: You must NOT save any login details, only keep refresh_token as the « password ».

##### Example cURL call to obtain an access token:

```json
curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "
client_id
=ABCDEFGHIJKLM&
username
=abcdefghsecret0123456789&
password
=abcdefghsecret0123456789&
grant_type
=password"
```

### Get a new access token from a refresh token

The following URLs are used in this process:

- token endpoint: /token
#### Full workflow

- Using the value of refresh_token your application saved earlier, your application makes a direct POST request to the token endpoint, with the following parameters: client_id client_secret code : the value of refresh_token grant_type : use the value "http://oauth.net/grant_type/device/1.0" The answer will be a JSON object with the following properties: access_token expires_in : token validity period, in seconds token_type : "Bearer" refresh_token Example cURL call to obtain an access token: curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d " client_id =ABCDEFGHIJKLM& client_secret =abcdefghsecret0123456789& code =ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789& grant_type =http://oauth.net/grant_type/device/1.0"
Using the value of refresh_token your application saved earlier, your application makes a direct POST request to the token endpoint, with the following parameters:

- client_id
- client_secret
- code : the value of refresh_token
- grant_type : use the value "http://oauth.net/grant_type/device/1.0"
The answer will be a JSON object with the following properties:

- access_token
- expires_in : token validity period, in seconds
- token_type : "Bearer"
- refresh_token
##### Example cURL call to obtain an access token:

```json
curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "
client_id
=ABCDEFGHIJKLM&
client_secret
=abcdefghsecret0123456789&
code
=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&
grant_type
=http://oauth.net/grant_type/device/1.0"
```

## List of numeric error codes

In addition to the HTTP error code, errors come with a message ( error parameter) and a numeric code ( error_code parameter). The error message is meant to be human-readable, while the numeric codes should be used by your application.
