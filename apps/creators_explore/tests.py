# import requests

# url = "https://instagram-scraper-20251.p.rapidapi.com/userinfo/"
# querystring = {"username_or_id": "instagram"}

# headers = {
#     "x-rapidapi-key": "5c45bc26b3mshcbb5b5935c4d291p1bb74ajsn78a5d810226c",
# 	"x-rapidapi-host": "instagram-scraper-20251.p.rapidapi.com"
# }

# response = requests.get(url, headers=headers, params=querystring)
# data = response.json()

# username = data['data'].get('username')
# followers_count = data['data'].get('follower_count')

# print(f"Username: {username}")
# print(f"Followers Count: {followers_count}")



# import requests

# url = "https://tiktok-api23.p.rapidapi.com/api/trending/creator"

# querystring = {"page":"1","limit":"20","sort_by":"follower","country":"US"}

# headers = {
# 	"x-rapidapi-key": "5c45bc26b3mshcbb5b5935c4d291p1bb74ajsn78a5d810226c",
# 	"x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
# }

# response = requests.get(url, headers=headers, params=querystring)

# print(response.json())