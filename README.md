# New Twitter App
> Pet project, based on FastAPI, Jinja2, Redis, Celery, 
> Flower, PostgreSQL, Docker, Pytest

MVP of a Twitter-like app, with the following features: registration, 
login, logout, adding tweets, adding tweets with images, editing tweets, 
retweeting tweets, liking tweets, adding profile pictures,
changing profile pictures, changing password 
and other personal information.


## Getting Started

To get it running clone my github repository, 
cd into the project folder and run docker-compose file.

```shell
git clone https://github.com/Aksyontov/FastApi-Pet-Projects.git
cd .../FastApi-Pet-Projects
docker compose up --build
```

If you don't have Docker installed, visit [official site](https://www.docker.com/get-started/) 
and follow the instructions.

After doing the steps above you should be able to access 
the app at http://localhost:8000

### Registration and Login

During your first visit, you would be redirected 
to the Login page. 

It's impossible to access any other page before creating an account. 
If you don't have one yet, click the "Register?" button. You would be
redirected to a Registration page. 

Fill in the form with your username, first name, 
last name, email, phone number and password. 

You could also upload
your profile picture on this step, but If you don't want to upload it right away, 
you could do it later. 

Any information provided, including your profile
picture, could be changed later as well. The only exception is your username.

After filling in all the necessary fields, click the "Sign Up" button.
You would be redirected back to the Login page.

Fill in the form with your username and password and click "Login". 
The app would create a session for you and you would be 
redirected to the Home Page.


### Home Page and User Pages

Here you can see 
all the tweets posted on the platform so far, 
sorted by the time of creation.

You would be able to like or retweet each of them, 
including your own tweets. 

To like any tweet, click the "Like" button. 
Your likes would be visible only to you. 

To retweet any tweet, click the "Retweet" button. It would refresh the page,
and you would see the tweet you retweeted reappearing in the feed once
again, but this time with a mark "Retweeted by @your_username".

On your own tweets in addition to the "Like" and "Retweet" buttons,
you would see an "Edit" button, which will allow you to change 
the contexts of it or delete it whatsoever.

Clicking on any user handle would redirect you to the specific user page, 
where you could see all the tweets posted by this user. This also works 
for your own username and for "Retweeted by @some_username" marks.

User pages are very similar to the Home page. Here you could also 
like or retweet any of the tweets and if it's your own page, you could 
edit them as well.

To return back to the Home Page, click the "Home" button in upper left corner.

### Adding, Editing and Deleting Tweets
To post a tweet, while on a Home Page or a User Page 
click the "Tweet Something Yourself!" button.

You will be redirected to a new page, where you could write new tweet and 
attach any image file to it. You could also skip the image part.

Click "Send" to post it and return back to the Home Page. 

Here you would see your new tweet at the top of the feed. And next to it
you would see an "Edit" button. 

Click "Edit" to get redirected to a page where you could see the tweet text
and make all the necessary changes. Notice that you couldn't attach 
a new image or change an existing one after publishing your tweet for the
first time.

After clicking the "Publish" button, you would be redirected back to 
the Home Page and your edited tweet would display the latest version 
of the text provided. The text of your tweet would also change in every 
retweet of it.

If you want to delete your tweet, click the "Delete" button while on Edit
Tweet page. This action would completely erase your tweet and all 
the retweets.

### Changing Settings and Logging Out

To change some personal information, click the "Settings" button. It's
located in the upper right corner of every page.

Here you would see the form, which is almost identical to the Registration 
page. Fill in only those fields, that you want to change. For example, if
you want to provide a new phone number, fill in only the phone number field.

To change you password, you need to fill both the "Current Password" and
the "New Password" fields. And if you didn't have a profile picture before,
you could upload it now.

Still, you can't leave all the fields blank, so if you don't want to 
change anything whatsoever, just click the "Home" button.

To exit the app, click the "Logout" button. It would terminate your session
and return you back to the Login page. Here you could login once more or
even create one more user.

### Finishing your session

After playing with the app, you can stop 
it by running the following command:

```shell
docker compose down
```

## Developing and Licensing

The code in this project is licensed under MIT license. Feel free to 
use it in your own projects or to contribute to this one.

### Tests
Tests are still in development. 

You could run existing ones 
by running the following command:

```shell
pytest
```