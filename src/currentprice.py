import requests

tempLink = "https://www.nerdjewels.com/sellers.json"

response = requests.get(tempLink)

print(response.json)