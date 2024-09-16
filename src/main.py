from helpers import send_get_request, send_delete_request
from termcolor import colored, cprint
from dotenv import load_dotenv

import requests
import sys
import os

# Load the environment variables
load_dotenv()

# Get the github access token from the environment variables
TOKEN = os.getenv("TOKEN")
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28"
}

GET_LIST_OF_FOLLOWING_USERS_URL = f"https://api.github.com/user/following?per_page=100&page=1"
GET_LIST_OF_FOLLOWERS_URL = f"https://api.github.com/user/followers?per_page=100&page=1"

following = []

# List the people the authenticated user follows
response = send_get_request(GET_LIST_OF_FOLLOWING_USERS_URL, headers=headers)
if response.status_code == 401:
    cprint("Invalid token!", "red")
    sys.exit()

for user in response.json():
    following.append(user["login"])

header_link = response.headers.get("Link")

if header_link:
    number_of_pages = int(header_link.split(",")[-1].split(";")[0].strip("<>")[-1])
    for i in range(2, number_of_pages + 1):
        next_page_url = f"https://api.github.com/user/following?per_page=100&page={i}"
        response = send_get_request(next_page_url, headers=headers)
        for user in response.json():
            following.append(user["login"])

# List followers of the authenticated user
response = send_get_request(GET_LIST_OF_FOLLOWERS_URL, headers=headers)
if response.status_code == 401:
    cprint("Invalid token!", "red")
    sys.exit()

followers = []
for user in response.json():
    followers.append(user["login"])

header_link = response.headers.get("Link")

if header_link:
    number_of_pages = int(header_link.split(",")[-1].split(";")[0].strip("<>")[-1])
    for i in range(2, number_of_pages + 1):
        next_page_url = f"https://api.github.com/user/followers?per_page=100&page={i}"
        response = send_get_request(next_page_url, headers=headers)
        for user in response.json():
            followers.append(user["login"])

# Get the list of users who are not following back
not_following_back = []
for user in following:
    if user not in followers:
        not_following_back.append({
            "username": colored(user, "cyan"),
            "profile_link": colored(f"https://github.com/{user}", 'light_red'),
            "unfollow_link": f"https://api.github.com/user/following/{user}"
        })

# Print the list of users who are not following back
cprint(f"List of users who are not following back:", "green")
for user in not_following_back:
    print(f"{user['username']} - Profile: {user['profile_link']}")

# Print the number of users who are not following back
cprint(f"Number of users who are not following back: {len(not_following_back)}", "yellow")

# Ask the user if he wants to unfollow
while True:
    choice = input("Do you want to unfollow some/all the users who are not following back? (y/n): ")
    if choice.lower() == "y" or choice.lower() == "yes":
        break
    elif choice.lower() == "n" or choice.lower() == "no":
        sys.exit()
    else:
        cprint("Invalid choice!", "red")

if choice.lower() == "y" or choice.lower() == "yes":
    # Ask the user if they want to unfollow all the users who are not following back at once or go one by one
    while True:
        choice = input("""1- Do you want to unfollow all the users who are not following back at once.\n2- Do you want to select who to unfollow one by one.\n""")
        if choice.lower() == "1":
            for user in not_following_back:
                response = send_delete_request(user["unfollow_link"], TOKEN)
                print(response.text, response.status_code)
                if response.status_code == 204:
                    cprint(f"Unfollowed {user['username']} successfully!", "green")
                else:
                    cprint(f"Unfollowing {user['username']} failed!", "red")
            break
        elif choice.lower() == "2":
            for user in not_following_back:
                while True:
                    choice = input(f"Do you want to unfollow {user['username']} - Profile: {user['profile_link']}? (y/n): ")
                    if choice.lower() == "y":
                        response = send_delete_request(user["unfollow_link"], headers)
                        if response.status_code == 204:
                            cprint(f"Unfollowed {user['username']} successfully!", "green")
                        else:
                            cprint(f"Unfollowing {user['username']} failed!", "red")
                        break
                    elif choice.lower() == "n":
                        break
                    else:
                        cprint("Invalid choice!", "red")
            break
        else:
            cprint("Invalid choice!", "red")




